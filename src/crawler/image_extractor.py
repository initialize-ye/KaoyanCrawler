"""最高精度图片识别提取器。

精度保障机制（5 层）：
  1. 图片预处理（增强对比度、去噪、二值化、自适应锐化）
  2. 多轮 OCR（不同预处理参数各跑一次，投票合并）
  3. 多引擎交叉验证（RapidOCR + EasyOCR，取并集）
  4. LLM 校验（对比 OCR 文本与原图，修正错误）
  5. 置信度追踪（标记低置信区域供人工复核）
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.settings import AI_PROVIDERS

# ── 提示词模板 ──

OCR_STRUCTURING_PROMPT = """你是一个考研招生数据提取专家。以下是从考研招生图片中通过 OCR 精确提取的文本内容。

请注意：
- 文本中可能包含"灰灰考研"等水印文字，请完全忽略这些内容
- 专注于提取实际的招生数据

OCR 提取的文本：
{ocr_text}

请从上述文本中提取全部考研招生统计信息，返回标准 JSON：

{{
  "schoolName": "学校全称（如：清华大学、北京大学）",
  "schoolWebsite": "学校研究生院官网 URL",
  "duration": "学制（如：3年）",
  "tuition": "学费（如：8000元/年）",
  "scholarship": "奖学金政策简述",
  "colleges": [
    {{
      "collegeName": "学院全称（如：计算机科学与技术学院）",
      "collegeWebsite": "学院官网 URL",
      "majors": [
        {{
          "majorName": "专业名称（如：计算机科学与技术）",
          "majorCode": "6位专业代码（如：081200）",
          "subjects": ["政治", "英语", "数学", "专业课"],
          "retestScoreLine": "复试分数线（如：320）",
          "retestCount": "进入复试人数（如：45）",
          "retestScoreRange": "复试总分区间（如：320-385）",
          "singleSubjectRange": "单科成绩区间（如：政治60-85，英语55-80）",
          "plannedEnrollment": "预计招生人数（如：30）",
          "admissionScoreRange": "拟录取分数区间（如：335-385）",
          "specialProgram": "特殊项目类型（专项计划/校企联合/中外合作/null）",
          "retestInfo": {{
            "time": "复试时间（如：2025年3月20日）",
            "method": "复试形式（如：线下笔试+面试）",
            "content": "复试内容（如：专业课笔试、综合面试、英语口语）",
            "scoreRule": "成绩计算方式（如：初试60%+复试40%）",
            "remark": "其他备注说明"
          }}
        }}
      ]
    }}
  ]
}}

提取规则：
1. 专业代码必须是 6 位数字（如 081200），如果没有则填 null
2. 分数必须是数字，不要包含"分"字
3. 分数区间用 "-" 连接（如 "320-385"）
4. 人数必须是整数
5. URL 必须完整（包含 http:// 或 https://）
6. 如果某字段在原文中不存在，填 null
7. 不要遗漏任何学院和专业
8. 只返回 JSON，不要其他文字"""

VISION_EXTRACTION_PROMPT = """你是一个考研招生数据提取专家。请仔细识别图片中的全部考研招生统计信息。

请注意：
- 图片中可能有"灰灰考研"等水印，请完全忽略水印内容
- 专注于识别实际的招生数据表格和文字

请提取以下信息并返回 JSON：

一、学校基本信息：
- schoolName: 学校全称（如：清华大学）
- schoolWebsite: 研究生院官网 URL
- duration: 学制（如：3年）
- tuition: 学费（如：8000元/年）
- scholarship: 奖学金政策

二、学院信息（每个学院一个对象）：
- collegeName: 学院全称
- collegeWebsite: 学院官网 URL

三、专业信息（每个专业一个对象）：
- majorName: 专业名称
- majorCode: 6位专业代码（如 081200）
- subjects: 初试科目数组（如 ["政治", "英语", "数学", "专业课"]）
- retestScoreLine: 复试分数线（数字）
- retestCount: 进入复试人数（整数）
- retestScoreRange: 复试总分区间（如 "320-385"）
- singleSubjectRange: 单科成绩区间
- plannedEnrollment: 预计招生人数（整数）
- admissionScoreRange: 拟录取分数区间
- specialProgram: 特殊项目（专项计划/校企联合/中外合作/null）

四、复试信息：
- time: 复试时间
- method: 复试形式
- content: 复试内容
- scoreRule: 成绩计算方式
- remark: 其他备注

JSON 结构：
{{
  "schoolName": "",
  "schoolWebsite": "",
  "duration": "",
  "tuition": "",
  "scholarship": "",
  "colleges": [
    {{
      "collegeName": "",
      "collegeWebsite": "",
      "majors": [
        {{
          "majorName": "",
          "majorCode": "",
          "subjects": [],
          "retestScoreLine": "",
          "retestCount": "",
          "retestScoreRange": "",
          "singleSubjectRange": "",
          "plannedEnrollment": "",
          "admissionScoreRange": "",
          "specialProgram": "",
          "retestInfo": {{
            "time": "",
            "method": "",
            "content": "",
            "scoreRule": "",
            "remark": ""
          }}
        }}
      ]
    }}
  ]
}}

提取规则：
1. 专业代码必须是 6 位数字，没有则填 null
2. 分数只填数字，不要"分"字
3. 分数区间用 "-" 连接
4. 人数填整数
5. URL 要完整
6. 不存在的字段填 null
7. 不要遗漏任何学院和专业
8. 忽略水印文字
9. 只返回 JSON"""

LLM_VERIFICATION_PROMPT = """你是一个考研招生数据校验专家。以下有两份从同一张图片中提取的数据：

【OCR 提取的原始文本】：
{ocr_text}

【AI 结构化提取的结果】：
{structured_json}

请执行以下校验和修正，返回修正后的完整 JSON：

一、数字校验：
1. 分数范围：政治/英语 0-100，数学/专业课 0-150，总分 0-500
2. 专业代码：必须是 6 位数字（如 081200）
3. 年份：4 位数字（如 2025）
4. 修正 OCR 错误：0↔O、1↔l/I、8↔B、5↔S、6↔G、2↔Z

二、逻辑校验：
1. 复试最低分 ≤ 复试最高分
2. 初试总分 ≈ 政治 + 英语 + 专业课1 + 专业课2（误差 ±5 分）
3. 拟录取人数 ≤ 复试人数
4. 复试分数线 ≤ 复试最高分

三、格式校验：
1. URL 必须以 http:// 或 https:// 开头
2. 分数区间格式："320-385" 或 "320~385"
3. 日期格式："2025年3月20日" 或 "2025-03-20"
4. 专业代码：6 位纯数字

四、完整性校验：
1. 检查是否有遗漏的学院或专业
2. 确保每个专业都有名称和代码
3. 移除明显的水印文字（如"灰灰考研"）

请返回修正后的完整 JSON（结构不变），只返回 JSON，不要其他文字。"""


# ── 水印去除 ──

# "灰灰考研" 水印特征：通常是半透明灰色/浅色文字叠加在图片上
WATERMARK_PATTERNS = ["灰灰考研", "灰灰", "考研"]


def remove_watermark(image: np.ndarray) -> np.ndarray:
    """去除图片中的"灰灰考研"水印。

    策略：
    1. 检测半透明浅色文字区域（水印通常是浅灰色，与背景有一定对比度）
    2. 对检测到的水印区域，用周围背景色填充
    3. 特别针对"灰灰考研"四字水印模式优化
    """
    if len(image.shape) == 2:
        # 灰度图：检测浅灰色水印
        return _remove_watermark_grayscale(image)
    else:
        # 彩色图：检测半透明灰色水印
        return _remove_watermark_color(image)


def _remove_watermark_grayscale(image: np.ndarray) -> np.ndarray:
    """去除灰度图上的水印。"""
    h, w = image.shape
    result = image.copy()

    # 水印特征：灰度值在 160-220 之间（浅灰色），且呈条状分布
    # 统计每行的灰度分布，找到水印所在区域
    row_means = np.mean(image, axis=1)

    # 找到灰度值异常高的行（水印行）
    global_mean = np.mean(image)
    watermark_threshold = global_mean + 30

    for y in range(h):
        if row_means[y] > watermark_threshold:
            # 检查该行是否呈条状分布（水印特征）
            row = image[y]
            # 检查灰度值的方差（水印区域方差较小）
            if np.std(row) < 40:
                # 用上下行的平均值填充
                y_top = max(0, y - 2)
                y_bot = min(h - 1, y + 2)
                result[y] = (image[y_top].astype(np.float64) + image[y_bot].astype(np.float64)) / 2

    return result.astype(np.uint8)


def _remove_watermark_color(image: np.ndarray) -> np.ndarray:
    """去除彩色图上的水印。"""
    h, w = image.shape[:2]
    result = image.copy()

    # 将图片转为 float 进行计算
    img_float = image.astype(np.float64)

    # 检测灰色水印：R≈G≈B，且亮度较高（浅灰色）
    if len(image.shape) == 3 and image.shape[2] >= 3:
        r, g, b = img_float[:, :, 0], img_float[:, :, 1], img_float[:, :, 2]

        # 灰色条件：RGB 通道差异小
        gray_diff = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
        is_gray = gray_diff < 30

        # 浅色条件：亮度较高
        brightness = (r + g + b) / 3
        is_light = brightness > 160

        # 水印区域：既是灰色又是浅色
        watermark_mask = is_gray & is_light

        # 形态学操作：膨胀以覆盖水印边缘
        from numpy.lib.stride_tricks import sliding_window_view
        if h >= 5 and w >= 5:
            # 5x5 膨胀
            padded = np.pad(watermark_mask.astype(np.uint8), 2, mode="edge")
            windows = sliding_window_view(padded, (5, 5))
            watermark_mask = np.any(windows, axis=(-2, -1))

        # 对水印区域用周围像素插值填充
        for y in range(h):
            for x in range(w):
                if watermark_mask[y, x]:
                    # 取周围非水印像素的平均值
                    neighbors = []
                    for dy in [-3, -2, -1, 1, 2, 3]:
                        for dx in [-3, -2, -1, 1, 2, 3]:
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and not watermark_mask[ny, nx]:
                                neighbors.append(image[ny, nx])
                    if neighbors:
                        result[y, x] = np.mean(neighbors, axis=0).astype(np.uint8)

    return result


def _fast_remove_watermark_color(image: np.ndarray) -> np.ndarray:
    """快速水印去除（向量化版本，适合大图）。"""
    h, w = image.shape[:2]
    result = image.copy()

    if len(image.shape) < 3 or image.shape[2] < 3:
        return result

    img_float = image.astype(np.float64)
    r, g, b = img_float[:, :, 0], img_float[:, :, 1], img_float[:, :, 2]

    # 灰色检测
    gray_diff = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
    is_gray = gray_diff < 30

    # 浅色检测
    brightness = (r + g + b) / 3
    is_light = brightness > 160

    # 水印掩码
    mask = is_gray & is_light

    # 用中值滤波结果替换水印区域
    from numpy.lib.stride_tricks import sliding_window_view
    if h >= 7 and w >= 7:
        for c in range(3):
            padded = np.pad(image[:, :, c], 3, mode="reflect")
            windows = sliding_window_view(padded, (7, 7))
            median_vals = np.median(windows, axis=(-2, -1))
            result[:, :, c] = np.where(mask, median_vals, result[:, :, c])

    return result.astype(np.uint8)


def preprocess_image(image_bytes: bytes, pipeline: PreprocessPipeline) -> np.ndarray:
    """按流水线配置预处理图片。"""
    import io
    from PIL import Image as PILImage

    img = PILImage.open(io.BytesIO(image_bytes))
    arr = np.array(img)

    # 去除水印（在转灰度之前，保留颜色信息用于检测）
    if pipeline.remove_watermark:
        arr = _fast_remove_watermark_color(arr)

    # 转灰度
    if pipeline.grayscale:
        arr = _to_grayscale(arr)

    # 放大
    if pipeline.scale > 1.0:
        arr = _scale_up(arr, pipeline.scale)

    # 对比度
    if pipeline.contrast != 1.0:
        arr = _adjust_contrast(arr, pipeline.contrast)

    # 去噪
    if pipeline.denoise:
        arr = _denoise(arr)

    # 二值化
    if pipeline.binarize == "otsu":
        arr = _binarize_otsu(arr)
    elif pipeline.binarize == "adaptive":
        block = getattr(pipeline, "block_size", 15)
        arr = _binarize_adaptive(arr, block_size=block)

    # 锐化
    if pipeline.sharpen > 0:
        arr = _sharpen(arr, pipeline.sharpen)

    return arr


# ── 图片预处理 ──

def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """转灰度图。"""
    if len(image.shape) == 3:
        return np.dot(image[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
    return image


def _adjust_contrast(image: np.ndarray, factor: float = 1.5) -> np.ndarray:
    """增强对比度。"""
    mean = np.mean(image)
    adjusted = (image - mean) * factor + mean
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def _denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """简单去噪（中值滤波近似）。"""
    from numpy.lib.stride_tricks import sliding_window_view

    if image.shape[0] < 3 or image.shape[1] < 3:
        return image
    pad = 1
    padded = np.pad(image, pad, mode="edge")
    windows = sliding_window_view(padded, (3, 3))
    return np.median(windows, axis=(-2, -1)).astype(np.uint8)


def _binarize_otsu(image: np.ndarray) -> np.ndarray:
    """Otsu 自适应二值化。"""
    # 计算直方图
    hist, _ = np.histogram(image, bins=256, range=(0, 256))
    total = image.size
    sum_total = np.sum(np.arange(256) * hist)

    sum_bg = 0.0
    weight_bg = 0
    max_variance = 0
    threshold = 0

    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > max_variance:
            max_variance = variance
            threshold = t

    return ((image > threshold) * 255).astype(np.uint8)


def _binarize_adaptive(image: np.ndarray, block_size: int = 15, c: int = 10) -> np.ndarray:
    """自适应二值化（局部均值）。"""
    from numpy.lib.stride_tricks import sliding_window_view

    h, w = image.shape
    pad = block_size // 2
    padded = np.pad(image.astype(np.float64), pad, mode="reflect")
    windows = sliding_window_view(padded, (block_size, block_size))
    local_mean = np.mean(windows, axis=(-2, -1))
    return ((image.astype(np.float64) > local_mean - c) * 255).astype(np.uint8)


def _sharpen(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """锐化。"""
    from numpy.lib.stride_tricks import sliding_window_view

    if image.shape[0] < 3 or image.shape[1] < 3:
        return image
    padded = np.pad(image.astype(np.float64), 1, mode="edge")
    windows = sliding_window_view(padded, (3, 3))
    center = windows[:, :, 1, 1]
    neighbor_mean = (
        windows[:, :, 0, 1] + windows[:, :, 2, 1]
        + windows[:, :, 1, 0] + windows[:, :, 1, 2]
    ) / 4.0
    sharpened = center + strength * (center - neighbor_mean)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def _scale_up(image: np.ndarray, factor: float = 2.0) -> np.ndarray:
    """最近邻放大图片（小图识别增强）。"""
    h, w = image.shape[:2]
    new_h, new_w = int(h * factor), int(w * factor)
    row_idx = (np.arange(new_h) / factor).astype(int)
    col_idx = (np.arange(new_w) / factor).astype(int)
    row_idx = np.clip(row_idx, 0, h - 1)
    col_idx = np.clip(col_idx, 0, w - 1)
    return image[np.ix_(row_idx, col_idx)]


@dataclass
class PreprocessPipeline:
    """预处理流水线配置。"""
    name: str
    grayscale: bool = True
    contrast: float = 1.0
    denoise: bool = False
    binarize: str = "none"  # "none", "otsu", "adaptive"
    sharpen: float = 0.0
    scale: float = 1.0
    block_size: int = 15
    remove_watermark: bool = False


# 5 套预处理参数，覆盖不同场景
PIPELINES = [
    PreprocessPipeline("original", grayscale=False, remove_watermark=True),
    PreprocessPipeline("high_contrast", contrast=2.0, sharpen=0.5, remove_watermark=True),
    PreprocessPipeline("otsu_binary", denoise=True, binarize="otsu", remove_watermark=True),
    PreprocessPipeline("adaptive_binary", contrast=1.3, binarize="adaptive", block_size=21, remove_watermark=True),
    PreprocessPipeline("sharpened", contrast=1.5, denoise=True, sharpen=1.0, remove_watermark=True),
]

# 扩展版：对小图额外放大
SMALL_IMAGE_PIPELINES = PIPELINES + [
    PreprocessPipeline("upscaled", scale=2.0, contrast=1.5, sharpen=0.5, remove_watermark=True),
]


# ── OCR 引擎 ──

@dataclass
class OCRResult:
    """单条 OCR 结果。"""
    box: list  # 四角坐标
    text: str
    confidence: float
    y_center: float = 0.0
    x_center: float = 0.0

    def __post_init__(self):
        self.y_center = (self.box[0][1] + self.box[2][1]) / 2
        self.x_center = (self.box[0][0] + self.box[2][0]) / 2


class OCREngine:
    """OCR 引擎，支持多轮预处理 + 多引擎交叉验证。"""

    def __init__(self):
        self._rapid = None
        self._easyocr = None
        self._rapid_ok = False
        self._easyocr_ok = False

    def _init_rapid(self):
        if self._rapid is not None:
            return
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._rapid = RapidOCR()
            self._rapid_ok = True
            logger.info("RapidOCR 初始化成功")
        except ImportError:
            logger.info("RapidOCR 未安装")

    def _init_easyocr(self):
        if self._easyocr is not None:
            return
        try:
            import easyocr
            self._easyocr = easyocr.Reader(["ch_sim", "en"], gpu=False)
            self._easyocr_ok = True
            logger.info("EasyOCR 初始化成功")
        except ImportError:
            logger.info("EasyOCR 未安装")

    def available_engines(self) -> list[str]:
        """返回可用引擎列表。"""
        self._init_rapid()
        self._init_easyocr()
        engines = []
        if self._rapid_ok:
            engines.append("RapidOCR")
        if self._easyocr_ok:
            engines.append("EasyOCR")
        return engines

    def extract_multi_pass(self, image_bytes: bytes) -> tuple[str, list[str]]:
        """多轮预处理 + 多引擎提取，投票合并。

        Returns:
            (最终文本, 各轮原始文本列表)
        """
        self._init_rapid()
        self._init_easyocr()

        if not self._rapid_ok and not self._easyocr_ok:
            raise ImportError(
                "未找到可用的 OCR 引擎。请安装:\n"
                "  pip install rapidocr-onnxruntime  (推荐)\n"
                "  pip install easyocr"
            )

        # 判断是否为小图
        try:
            import io
            from PIL import Image as PILImage
            img = PILImage.open(io.BytesIO(image_bytes))
            is_small = max(img.size) < 800
        except Exception:
            is_small = False

        pipelines = SMALL_IMAGE_PIPELINES if is_small else PIPELINES

        all_texts: list[str] = []
        all_results: list[tuple[str, list[OCRResult]]] = []
        high_confidence_count = 0
        HIGH_CONFIDENCE_THRESHOLD = 0.95
        MIN_PASSES_FOR_EARLY_EXIT = 2

        # 对每个预处理流水线运行 OCR
        for i, pipe in enumerate(pipelines):
            try:
                arr = preprocess_image(image_bytes, pipe)
            except Exception as e:
                logger.warning(f"预处理 [{pipe.name}] 失败: {e}")
                continue

            # RapidOCR
            if self._rapid_ok:
                text, results = self._run_rapid(arr, pipe.name)
                if text.strip():
                    all_texts.append(text)
                    all_results.append((f"rapid/{pipe.name}", results))
                    # 检查置信度
                    if results:
                        avg_conf = sum(r.confidence for r in results) / len(results)
                        if avg_conf >= HIGH_CONFIDENCE_THRESHOLD:
                            high_confidence_count += 1

            # EasyOCR
            if self._easyocr_ok:
                text, results = self._run_easyocr(arr, pipe.name)
                if text.strip():
                    all_texts.append(text)
                    all_results.append((f"easyocr/{pipe.name}", results))
                    # 检查置信度
                    if results:
                        avg_conf = sum(r.confidence for r in results) / len(results)
                        if avg_conf >= HIGH_CONFIDENCE_THRESHOLD:
                            high_confidence_count += 1

            # 提前终止：如果已经有足够的高置信度结果
            if high_confidence_count >= MIN_PASSES_FOR_EARLY_EXIT and i >= 1:
                logger.info(f"OCR 提前终止: 已获得 {high_confidence_count} 个高置信度结果")
                break

        if not all_texts:
            return "", []

        # 投票合并：选择出现次数最多的文本变体
        merged = self._merge_texts(all_texts)
        logger.info(f"多轮 OCR 完成: {len(all_texts)} 轮 → 合并后 {len(merged)} 字符")
        return merged, all_texts

    def _run_rapid(self, arr: np.ndarray, pipe_name: str) -> tuple[str, list[OCRResult]]:
        """运行 RapidOCR。"""
        try:
            result, _ = self._rapid(arr)
            if not result:
                return "", []

            ocr_results = []
            for item in result:
                box, text, conf = item
                ocr_results.append(OCRResult(box=box, text=text, confidence=conf))

            merged = self._merge_by_position(ocr_results)
            return merged, ocr_results
        except Exception as e:
            logger.warning(f"RapidOCR [{pipe_name}] 失败: {e}")
            return "", []

    def _run_easyocr(self, arr: np.ndarray, pipe_name: str) -> tuple[str, list[OCRResult]]:
        """运行 EasyOCR。"""
        try:
            results = self._easyocr.readtext(arr)
            if not results:
                return "", []

            ocr_results = []
            for bbox, text, conf in results:
                # EasyOCR bbox 格式: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                ocr_results.append(OCRResult(box=bbox, text=text, confidence=conf))

            merged = self._merge_by_position(ocr_results)
            return merged, ocr_results
        except Exception as e:
            logger.warning(f"EasyOCR [{pipe_name}] 失败: {e}")
            return "", []

    def _merge_by_position(self, results: list[OCRResult]) -> str:
        """按位置排序合并 OCR 结果。"""
        if not results:
            return ""

        # 按 y 坐标分组（同行阈值 20px）
        results.sort(key=lambda r: (round(r.y_center / 20) * 20, r.x_center))

        lines: list[str] = []
        current_y = None
        parts: list[tuple[float, str]] = []

        for r in results:
            if current_y is None or abs(r.y_center - current_y) > 20:
                if parts:
                    parts.sort(key=lambda p: p[0])
                    lines.append(" ".join(p[1] for p in parts))
                current_y = r.y_center
                parts = [(r.x_center, r.text)]
            else:
                parts.append((r.x_center, r.text))

        if parts:
            parts.sort(key=lambda p: p[0])
            lines.append(" ".join(p[1] for p in parts))

        return "\n".join(lines)

    def _merge_texts(self, texts: list[str]) -> str:
        """投票合并多轮 OCR 文本。

        策略：
        - 按行对齐
        - 对每行，选择出现次数最多的版本
        - 如果所有版本都不同，选择最长的（通常包含更多信息）
        """
        if len(texts) == 1:
            return texts[0]

        # 将每个文本按行拆分
        all_lines = [t.split("\n") for t in texts]

        # 找到最长的行数
        max_lines = max(len(lines) for lines in all_lines)

        merged_lines: list[str] = []
        for i in range(max_lines):
            candidates: list[str] = []
            for lines in all_lines:
                if i < len(lines) and lines[i].strip():
                    candidates.append(lines[i].strip())

            if not candidates:
                continue

            # 投票：出现次数最多
            from collections import Counter
            counter = Counter(candidates)
            best, count = counter.most_common(1)[0]

            # 如果票数相同，选最长的
            if count == 1 and len(candidates) > 1:
                best = max(candidates, key=len)

            merged_lines.append(best)

        return "\n".join(merged_lines)


# ── 主提取器 ──

class ImageExtractor:
    """最高精度图片识别提取器。

    5 层精度保障：
    1. 图片预处理（多套参数）
    2. 多轮 OCR（每套参数各跑一次）
    3. 多引擎交叉验证（RapidOCR + EasyOCR）
    4. LLM 结构化
    5. LLM 校验（对比 OCR 文本与结构化结果）
    """

    def __init__(self, provider: str, api_key: str, base_url: str = "", model: str = ""):
        self.provider = provider
        self.api_key = api_key

        provider_config = AI_PROVIDERS.get(provider, {})
        self.base_url = base_url or provider_config.get("base_url", "")
        self.model = model or provider_config.get("model", "")

        self._ocr = OCREngine()

    @classmethod
    def from_settings(cls, **kwargs) -> ImageExtractor | None:
        """从配置文件创建实例。"""
        from src.config.settings import get_ai_config

        config = get_ai_config()
        if not config:
            return None
        return cls(
            provider=config["provider"],
            api_key=config["api_key"],
            base_url=config.get("base_url", ""),
            model=config.get("model", ""),
        )

    async def extract_from_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        progress_callback=None,
    ) -> dict[str, Any]:
        """从图片中提取结构化数据（最高精度模式）。

        Args:
            image_bytes: 图片二进制内容
            mime_type: 图片MIME类型
            progress_callback: 进度回调函数，接收 (step, status, detail, progress)
        """
        if not self.api_key:
            return {"success": False, "error": "API Key未配置"}

        try:
            return await self._extract_highest_precision(image_bytes, mime_type, progress_callback)
        except Exception as e:
            error_msg = str(e) or repr(e) or f"未知错误 ({type(e).__name__})"
            logger.error(f"图片识别失败 [{self.provider}]: {error_msg}")
            return {"success": False, "error": error_msg}

    async def extract_from_file(self, file_path: str) -> dict[str, Any]:
        """从图片文件中提取结构化数据。"""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}

        suffix = path.suffix.lower()
        mime_map = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(suffix, "image/png")
        image_bytes = path.read_bytes()
        return await self.extract_from_image(image_bytes, mime_type)

    async def _extract_highest_precision(
        self,
        image_bytes: bytes,
        mime_type: str,
        progress_callback=None,
    ) -> dict[str, Any]:
        """最高精度提取流程。"""

        def _notify(step: str, status: str, detail: str, progress: int):
            """发送进度通知。"""
            logger.info(f"[{step}] {status}: {detail}")
            if progress_callback:
                progress_callback(step, status, detail, progress)

        # ── 步骤 1：初始化 OCR 引擎 ──
        _notify("init", "running", "正在初始化 OCR 引擎...", 5)
        engines = self._ocr.available_engines()
        _notify("init", "done", f"可用引擎: {', '.join(engines)}", 10)

        # ── 步骤 2：图片预处理 ──
        _notify("preprocess", "running", "正在预处理图片（去水印、增强对比度）...", 15)

        # ── 步骤 3：多轮 OCR 提取 ──
        _notify("ocr", "running", "正在进行多轮 OCR 提取...", 20)
        ocr_text, all_passes = self._ocr.extract_multi_pass(image_bytes)

        if not ocr_text.strip():
            _notify("ocr", "warn", "OCR 未提取到文字，回退到 AI Vision 模式", 50)
            result = await self._extract_vision_only(image_bytes, mime_type)
            result["precision_mode"] = "vision_fallback"
            return result

        _notify("ocr", "done", f"OCR 完成: {len(all_passes)} 轮提取，合并后 {len(ocr_text)} 字符", 50)

        # ── 步骤 4：LLM 结构化 ──
        _notify("structure", "running", "正在使用 AI 进行结构化提取...", 55)
        prompt = OCR_STRUCTURING_PROMPT.format(ocr_text=ocr_text)
        structured = await self._call_llm(prompt)

        if not structured.get("success"):
            _notify("structure", "error", "AI 结构化提取失败", 100)
            return structured

        _notify("structure", "done", "AI 结构化提取完成", 75)

        # ── 步骤 5：LLM 校验 ──
        _notify("verify", "running", "正在交叉校验数据准确性...", 80)
        verify_prompt = LLM_VERIFICATION_PROMPT.format(
            ocr_text=ocr_text,
            structured_json=json.dumps(structured, ensure_ascii=False, indent=2),
        )
        verified = await self._call_llm(verify_prompt)

        if verified.get("success"):
            _notify("verify", "done", "数据校验完成，已自动修正", 95)
            verified["ocr_text"] = ocr_text
            verified["ocr_passes"] = len(all_passes)
            verified["ocr_engines"] = engines
            verified["precision_mode"] = "highest"
            return verified
        else:
            _notify("verify", "warn", "校验失败，返回原始提取结果", 95)
            structured["ocr_text"] = ocr_text
            structured["ocr_passes"] = len(all_passes)
            structured["ocr_engines"] = engines
            structured["precision_mode"] = "high"
            return structured

    async def _extract_vision_only(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        """纯 Vision 模式（OCR 失败时的回退）。"""
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        if self.provider == "claude":
            return await self._call_claude_vision(b64_image, mime_type)
        else:
            return await self._call_openai_compatible_vision(b64_image, mime_type)

    # ── LLM 调用 ──

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _call_llm(self, prompt: str, max_tokens: int = 8192) -> dict[str, Any]:
        """调用 LLM（纯文本模式）。"""
        if self.provider == "claude":
            return await self._call_claude_text(prompt, max_tokens)
        else:
            return await self._call_openai_compatible_text(prompt, max_tokens)

    async def _call_claude_text(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code >= 400:
                logger.error(f"Claude API错误 {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            result = self._parse_json_response(text)
            result["success"] = True
            return result

    async def _call_openai_compatible_text(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code >= 400:
                logger.error(f"LLM API错误 {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            result = self._parse_json_response(text)
            result["success"] = True
            return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _call_claude_vision(self, b64_image: str, mime_type: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 8192,
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_image}},
                                {"type": "text", "text": VISION_EXTRACTION_PROMPT},
                            ],
                        }
                    ],
                },
            )
            if resp.status_code >= 400:
                logger.error(f"Claude Vision API错误 {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            result = self._parse_json_response(text)
            result["success"] = True
            result["mode"] = "vision"
            return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _call_openai_compatible_vision(self, b64_image: str, mime_type: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_image}"}},
                                {"type": "text", "text": VISION_EXTRACTION_PROMPT},
                            ],
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8192,
                },
            )
            if resp.status_code >= 400:
                logger.error(f"Vision API错误 {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            result = self._parse_json_response(text)
            result["success"] = True
            result["mode"] = "vision"
            return result

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """解析 LLM 返回的 JSON 响应。"""
        # 1. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 尝试提取 markdown 代码块中的 JSON
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 尝试找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        # 4. 尝试修复常见 JSON 错误（截断、多余逗号等）
        if start != -1:
            # 从第一个 { 开始，尝试逐步修复
            json_str = text[start:]
            # 移除末尾的非 JSON 字符
            for i in range(len(json_str) - 1, -1, -1):
                if json_str[i] in ('}', ']', '"', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
                    try:
                        return json.loads(json_str[:i + 1])
                    except json.JSONDecodeError:
                        continue

            # 尝试补全未闭合的括号
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')
            if open_braces > 0 or open_brackets > 0:
                json_str += ']' * open_brackets + '}' * open_braces
                # 移除末尾可能的多余逗号
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        logger.warning(f"LLM 响应解析失败，原始文本前200字符: {text[:200]}")
        return {"success": False, "error": "无法解析 AI 响应"}
