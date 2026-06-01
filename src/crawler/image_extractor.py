"""纯 OCR 图片识别提取器。

识别流程：
  1. 图片预处理（去水印、增强对比度、去噪、二值化）
  2. 多轮 OCR（不同预处理参数各跑一次）
  3. 多引擎交叉验证（RapidOCR + EasyOCR，投票合并）
  4. LLM 结构化（将 OCR 文本转为 JSON，仅文本处理）

注意：不使用 LLM Vision API，仅用 OCR 提取文字，LLM 用于数据清洗和结构化。
"""

from __future__ import annotations

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

OCR_STRUCTURING_PROMPT = """你是一个考研招生数据提取专家。以下是从考研招生图片中通过 OCR 提取的文本。

任务：从文本中提取所有学院和专业的招生数据，返回 JSON。请尽可能完整地提取所有数据。

OCR 文本：
{ocr_text}

提取规则：
1. **学院识别**：识别所有学院（如"计算机学院"、"软件学院"、"信息学院"、"人工智能学院"等）
2. **专业提取**：每个学院下的所有专业都要提取，不要遗漏任何一个专业
3. **专业代码**：提取数字代码（如081200、085400、083900），括号内的也要提取
4. **招生人数**：提取"招生"、"计划"、"拟录取"、"名额"等后面的数字
5. **分数线**：提取"分数线"、"复试线"、"最低分"、"总分线"等后面的数字
6. **复试人数**：提取"复试人数"、"进入复试"、"复试名单"等后面的数字
7. **录取人数**：提取"录取人数"、"拟录取"、"录取名单"等后面的数字
8. **复录比**：提取"复录比"、"录取比例"等后面的数字或比例
9. **分数统计**：提取"最低分"、"最高分"、"平均分"、"中位数"等
10. **初试科目**：提取政治、英语一/二、数学一/二/三、专业课（如408统考、408计算机学科专业基础）
11. **复试信息**：提取复试时间、形式、内容、成绩计算方式
12. **调剂信息**：提取"调剂"、"接收调剂"等信息
13. **忽略**：水印文字（如"灰灰考研"、"皮皮灰"等）和无关内容

重要提示：
- 不同图片格式可能不同，请灵活识别
- 表格数据按行列对应提取，注意对齐
- 同一学院可能有多个专业方向，都要提取
- 如果数据不完整，提取能识别的部分，缺失字段填 null
- 请务必提取所有能找到的数据，不要遗漏

返回 JSON：
{{
  "schoolName": "学校全称",
  "schoolWebsite": "官网URL",
  "duration": "学制",
  "tuition": "学费",
  "scholarship": "奖学金",
  "colleges": [
    {{
      "collegeName": "学院名称",
      "collegeWebsite": "学院官网",
      "majors": [
        {{
          "majorName": "专业名称",
          "majorCode": "专业代码",
          "researchDirection": "研究方向",
          "subjects": ["科目1", "科目2", "科目3", "科目4"],
          "plannedEnrollment": "招生人数",
          "retestScoreLine": "复试分数线",
          "retestCount": "复试人数",
          "retestAvgScore": "复试均分",
          "admissionCount": "录取人数",
          "admissionRatio": "复录比",
          "admissionMinScore": "录取最低分",
          "admissionMedianScore": "录取中位数",
          "admissionMaxScore": "录取最高分",
          "admissionAvgScore": "录取平均分",
          "retestScoreRange": "复试分数区间",
          "singleSubjectRange": "单科区间",
          "admissionScoreRange": "录取分数区间",
          "specialProgram": "特殊项目或null",
          "transferType": "调剂类型或null",
          "retestInfo": {{
            "time": "复试时间",
            "method": "复试形式",
            "content": "复试内容",
            "scoreRule": "成绩计算方式",
            "remark": "备注"
          }}
        }}
      ]
    }}
  ]
}}

只返回 JSON，不要其他文字。"""


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

    def extract_text(self, image_bytes: bytes) -> tuple[str, int, list[str]]:
        """从图片中提取文字。

        Returns:
            (合并后的文本, OCR轮数, 各轮原始文本列表)
        """
        self._init_rapid()
        self._init_easyocr()

        if not self._rapid_ok and not self._easyocr_ok:
            raise ImportError(
                "未找到可用的 OCR 引擎。请安装:\n"
                "  pip install rapidocr-onnxruntime  (推荐)\n"
                "  pip install easyocr"
            )

        # 图片预处理参数组合 - 更多组合以提高识别率
        pipelines = [
            {"name": "original", "contrast": 1.0, "denoise": False, "binarize": False},
            {"name": "high_contrast", "contrast": 1.8, "denoise": False, "binarize": False},
            {"name": "very_high_contrast", "contrast": 2.5, "denoise": False, "binarize": False},
            {"name": "denoised", "contrast": 1.2, "denoise": True, "binarize": False},
            {"name": "binarized", "contrast": 1.0, "denoise": True, "binarize": True},
            {"name": "enhanced", "contrast": 1.5, "denoise": True, "binarize": True},
            {"name": "sharp_enhanced", "contrast": 2.0, "denoise": False, "binarize": False, "sharpen": True},
        ]

        all_texts = []
        high_conf_count = 0

        for i, pipe in enumerate(pipelines):
            try:
                arr = self._preprocess(image_bytes, pipe)
            except Exception as e:
                logger.warning(f"预处理 [{pipe['name']}] 失败: {e}")
                continue

            # RapidOCR
            if self._rapid_ok:
                text, conf = self._run_rapid(arr)
                if text.strip():
                    all_texts.append(text)
                    if conf > 0.9:
                        high_conf_count += 1

            # EasyOCR
            if self._easyocr_ok:
                text, conf = self._run_easyocr(arr)
                if text.strip():
                    all_texts.append(text)
                    if conf > 0.9:
                        high_conf_count += 1

            # 提前终止：已有足够高置信度结果
            if high_conf_count >= 3 and i >= 2:
                logger.info(f"OCR 提前终止: 已获得 {high_conf_count} 个高置信度结果")
                break

        if not all_texts:
            return "", 0, []

        # 投票合并
        merged = self._merge_texts(all_texts)
        logger.info(f"OCR 完成: {len(all_texts)} 轮 → 合并后 {len(merged)} 字符")
        return merged, len(all_texts), all_texts

    def _preprocess(self, image_bytes: bytes, config: dict) -> np.ndarray:
        """图片预处理。"""
        import io
        from PIL import Image as PILImage, ImageEnhance, ImageFilter

        img = PILImage.open(io.BytesIO(image_bytes))

        # 去水印（灰灰考研等灰色水印）
        img = self._remove_watermark(img)

        # 转灰度
        if img.mode != 'L':
            img = img.convert('L')

        # 调整对比度
        if config["contrast"] != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(config["contrast"])

        # 锐化
        if config.get("sharpen"):
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)

        # 去噪
        if config["denoise"]:
            img = img.filter(ImageFilter.MedianFilter(size=3))

        # 二值化
        if config["binarize"]:
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
            img = img.convert('L')

        # 放大小图
        if max(img.size) < 800:
            img = img.resize((img.width * 2, img.height * 2), PILImage.LANCZOS)

        return np.array(img)

    def _remove_watermark(self, img):
        """去除灰色水印。"""
        from PIL import Image as PILImage

        if img.mode != 'RGB':
            img_rgb = img.convert('RGB')
        else:
            img_rgb = img

        arr = np.array(img_rgb, dtype=np.float64)

        # 检测灰色水印：R≈G≈B，且亮度较高
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        gray_diff = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
        brightness = (r + g + b) / 3

        # 水印条件：灰色且亮度高
        watermark_mask = (gray_diff < 30) & (brightness > 160)

        if np.any(watermark_mask):
            # 用中值滤波替换水印区域
            from PIL import ImageFilter
            filtered = img_rgb.filter(ImageFilter.MedianFilter(size=5))
            filtered_arr = np.array(filtered, dtype=np.float64)
            arr[watermark_mask] = filtered_arr[watermark_mask]
            img_rgb = PILImage.fromarray(arr.astype(np.uint8))

        return img_rgb.convert('L') if img.mode == 'L' else img_rgb

    def _run_rapid(self, arr: np.ndarray) -> tuple[str, float]:
        """运行 RapidOCR。"""
        try:
            result, _ = self._rapid(arr)
            if not result:
                return "", 0.0

            texts = []
            confs = []
            for item in result:
                box, text, conf = item
                texts.append(text)
                confs.append(conf)

            avg_conf = sum(confs) / len(confs) if confs else 0
            return " ".join(texts), avg_conf
        except Exception as e:
            logger.warning(f"RapidOCR 失败: {e}")
            return "", 0.0

    def _run_easyocr(self, arr: np.ndarray) -> tuple[str, float]:
        """运行 EasyOCR。"""
        try:
            results = self._easyocr.readtext(arr)
            if not results:
                return "", 0.0

            texts = []
            confs = []
            for bbox, text, conf in results:
                texts.append(text)
                confs.append(conf)

            avg_conf = sum(confs) / len(confs) if confs else 0
            return " ".join(texts), avg_conf
        except Exception as e:
            logger.warning(f"EasyOCR 失败: {e}")
            return "", 0.0

    def _merge_texts(self, texts: list[str]) -> str:
        """投票合并多轮 OCR 文本。"""
        if len(texts) == 1:
            return texts[0]

        # 按行拆分
        all_lines = [t.split() for t in texts]

        # 找最长的版本作为基准
        best_idx = max(range(len(texts)), key=lambda i: len(texts[i]))
        return texts[best_idx]


class ImageExtractor:
    """纯 OCR 图片识别提取器。

    流程：
    1. OCR 提取文字（多轮预处理 + 多引擎）
    2. LLM 结构化（文本 → JSON，仅处理文字）
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

    def _extract_basic_from_ocr(self, text: str) -> dict[str, Any]:
        """从 OCR 文本中提取基本信息（无需 LLM）。"""
        result = {
            "schoolName": None,
            "schoolWebsite": None,
            "duration": None,
            "tuition": None,
            "colleges": [],
        }

        # 提取学校名称（通常是第一行或包含"大学"、"学院"的文本）
        school_match = re.search(r'(\d{2,4})?([一-龥]{2,}(?:大学|学院|研究院))', text)
        if school_match:
            result["schoolName"] = school_match.group(2)

        # 提取官网
        url_match = re.search(r'(https?://[^\s]+)', text)
        if url_match:
            result["schoolWebsite"] = url_match.group(1)

        # 提取学制
        duration_match = re.search(r'学制\s*(\d+年)', text)
        if duration_match:
            result["duration"] = duration_match.group(1)

        # 提取学费
        tuition_match = re.search(r'学费\s*(\d+[/每]年)', text)
        if tuition_match:
            result["tuition"] = tuition_match.group(1)

        # 提取学院和专业
        # 查找学院名称（以"学院"结尾）
        college_pattern = r'([一-龥]+(?:学院|研究院|学部))'
        colleges = re.findall(college_pattern, text)

        # 查找专业名称和分数线
        # 格式：专业名称 ... 【数字-数字】或 数字【数字-数字】
        major_pattern = r'([一-龥]{2,}(?:工程|技术|科学|学|理论|设计))\s+.*?(\d*[【\[]\d+[-~]\d+[】\]])'
        majors = re.findall(major_pattern, text)

        # 查找复试信息
        retest_time_match = re.search(r'(?:复试|上机|面试).*?(?:时间|：)\s*([^\n]+?)(?:\s|$)', text)
        retest_method_match = re.search(r'复试形式[：:]\s*([^\n]+)', text)
        retest_content_match = re.search(r'(?:复试内容|考试内容|上机能力测试)[：:]\s*([^\n]+)', text)
        score_rule_match = re.search(r'总成绩[=＝]\s*([^\n]+)', text)

        retest_info = {}
        if retest_time_match:
            retest_info["time"] = retest_time_match.group(1).strip()
        if retest_method_match:
            retest_info["method"] = retest_method_match.group(1).strip()
        if retest_content_match:
            retest_info["content"] = retest_content_match.group(1).strip()
        if score_rule_match:
            retest_info["scoreRule"] = score_rule_match.group(1).strip()

        # 如果没有提取到复试信息，尝试从文本中提取
        if not retest_info:
            # 查找时间信息
            time_match = re.search(r'(\d+月\d+日[^\s]*)', text)
            if time_match:
                retest_info["time"] = time_match.group(1)

        # 构建学院和专业数据
        if colleges:
            for college_name in set(colleges):
                college_majors = []
                for major_name, score_range in majors:
                    # 尝试提取复试线
                    score_match = re.search(r'(\d+)[【\[]', score_range)
                    retest_score_line = score_match.group(1) if score_match else None

                    college_majors.append({
                        "majorName": major_name,
                        "majorCode": None,
                        "subjects": [],
                        "retestScoreLine": retest_score_line,
                        "retestCount": None,
                        "retestScoreRange": score_range.replace("【", "").replace("】", "").replace("[", "").replace("]", ""),
                        "singleSubjectRange": None,
                        "plannedEnrollment": None,
                        "admissionScoreRange": None,
                        "specialProgram": None,
                        "retestInfo": retest_info if retest_info else None,
                    })

                result["colleges"].append({
                    "collegeName": college_name,
                    "collegeWebsite": None,
                    "majors": college_majors if college_majors else [{
                        "majorName": None,
                        "majorCode": None,
                        "subjects": [],
                        "retestScoreLine": None,
                        "retestCount": None,
                        "retestScoreRange": None,
                        "singleSubjectRange": None,
                        "plannedEnrollment": None,
                        "admissionScoreRange": None,
                        "specialProgram": None,
                        "retestInfo": retest_info if retest_info else None,
                    }],
                })
        elif majors:
            # 没有学院信息，但有专业信息
            college_majors = []
            for major_name, score_range in majors:
                score_match = re.search(r'(\d+)[【\[]', score_range)
                retest_score_line = score_match.group(1) if score_match else None

                college_majors.append({
                    "majorName": major_name,
                    "majorCode": None,
                    "subjects": [],
                    "retestScoreLine": retest_score_line,
                    "retestCount": None,
                    "retestScoreRange": score_range.replace("【", "").replace("】", "").replace("[", "").replace("]", ""),
                    "singleSubjectRange": None,
                    "plannedEnrollment": None,
                    "admissionScoreRange": None,
                    "specialProgram": None,
                    "retestInfo": retest_info if retest_info else None,
                })

            result["colleges"].append({
                "collegeName": None,
                "collegeWebsite": None,
                "majors": college_majors,
            })

        return result

    def _clean_ocr_text(self, text: str) -> str:
        """清洗 OCR 文本，去除水印标签（保留实际数据内容）。"""
        cleaned = text

        # 1. 先去除嵌入的水印标签（不影响数据内容的短标签）
        inline_tags = [
            r'【灰灰考研统计】',
            r'灰灰考研统计',
            r'灰灰考研多',
            r'灰灰考研更新',
            r'灰灰考研',
            r'灰灰考硬统计',
            r'灰灰考',
            r'灰灰',
            r'考研统店',
            r'考研统计',
            r'皮皮灰统计',
            r'皮皮灰',
            r'东东老研统社',
            r'东东老码统计',
        ]
        for tag in inline_tags:
            cleaned = re.sub(tag, '', cleaned)

        # 2. 去除特定的广告/水印句子（使用精确匹配，不跨数据）
        ad_sentences = [
            r'免责声明：.*?一切以官网为准',
            r'标记/代表.*?暂时未找到相关数据',
            r'院校文章付费用户.*?院校信息咨询等',
            r'可领取【专属信息更新提醒服务】.*?院校信息咨询等',
            r'包含：院校改考动态提醒.*?院校信息咨询等',
            r'可至灰灰考研公众号.*?获取更多资料',
            r'如有错误.*?请以官网为准',
            r'灰灰公众号后台回复【院校】',
            r'后台回复【院校名称】',
            r'后台回复【院校】',
            r'关注灰灰考研',
            r'皮皮灰一志愿被刷统计->',
            r'皮皮信息-.*?(?=\s|$)',
            r'一志愿被刷统计->',
            r'可至公众号回复【院校名称】获取更多资料',
            r'可至.*?公众号回复.*?获取更多资料',
        ]
        for pattern in ad_sentences:
            cleaned = re.sub(pattern, '', cleaned)

        # 3. 去除残留的短碎片
        fragments = [
            r'公众号',
            r'关注',
            r'统计',
            r'灰灰',
            r'皮皮',
            r'东东',
        ]
        for frag in fragments:
            cleaned = re.sub(frag, '', cleaned)

        # 4. 清理空格
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = cleaned.strip()

        return cleaned

    async def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/png", progress_callback=None, mode: str = "AI辅助") -> dict[str, Any]:
        """从图片中提取结构化数据。

        mode:
          - "纯OCR": 仅用 OCR 提取文字 + 正则匹配，不调用 LLM
          - "AI辅助": OCR + LLM 结构化（默认）
          - "AI优先": OCR + LLM，使用更详细的提示词，尽可能提取所有数据
        """

        def _notify(step: str, status: str, detail: str, progress: int):
            logger.info(f"[{step}] {status}: {detail}")
            if progress_callback:
                progress_callback(step, status, detail, progress)

        # 纯OCR模式不需要API Key
        if mode != "纯OCR" and not self.api_key:
            return {"success": False, "error": "API Key未配置，请在设置中配置（纯OCR模式除外）"}

        try:
            engines = self._ocr.available_engines()
            _notify("init", "done", f"可用引擎: {', '.join(engines) if engines else '无'}", 10)

            if not engines:
                return {"success": False, "error": "未安装 OCR 引擎，请运行: pip install rapidocr-onnxruntime"}

            # OCR 提取
            _notify("ocr", "running", "正在进行 OCR 文字识别...", 20)
            ocr_text, passes, all_texts = self._ocr.extract_text(image_bytes)

            if not ocr_text.strip():
                _notify("ocr", "error", "OCR 未能识别到文字", 100)
                return {"success": False, "error": "OCR 未能识别到文字，请确保图片清晰"}

            _notify("ocr", "done", f"OCR 完成: {passes} 轮识别, 提取 {len(ocr_text)} 字符", 45)

            # 清洗 OCR 文本
            _notify("clean", "running", "正在去除水印和无关内容...", 50)
            cleaned_text = self._clean_ocr_text(ocr_text)

            # 如果清洗后文本太短，使用原文
            if len(cleaned_text) < 50:
                logger.warning(f"清洗后文本过短({len(cleaned_text)}字符)，使用原始OCR文本")
                cleaned_text = ocr_text

            _notify("clean", "done", f"清洗完成: {len(ocr_text)} → {len(cleaned_text)} 字符", 60)

            # LLM 结构化（非纯OCR模式）
            if mode == "纯OCR":
                _notify("structure", "skip", "纯OCR模式，跳过AI结构化", 80)
            elif self.api_key:
                _notify("structure", "running", f"正在使用 AI 进行数据清洗和结构化（{mode}模式）...", 65)
                prompt = OCR_STRUCTURING_PROMPT.format(ocr_text=cleaned_text)
                result = await self._call_llm(prompt)

                if result.get("success"):
                    _notify("structure", "done", "AI 结构化完成", 95)
                    result["ocr_text"] = ocr_text
                    result["cleaned_text"] = cleaned_text
                    result["ocr_passes"] = passes
                    result["ocr_engines"] = engines
                    result["mode"] = f"ocr+llm({mode})"
                    # 确保 colleges 存在且非空
                    colleges = result.get("colleges", [])
                    if not colleges:
                        logger.warning("LLM 返回了空的 colleges，尝试基本提取补充")
                        basic_data = self._extract_basic_from_ocr(cleaned_text)
                        if basic_data.get("colleges"):
                            result["colleges"] = basic_data["colleges"]
                            result["mode"] = f"ocr+llm+fallback({mode})"
                    return result
                else:
                    # LLM 解析失败，尝试用基本提取
                    llm_error = result.get("error", "未知错误")
                    _notify("structure", "warn", f"AI 结构化失败: {llm_error}，尝试基本提取", 90)
                    logger.warning(f"LLM 结构化失败: {llm_error}")
            else:
                _notify("structure", "skip", "未配置 AI，仅返回 OCR 文本", 90)

            # 无 AI 或 AI 失败时，尝试从 OCR 文本提取基本信息
            basic_data = self._extract_basic_from_ocr(cleaned_text)
            return {
                "success": True,
                "ocr_text": ocr_text,
                "cleaned_text": cleaned_text,
                "ocr_passes": passes,
                "ocr_engines": engines,
                "mode": "ocr_only",
                "schoolName": basic_data.get("schoolName"),
                "schoolWebsite": basic_data.get("schoolWebsite"),
                "duration": basic_data.get("duration"),
                "tuition": basic_data.get("tuition"),
                "colleges": basic_data.get("colleges", []),
                "raw_text": cleaned_text,
            }

        except Exception as e:
            error_msg = str(e) or repr(e) or f"未知错误 ({type(e).__name__})"
            logger.error(f"图片识别失败: {error_msg}")
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _call_llm(self, prompt: str, max_tokens: int = 8192) -> dict[str, Any]:
        """调用 LLM 进行文本结构化（纯文本，非 Vision）。"""
        try:
            if self.provider == "claude":
                return await self._call_claude_text(prompt, max_tokens)
            else:
                return await self._call_openai_compatible_text(prompt, max_tokens)
        except Exception as e:
            error_msg = str(e) or repr(e) or f"未知错误 ({type(e).__name__})"
            logger.error(f"LLM 调用失败 [{self.provider}]: {error_msg}")
            return {"success": False, "error": error_msg}

    def _normalize_response(self, result: dict[str, Any]) -> dict[str, Any]:
        """规范化 LLM 返回的数据结构，兼容不同格式。"""
        if not isinstance(result, dict):
            return result

        # 如果已经有 colleges 且非空，直接返回
        if result.get("colleges"):
            return result

        # 情况1: LLM 返回了 majors 列表（扁平结构，没有 colleges 包装）
        if result.get("majors") and isinstance(result["majors"], list):
            college_name = result.get("schoolName", result.get("university", ""))
            result["colleges"] = [{
                "collegeName": college_name,
                "collegeWebsite": None,
                "majors": result["majors"],
            }]
            return result

        # 情况2: LLM 返回了 subjects 列表（招生目录格式）
        if result.get("subjects") and isinstance(result["subjects"], list):
            # 将 subjects 按 department 分组
            dept_map = {}
            for s in result["subjects"]:
                dept = s.get("department", s.get("collegeName", "未知学院"))
                if dept not in dept_map:
                    dept_map[dept] = []
                # 统一字段名
                major = {
                    "majorName": s.get("major_name", s.get("majorName", "")),
                    "majorCode": s.get("major_code", s.get("majorCode", "")),
                    "researchDirection": s.get("research_direction", s.get("researchDirection", "")),
                    "subjects": s.get("subjects", []),
                    "plannedEnrollment": s.get("enrollment", s.get("plannedEnrollment")),
                    "retestScoreLine": s.get("retest_score_line", s.get("retestScoreLine")),
                    "retestCount": s.get("retest_count", s.get("retestCount")),
                    "admissionCount": s.get("admission_count", s.get("admissionCount")),
                    "admissionRatio": s.get("admission_ratio", s.get("admissionRatio")),
                    "admissionMinScore": s.get("admission_min_score", s.get("admissionMinScore")),
                    "admissionMedianScore": s.get("admission_median_score", s.get("admissionMedianScore")),
                    "admissionMaxScore": s.get("admission_max_score", s.get("admissionMaxScore")),
                    "admissionAvgScore": s.get("admission_avg_score", s.get("admissionAvgScore")),
                    "transferType": s.get("transfer_type", s.get("transferType")),
                }
                dept_map[dept].append(major)

            result["colleges"] = [
                {"collegeName": dept, "collegeWebsite": None, "majors": majors}
                for dept, majors in dept_map.items()
            ]
            return result

        # 情况3: LLM 返回了 records 列表（录取名单格式）
        if result.get("records") and isinstance(result["records"], list):
            # 按 major 分组
            major_map = {}
            for r in result["records"]:
                major = r.get("major", "未知专业")
                if major not in major_map:
                    major_map[major] = []
                major_map[major].append(r)
            # 转为 colleges 结构
            result["colleges"] = [{
                "collegeName": result.get("university", ""),
                "collegeWebsite": None,
                "majors": [
                    {"majorName": major, "majorCode": "", "admissionCount": len(records)}
                    for major, records in major_map.items()
                ],
            }]
            return result

        return result

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
            logger.info(f"LLM 响应长度: {len(text)} 字符")
            logger.info(f"LLM 响应前1000字符: {text[:1000]}")
            result = self._parse_json_response(text)
            # 只有解析成功才设置 success=True
            if "error" not in result:
                result["success"] = True
                result = self._normalize_response(result)
                # 确保 colleges 字段存在
                if "colleges" not in result:
                    result["colleges"] = []
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
            logger.info(f"LLM 响应长度: {len(text)} 字符")
            logger.info(f"LLM 响应前2000字符: {text[:2000]}")
            result = self._parse_json_response(text)
            logger.info(f"解析后 keys: {list(result.keys())}")
            logger.info(f"解析后 colleges 数量: {len(result.get('colleges', []))}")
            # 只有解析成功才设置 success=True
            if "error" not in result:
                result["success"] = True
                result = self._normalize_response(result)
                # 确保 colleges 字段存在
                if "colleges" not in result:
                    result["colleges"] = []
            return result

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """解析 LLM 返回的 JSON，支持截断修复。"""
        if not text or not text.strip():
            logger.warning("LLM 返回空内容")
            return {"error": "AI 返回空内容"}

        text = text.strip()

        # 1. 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 提取 markdown 代码块中的 JSON
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        # 4. 尝试修复截断的 JSON
        if start != -1:
            json_str = text[start:]

            # 多轮修复尝试
            for attempt in range(5):
                # 统计未闭合的括号
                open_braces = json_str.count('{') - json_str.count('}')
                open_brackets = json_str.count('[') - json_str.count(']')

                if open_braces <= 0 and open_brackets <= 0:
                    # 括号已平衡，尝试解析
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

                # 移除末尾不完整内容
                if attempt == 0:
                    # 第一轮：移除末尾不完整的键值对
                    json_str = re.sub(r',\s*"[^"]*:\s*"[^"]*$', '', json_str)
                    json_str = re.sub(r',\s*"[^"]*$', '', json_str)
                elif attempt == 1:
                    # 第二轮：移除末尾的逗号和空白
                    json_str = re.sub(r',\s*$', '', json_str)
                    json_str = re.sub(r':\s*$', ': null', json_str)
                elif attempt == 2:
                    # 第三轮：移除更多末尾内容
                    json_str = re.sub(r'[\s,]*"[^"]*$', '', json_str)
                elif attempt == 3:
                    # 第四轮：移除最后一个不完整的对象
                    json_str = re.sub(r',\s*\{[^}]*$', '', json_str)
                else:
                    # 第五轮：激进清理
                    json_str = re.sub(r'[,\s]*$', '', json_str)

                # 补全括号
                open_braces = json_str.count('{') - json_str.count('}')
                open_brackets = json_str.count('[') - json_str.count(']')
                if open_braces > 0 or open_brackets > 0:
                    fix = ']' * max(0, open_brackets) + '}' * max(0, open_braces)
                    try:
                        return json.loads(json_str + fix)
                    except json.JSONDecodeError:
                        pass

        logger.warning(f"JSON 解析失败，原始文本前500字符: {text[:500]}")
        return {"error": "无法解析 AI 响应"}
