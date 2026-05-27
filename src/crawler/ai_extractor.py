"""AI智能提取器：使用LLM自动识别和提取页面中的名单数据。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from loguru import logger

# 提取提示词模板
EXTRACTION_PROMPT = """你是一个数据提取专家。请分析以下HTML页面内容，提取其中的研究生复试名单或录取名单数据。

页面URL: {url}
页面内容:
{content}

请完成以下任务：
1. 判断页面中是否包含复试名单、录取名单、拟录取名单等数据
2. 如果包含，请提取所有学生的数据
3. 返回JSON格式的结果，结构如下：

{{
  "found": true/false,
  "list_type": "复试名单" 或 "录取名单",
  "year": 2025,
  "university": "学校名称",
  "records": [
    {{
      "exam_id": "考生编号",
      "name": "姓名",
      "major": "专业名称",
      "initial_score": "初试成绩（如有）",
      "retest_score": "复试成绩（如有）",
      "total_score": "总分（如有）",
      "admission_status": "录取状态（如有）"
    }}
  ]
}}

注意：
- 如果页面中没有名单数据，返回 {{"found": false}}
- 如果是PDF链接，请返回 {{"found": false, "pdf_url": "PDF的URL"}}
- 成绩字段如果没有就设为null
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
      "major_code": "专业代码",
      "major_name": "专业名称",
      "subject1": "政治科目名称",
      "subject2": "外语科目名称",
      "subject3": "业务课一名称",
      "subject4": "业务课二名称"
    }}
  ]
}}

注意：
- 如果页面中没有专业目录数据，返回 {{"found": false}}
- 只返回JSON，不要其他文字
"""


class AIExtractor:
    """AI智能数据提取器。"""

    def __init__(self, api_key: str, provider: str = "claude", base_url: str = ""):
        self.api_key = api_key
        self.provider = provider
        self.base_url = base_url or self._get_default_url()

    def _get_default_url(self) -> str:
        if self.provider == "claude":
            return "https://api.anthropic.com/v1/messages"
        elif self.provider == "openai":
            return "https://api.openai.com/v1/chat/completions"
        elif self.provider == "deepseek":
            return "https://api.deepseek.com/v1/chat/completions"
        return ""

    async def extract_admission_list(self, url: str, content: str) -> dict[str, Any]:
        """从页面内容中提取录取名单。"""
        prompt = EXTRACTION_PROMPT.format(url=url, content=content[:15000])
        return await self._call_llm(prompt)

    async def extract_catalog(self, url: str, content: str) -> dict[str, Any]:
        """从页面内容中提取招生专业目录。"""
        prompt = CATALOG_PROMPT.format(url=url, content=content[:15000])
        return await self._call_llm(prompt)

    async def _call_llm(self, prompt: str) -> dict[str, Any]:
        """调用LLM API。"""
        try:
            if self.provider == "claude":
                return await self._call_claude(prompt)
            else:
                return await self._call_openai_compatible(prompt)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return {"found": False, "error": str(e)}

    async def _call_claude(self, prompt: str) -> dict[str, Any]:
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
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            return self._parse_json_response(text)

    async def _call_openai_compatible(self, prompt: str) -> dict[str, Any]:
        """调用OpenAI兼容API（适用于DeepSeek、OpenAI等）。"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
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

        return {"found": False, "error": "无法解析LLM响应"}
