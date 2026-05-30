"""AI智能提取器：使用LLM自动识别和提取页面中的名单数据。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config.settings import AI_PROVIDERS

# 提取提示词模板
EXTRACTION_PROMPT = """你是一个数据提取专家。请分析以下页面内容，提取其中的研究生招生相关数据。

页面URL: {url}
页面内容:
{content}
{major_filter}

请识别页面中的数据类型并提取：

1. 如果是**复试名单/录取名单/拟录取名单**（包含考生姓名、考生编号等），提取为 records：
{{
  "found": true,
  "list_type": "复试名单" 或 "录取名单",
  "year": 2025,
  "university": "学校名称",
  "records": [
    {{
      "exam_id": "考生编号",
      "name": "姓名",
      "major": "专业名称",
      "initial_score": "初试成绩",
      "retest_score": "复试成绩",
      "total_score": "总分",
      "admission_status": "录取状态"
    }}
  ]
}}

2. 如果是**复试分数线/基本分数线**（包含学科门类、总分线、单科线等），提取为 score_lines：
{{
  "found": true,
  "list_type": "复试分数线",
  "year": 2025,
  "university": "学校名称",
  "score_lines": [
    {{
      "category": "学术学位/专业学位",
      "discipline": "学科门类/专业名称",
      "discipline_code": "专业代码（如有）",
      "total_score": "总分线",
      "score1": "单科1分数线（满分=100分）",
      "score2": "单科2分数线（满分>100分）"
    }}
  ]
}}

3. 如果页面中没有数据但有链接，返回 {{"found": false, "data_url": "链接URL"}}

注意：
- 仔细识别数据类型，分数线数据包含"分数线"、"总分"、"单科"等关键词
- 成绩/分数线字段如果没有就设为null
- 只返回JSON，不要其他文字
"""

CATALOG_PROMPT = """你是一个数据提取专家。请分析以下HTML页面内容，提取其中的研究生招生专业目录数据。

页面URL: {url}
页面内容:
{content}

请提取所有专业的考试科目信息，返回JSON格式：

{{
  "found": true/false,
  "university": "学校名称",
  "year": 2025,
  "subjects": [
    {{
      "department": "所属学院名称",
      "major_code": "专业代码",
      "major_name": "专业名称",
      "research_direction": "研究方向（如有）",
      "subject1": "政治科目名称",
      "subject2": "外语科目名称",
      "subject3": "业务课一名称",
      "subject4": "业务课二名称"
    }}
  ]
}}

注意：
- 如果页面中没有专业目录数据，但有指向目录数据的链接（如"点击查看"、"附件下载"等），返回 {{"found": false, "data_url": "链接URL"}}
- department是该专业所属的学院/院系名称，如"计算机科学与技术学院"
- research_direction是具体研究方向，如果没有则设为空字符串
- 科目名称应尽量完整，如"思想政治理论"而非"政治"
- 只返回JSON，不要其他文字
"""

RETEST_RULES_PROMPT = """你是一个数据提取专家。请分析以下页面内容，提取其中的研究生复试细则/复试办法/复试录取方案。

页面URL: {url}
页面内容:
{content}

请提取复试细则的关键信息，返回JSON格式：

{{
  "found": true/false,
  "university": "学校名称",
  "year": 2025,
  "title": "文件标题，如XX大学2025年硕士研究生复试录取办法",
  "department": "学院名称（如果是校级文件则为空）",
  "major": "专业名称（如果是针对特定专业的细则）",
  "content_summary": "内容摘要，200字以内概括主要信息",
  "retest_format": "复试形式，如：笔试+面试+英语口语",
  "score_composition": "成绩构成，如：初试占60%，复试占40%",
  "retest_content": "复试内容详情，包括笔试科目、面试内容等",
  "other_requirements": "其他要求，如资格审查材料、体检要求等"
}}

注意：
- 如果页面中没有复试细则相关内容，但有指向细则的链接，返回 {{"found": false, "data_url": "链接URL"}}
- title应完整，如"XX大学计算机学院2025年硕士研究生复试工作细则"
- content_summary应简洁概括，不要超过200字
- score_composition应包含初试和复试的占比信息（如有）
- 只返回JSON，不要其他文字
"""

NAVIGATION_PROMPT = """你是研究生招生信息导航专家。分析以下页面，决定下一步操作。

页面URL: {url}
页面标题: {title}
{major_context}

页面中的链接列表:
{link_list}

请判断这个页面的类型并返回JSON：

1. 如果页面直接包含研究生复试名单、录取名单、拟录取名单等数据（表格形式）：
{{"action": "extract", "reason": "页面包含录取名单数据"}}

2. 如果页面包含可能指向名单页面的链接（如各学院招生、通知公告等）：
{{"action": "follow", "links": [{{"url": "链接URL", "text": "链接文字"}}], "reason": "发现了相关链接"}}

3. 如果页面与研究生招生名单无关：
{{"action": "skip", "reason": "页面不相关"}}

注意：
- "follow"时最多返回5个最相关的链接
- 优先关注包含"学院"、"复试"、"录取"、"拟录取"、"名单"、"公示"等关键词的链接
- 只返回JSON，不要其他文字
"""

CATALOG_NAVIGATION_PROMPT = """你是研究生招生信息导航专家。分析以下页面，寻找招生专业目录（考试科目目录）。

页面URL: {url}
页面标题: {title}
{major_context}

页面中的链接列表:
{link_list}

请判断这个页面的类型并返回JSON：

1. 如果页面直接包含研究生招生专业目录、考试科目目录等数据（表格形式，含专业代码、考试科目等）：
{{"action": "extract", "reason": "页面包含专业目录数据"}}

2. 如果页面包含可能指向专业目录页面的链接：
{{"action": "follow", "links": [{{"url": "链接URL", "text": "链接文字"}}], "reason": "发现了相关链接"}}

3. 如果页面与招生专业目录无关：
{{"action": "skip", "reason": "页面不相关"}}

注意：
- 专业目录页面通常包含：专业代码、专业名称、研究方向、考试科目（政治、外语、业务课一、业务课二）
- 优先关注包含"专业目录"、"招生目录"、"考试科目"、"招生简章"、"招生专业"等关键词的链接
- "follow"时最多返回5个最相关的链接
- 只返回JSON，不要其他文字
"""

INFER_DEPT_URL_PROMPT = """你是中国高校网站专家。根据以下信息，推断研究生录取名单可能发布的学院官网地址。

学校名称: {university}
已访问页面标题: {visited_titles}

很多综合性大学的各学院（如软件学院、计算机学院、经济管理学院等）会单独在自己学院官网发布复试名单和录取名单，而不是统一在研究生院发布。

请推断最可能发布研究生录取名单的学院官网URL，返回JSON：

{{
  "urls": [
    {{"url": "https://ss.cs.tsinghua.edu.cn", "name": "软件学院", "reason": "清华大学软件学院官网"}},
    {{"url": "https://www.cs.tsinghua.edu.cn", "name": "计算机学院", "reason": "清华大学计算机学院官网"}}
  ]
}}

注意：
- 只返回你有把握的URL，不确定的不要返回
- 优先返回可能发布录取/复试名单的学院
- URL格式通常是 https://xxx.{{school_short}}.edu.cn 或 https://{{school_short}}.edu.cn/xxx
- 最多返回5个URL
- 只返回JSON，不要其他文字
"""


class AIExtractor:
    """AI智能数据提取器。"""

    def __init__(self, api_key: str, provider: str = "claude", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.provider = provider
        provider_config = AI_PROVIDERS.get(provider, {})
        self.base_url = base_url or provider_config.get("base_url", "")
        self.model = model or provider_config.get("model", "")
        # AI响应缓存 {content_hash: (result, timestamp)}
        self._cache: dict[str, tuple[dict, float]] = {}
        self._cache_ttl = 3600  # 缓存1小时

    def _strip_html(self, content: str) -> str:
        """去除HTML标签、脚本、样式，保留文本内容。"""
        # 移除script和style标签及其内容
        content = re.sub(r'<script[\s\S]*?</script>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<style[\s\S]*?</style>', '', content, flags=re.IGNORECASE)
        # 移除HTML注释
        content = re.sub(r'<!--[\s\S]*?-->', '', content)
        # 移除导航、页脚、侧边栏等非主要内容
        content = re.sub(r'<nav[\s\S]*?</nav>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<footer[\s\S]*?</footer>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<aside[\s\S]*?</aside>', '', content, flags=re.IGNORECASE)
        # 将块级标签转换为换行
        content = re.sub(r'<(br|hr|/p|/div|/tr|/li)[\s/]*>', '\n', content, flags=re.IGNORECASE)
        # 移除所有剩余HTML标签
        content = re.sub(r'<[^>]+>', ' ', content)
        # 清理多余空白
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n', content)
        return content.strip()

    def _truncate_content(self, content: str, limit: int = 15000) -> str:
        """智能截断：优先保留表格内容，预处理HTML减少token。"""
        # 先进行HTML预处理
        stripped = self._strip_html(content)

        if len(stripped) <= limit:
            return stripped

        # 尝试提取所有<table>内容
        tables = re.findall(r'<table[\s\S]*?</table>', content, re.IGNORECASE)
        if tables:
            table_content = "\n".join(tables)
            table_stripped = self._strip_html(table_content)
            if len(table_stripped) <= limit:
                return table_stripped
            # 表格总和超限，按表格边界截断
            result = ""
            for t in tables:
                t_stripped = self._strip_html(t)
                if len(result) + len(t_stripped) > limit:
                    break
                result += t_stripped + "\n"
            if result:
                return result

        # 无表格或表格太大，回退到硬截断
        return stripped[:limit]

    async def extract_admission_list(self, url: str, content: str, major: str = "") -> dict[str, Any]:
        """从页面内容中提取录取名单。"""
        major_filter = f"\n目标专业: {major}\n请只提取该专业相关的数据。" if major else ""
        truncated = self._truncate_content(content)
        prompt = EXTRACTION_PROMPT.format(url=url, content=truncated, major_filter=major_filter)
        result = await self._call_llm(prompt, max_tokens=8192)
        return self._validate_extraction(result)

    async def extract_catalog(self, url: str, content: str) -> dict[str, Any]:
        """从页面内容中提取招生专业目录。"""
        truncated = self._truncate_content(content)
        prompt = CATALOG_PROMPT.format(url=url, content=truncated)
        result = await self._call_llm(prompt, max_tokens=8192)
        return self._validate_extraction(result)

    async def extract_retest_rules(self, url: str, content: str) -> dict[str, Any]:
        """从页面内容中提取复试细则/复试办法。"""
        truncated = self._truncate_content(content)
        prompt = RETEST_RULES_PROMPT.format(url=url, content=truncated)
        result = await self._call_llm(prompt)
        if result.get("found") and not result.get("title"):
            result["found"] = False
            result["reason"] = "未能识别文件标题"
        return result

    async def navigate_page(self, url: str, title: str, links: list[dict[str, str]], major: str = "") -> dict[str, Any]:
        """用AI分析页面结构，决定下一步操作（提取/跟进/跳过）。"""
        # 按相关性排序链接
        nav_keywords = ["招生", "学院", "复试", "录取", "拟录取", "名单", "硕士", "研究生", "公示", "通知"]
        if major:
            nav_keywords.append(major)

        def relevance(link):
            t = link.get("text", "")
            score = sum(1 for kw in nav_keywords if kw in t)
            if len(t) > 50:
                score -= 1
            return -score

        sorted_links = sorted(links, key=relevance)

        # 构建链接列表文本，截断到5000字符
        lines = []
        total = 0
        for link in sorted_links:
            text = link.get("text", "")[:80]
            href = link.get("href", "")
            line = f"- {text} → {href}"
            if total + len(line) > 5000:
                break
            lines.append(line)
            total += len(line)

        link_list = "\n".join(lines) if lines else "(无链接)"

        major_context = f"用户目标专业: {major}" if major else ""
        prompt = NAVIGATION_PROMPT.format(url=url, title=title, link_list=link_list, major_context=major_context)
        result = await self._call_llm(prompt, max_tokens=1024)

        # 校验返回结构
        action = result.get("action", "skip")
        if action not in ("extract", "follow", "skip"):
            result["action"] = "skip"
        if action == "follow":
            # 过滤掉缺少url的链接
            valid_links = [lnk for lnk in result.get("links", []) if lnk.get("url")]
            if not valid_links:
                result["action"] = "skip"
                result["reason"] = result.get("reason", "") + " (未返回有效链接)"
            else:
                result["links"] = valid_links

        return result

    async def navigate_for_catalog(self, url: str, title: str, links: list[dict[str, str]], major: str = "") -> dict[str, Any]:
        """用AI分析页面结构，寻找招生专业目录。"""
        nav_keywords = ["专业目录", "招生目录", "考试科目", "招生简章", "招生专业", "硕士招生", "研究生招生", "目录"]
        if major:
            nav_keywords.append(major)

        def relevance(link):
            t = link.get("text", "")
            score = sum(1 for kw in nav_keywords if kw in t)
            if len(t) > 50:
                score -= 1
            return -score

        sorted_links = sorted(links, key=relevance)

        lines = []
        total = 0
        for link in sorted_links:
            text = link.get("text", "")[:80]
            href = link.get("href", "")
            line = f"- {text} → {href}"
            if total + len(line) > 5000:
                break
            lines.append(line)
            total += len(line)

        link_list = "\n".join(lines) if lines else "(无链接)"

        major_context = f"用户目标专业: {major}" if major else ""
        prompt = CATALOG_NAVIGATION_PROMPT.format(url=url, title=title, link_list=link_list, major_context=major_context)
        result = await self._call_llm(prompt, max_tokens=1024)

        action = result.get("action", "skip")
        if action not in ("extract", "follow", "skip"):
            result["action"] = "skip"
        if action == "follow":
            valid_links = [lnk for lnk in result.get("links", []) if lnk.get("url")]
            if not valid_links:
                result["action"] = "skip"
                result["reason"] = result.get("reason", "") + " (未返回有效链接)"
            else:
                result["links"] = valid_links

        return result

    async def infer_dept_urls(self, university: str, visited_titles: list[str], major: str = "") -> list[dict[str, str]]:
        """根据学校名和已访问页面，推断可能发布录取名单的学院官网URL。"""
        titles_text = "\n".join(f"- {t}" for t in visited_titles[:20]) if visited_titles else "(无)"
        major_hint = ""
        if major:
            major_hint = f"\n用户特别关注专业: {major}。请优先推断该专业所属学院的官网。"
        prompt = INFER_DEPT_URL_PROMPT.format(
            university=university,
            visited_titles=titles_text + major_hint,
        )

        try:
            result = await self._call_llm(prompt, max_tokens=1024)
            urls = result.get("urls", [])
            # 过滤掉明显无效的URL并验证可达性
            valid = []
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                for item in urls:
                    url = item.get("url", "")
                    if not url or not url.startswith("http"):
                        continue
                    try:
                        resp = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})
                        if resp.status_code < 500:
                            valid.append(item)
                        else:
                            logger.warning(f"学院URL返回 {resp.status_code}: {url}")
                    except Exception as e:
                        logger.warning(f"学院URL不可达 {url}: {e}")
            return valid[:5]
        except Exception as e:
            logger.error(f"推断学院URL失败: {e}")
            return []

    def _get_cache_key(self, prompt: str) -> str:
        """生成缓存键。"""
        import hashlib
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached(self, key: str) -> dict | None:
        """获取缓存结果。"""
        import time
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"命中AI缓存: {key[:8]}...")
                return result
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, result: dict):
        """设置缓存。"""
        import time
        self._cache[key] = (result, time.time())
        # 清理过期缓存
        if len(self._cache) > 100:
            now = time.time()
            expired = [k for k, v in self._cache.items() if now - v[1] > self._cache_ttl]
            for k in expired:
                del self._cache[k]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _call_llm(self, prompt: str, max_tokens: int = 4096) -> dict[str, Any]:
        """调用LLM API（支持缓存）。"""
        if not self.api_key:
            return {"found": False, "error": "API Key未配置"}
        if not self.base_url:
            return {"found": False, "error": f"Provider {self.provider} 的API地址未配置"}

        # 检查缓存
        cache_key = self._get_cache_key(prompt)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            if self.provider == "claude":
                result = await self._call_claude(prompt, max_tokens=max_tokens)
            else:
                result = await self._call_openai_compatible(prompt, max_tokens=max_tokens)

            # 缓存成功结果
            if result.get("found"):
                self._set_cache(cache_key, result)

            return result
        except Exception as e:
            error_msg = str(e) or repr(e) or f"未知错误 ({type(e).__name__})"
            logger.error(f"LLM调用失败 [{self.provider}] [{self.model}]: {error_msg}")
            return {"found": False, "error": error_msg}

    async def _call_claude(self, prompt: str, max_tokens: int = 4096) -> dict[str, Any]:
        """调用Claude API。"""
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            return self._parse_json_response(text)

    async def _call_openai_compatible(self, prompt: str, max_tokens: int = 4096) -> dict[str, Any]:
        """调用OpenAI兼容API（适用于DeepSeek、OpenAI等）。"""
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """从LLM响应中解析JSON。"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到第一个{到最后一个}
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(f"LLM响应解析失败，原始文本前200字符: {text[:200]}")
        return {"found": False, "error": "无法解析LLM响应"}

    def _validate_extraction(self, result: dict[str, Any]) -> dict[str, Any]:
        """验证并清理AI提取结果。"""
        if not isinstance(result, dict):
            return {"found": False, "error": "AI返回非字典类型"}

        if not result.get("found"):
            return result

        # 验证录取名单
        records = result.get("records")
        if records is not None:
            if not isinstance(records, list):
                result["records"] = []
                result["found"] = False
                return result
            # 清理每条记录
            valid_records = []
            for r in records:
                if not isinstance(r, dict):
                    continue
                # 必须有姓名或考生编号
                if not r.get("name") and not r.get("exam_id"):
                    continue
                # 清理空字符串为None
                for key in ("initial_score", "retest_score", "total_score"):
                    val = r.get(key)
                    if val == "" or val == "null" or val == "N/A":
                        r[key] = None
                valid_records.append(r)
            result["records"] = valid_records
            if not valid_records:
                result["found"] = False

        # 验证招生目录
        subjects = result.get("subjects")
        if subjects is not None:
            if not isinstance(subjects, list):
                result["subjects"] = []
                result["found"] = False
                return result
            valid_subjects = []
            for s in subjects:
                if not isinstance(s, dict):
                    continue
                # 必须有专业名称或专业代码
                if not s.get("major_name") and not s.get("major_code"):
                    continue
                valid_subjects.append(s)
            result["subjects"] = valid_subjects
            if not valid_subjects:
                result["found"] = False

        # 验证分数线
        score_lines = result.get("score_lines")
        if score_lines is not None:
            if not isinstance(score_lines, list):
                result["score_lines"] = []
                result["found"] = False
                return result
            valid_lines = []
            for sl in score_lines:
                if not isinstance(sl, dict):
                    continue
                # 必须有学科名称
                if not sl.get("discipline"):
                    continue
                valid_lines.append(sl)
            result["score_lines"] = valid_lines
            if not valid_lines:
                result["found"] = False

        return result
