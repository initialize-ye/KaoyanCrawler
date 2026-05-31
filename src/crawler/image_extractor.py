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

OCR_STRUCTURING_PROMPT = """你是一个考研招生数据清洗专家。以下是从考研招生图片中通过 OCR 提取的原始文本。

由于 OCR 识别可能有误差，请你：
1. 修正明显的 OCR 错误（如 0/O、1/l/I、8/B、5/S 混淆）
2. 忽略水印文字（如"灰灰考研"等无关内容）
3. 识别并提取结构化的招生数据
4. 补全缺失的逻辑关系（如根据初试科目推断专业类型）

OCR 原始文本：
{ocr_text}

请提取以下信息并返回 JSON：

{{
  "schoolName": "学校全称",
  "schoolWebsite": "研究生院官网 URL（如有）",
  "duration": "学制（如：3年）",
  "tuition": "学费（如：8000元/年）",
  "scholarship": "奖学金政策（如有）",
  "colleges": [
    {{
      "collegeName": "学院名称",
      "collegeWebsite": "学院官网（如有）",
      "majors": [
        {{
          "majorName": "专业名称",
          "majorCode": "6位专业代码（如 081200）",
          "subjects": ["科目1", "科目2", "科目3", "科目4"],
          "retestScoreLine": "复试分数线（数字）",
          "retestCount": "复试人数（整数）",
          "retestScoreRange": "复试分数区间（如 320-385）",
          "singleSubjectRange": "单科分数区间",
          "plannedEnrollment": "招生人数（整数）",
          "admissionScoreRange": "录取分数区间",
          "specialProgram": "特殊项目（专项计划/校企联合/中外合作/null）",
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

数据清洗规则：
1. 专业代码：必须是6位数字，无法识别则填 null
2. 分数：只保留数字，不带"分"字
3. 分数区间：用"-"连接（如"320-385"）
4. 人数：整数
5. URL：完整格式（http:// 或 https://）
6. 缺失字段：填 null
7. 忽略水印和无关文字
8. 不要遗漏任何学院和专业
9. 只返回 JSON，不要其他文字"""


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

        # 图片预处理参数组合
        pipelines = [
            {"name": "original", "contrast": 1.0, "denoise": False, "binarize": False},
            {"name": "high_contrast", "contrast": 1.8, "denoise": False, "binarize": False},
            {"name": "denoised", "contrast": 1.2, "denoise": True, "binarize": False},
            {"name": "binarized", "contrast": 1.0, "denoise": True, "binarize": True},
            {"name": "enhanced", "contrast": 1.5, "denoise": True, "binarize": True},
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

    def _clean_ocr_text(self, text: str) -> str:
        """清洗 OCR 文本，去除水印标签（保留实际数据内容）。"""
        cleaned = text

        # 1. 去除独立的水印标签（前后是空格、标点或行首行尾）
        # 这些是嵌入在数据间的水印标记，不会跨有用内容
        watermark_tags = [
            r'灰灰考研统计',
            r'灰灰考研',
            r'灰灰考',
            r'皮皮灰统计',
            r'皮皮灰',
            r'东东老[考研码]统计',
            r'东东老码统计',
            r'东东老研统社',
            r'考研统[店计]',
            r'考研统计',
        ]
        for tag in watermark_tags:
            cleaned = re.sub(tag, '', cleaned)

        # 2. 去除整行都是水印/广告的行
        ad_lines = [
            r'^.*免责声明.*官网为准.*$',
            r'^.*所有数据均来源.*公示的信息.*$',
            r'^.*院校文章付费用户.*信息咨询等.*$',
            r'^.*可领取【专属信息更新提醒服务】.*$',
            r'^.*包含：院校改考动态提醒.*$',
            r'^.*可至灰灰考研公众号.*$',
            r'^.*如有错误.*请以官网为准.*$',
            r'^.*灰灰公众号后台回复【院校】.*$',
            r'^.*后台回复【院校名称】.*$',
            r'^.*后台回复【院校】.*$',
            r'^.*关注灰灰考研.*$',
            r'^.*标记/代表.*暂时未找到.*$',
            r'^.*如信息偏差.*$',
            r'^.*灰灰考研更新.*$',
            r'皮皮灰一志愿被刷统计->',
            r'皮皮信息-.*$',
        ]
        for pattern in ad_lines:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)

        # 3. 清理空格和空行
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)
        cleaned = re.sub(r'^\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s+$', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        return cleaned

    async def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/png", progress_callback=None) -> dict[str, Any]:
        """从图片中提取结构化数据（纯 OCR 模式）。"""

        def _notify(step: str, status: str, detail: str, progress: int):
            logger.info(f"[{step}] {status}: {detail}")
            if progress_callback:
                progress_callback(step, status, detail, progress)

        if not self.api_key:
            return {"success": False, "error": "API Key未配置"}

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
            _notify("clean", "done", f"清洗完成: {len(ocr_text)} → {len(cleaned_text)} 字符", 60)

            # LLM 结构化
            if self.api_key:
                _notify("structure", "running", "正在使用 AI 进行数据清洗和结构化...", 65)
                prompt = OCR_STRUCTURING_PROMPT.format(ocr_text=cleaned_text)
                result = await self._call_llm(prompt)

                if result.get("success"):
                    _notify("structure", "done", "AI 结构化完成", 95)
                    result["ocr_text"] = ocr_text
                    result["cleaned_text"] = cleaned_text
                    result["ocr_passes"] = passes
                    result["ocr_engines"] = engines
                    result["mode"] = "ocr+llm"
                    return result
                else:
                    _notify("structure", "warn", "AI 结构化失败，返回原始文本", 90)
            else:
                _notify("structure", "skip", "未配置 AI，仅返回 OCR 文本", 90)

            # 无 AI 或 AI 失败时，返回基本结构
            return {
                "success": True,
                "ocr_text": ocr_text,
                "cleaned_text": cleaned_text,
                "ocr_passes": passes,
                "ocr_engines": engines,
                "mode": "ocr_only",
                "schoolName": None,
                "colleges": [],
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
            logger.debug(f"LLM 响应前500字符: {text[:500]}")
            result = self._parse_json_response(text)
            # 只有解析成功才设置 success=True
            if "error" not in result:
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
            logger.debug(f"LLM 响应前500字符: {text[:500]}")
            result = self._parse_json_response(text)
            # 只有解析成功才设置 success=True
            if "error" not in result:
                result["success"] = True
            return result

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """解析 LLM 返回的 JSON。"""
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
            # 统计未闭合的括号
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')
            if open_braces > 0 or open_brackets > 0:
                # 移除末尾可能的不完整键值对
                json_str = re.sub(r',\s*"[^"]*:\s*"[^"]*$', '', json_str)
                json_str = re.sub(r',\s*"[^"]*$', '', json_str)
                json_str = re.sub(r',\s*$', '', json_str)
                json_str = re.sub(r':\s*$', ': null', json_str)
                # 补全括号
                json_str += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                # 再试一次，移除更多末尾内容
                json_str = re.sub(r'[\s,]*"[^"]*$', '', json_str)
                json_str += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        logger.warning(f"JSON 解析失败，原始文本前500字符: {text[:500]}")
        return {"error": "无法解析 AI 响应"}
