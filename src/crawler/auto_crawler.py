"""自动爬虫：用户只输入学校名称，AI自动完成搜索、发现、提取全流程。"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from loguru import logger
from selectolax.parser import HTMLParser

from src.crawler.ai_extractor import AIExtractor

# 985/211院校研究生院官网映射
GRAD_SCHOOL_URLS = {
    "北京大学": "https://admission.pku.edu.cn",
    "清华大学": "https://yz.tsinghua.edu.cn",
    "中国人民大学": "https://pgs.ruc.edu.cn",
    "北京航空航天大学": "https://yzb.buaa.edu.cn",
    "北京理工大学": "https://grd.bit.edu.cn",
    "北京师范大学": "https://yz.bnu.edu.cn",
    "中央民族大学": "https://grs.muc.edu.cn",
    "中国农业大学": "https://yz.cau.edu.cn",
    "天津大学": "https://yzb.tju.edu.cn",
    "南开大学": "https://yzb.nankai.edu.cn",
    "大连理工大学": "https://gs.dlut.edu.cn",
    "东北大学": "https://yz.neu.edu.cn",
    "吉林大学": "https://zsb.jlu.edu.cn",
    "哈尔滨工业大学": "https://yzb.hit.edu.cn",
    "复旦大学": "https://gsao.fudan.edu.cn",
    "上海交通大学": "https://yzb.sjtu.edu.cn",
    "同济大学": "https://yz.tongji.edu.cn",
    "华东师范大学": "https://yjszs.ecnu.edu.cn",
    "南京大学": "https://yzb.nju.edu.cn",
    "东南大学": "https://yzb.seu.edu.cn",
    "浙江大学": "https://grs.zju.edu.cn",
    "中国科学技术大学": "https://yz.ustc.edu.cn",
    "厦门大学": "https://zs.xmu.edu.cn",
    "山东大学": "https://www.yz.sdu.edu.cn",
    "中国海洋大学": "https://yz.ouc.edu.cn",
    "武汉大学": "https://gs.whu.edu.cn",
    "华中科技大学": "https://gszs.hust.edu.cn",
    "中南大学": "https://gra.csu.edu.cn",
    "湖南大学": "https://gra.hnu.edu.cn",
    "国防科技大学": "https://yjszs.nudt.edu.cn",
    "中山大学": "https://graduate.sysu.edu.cn",
    "华南理工大学": "https://admission.scut.edu.cn",
    "四川大学": "https://yz.scu.edu.cn",
    "电子科技大学": "https://yz.uestc.edu.cn",
    "重庆大学": "https://yz.cqu.edu.cn",
    "西安交通大学": "https://yz.xjtu.edu.cn",
    "西北工业大学": "https://yzb.nwpu.edu.cn",
    "兰州大学": "https://yz.lzu.edu.cn",
    "西北农林科技大学": "https://yjshy.nwafu.edu.cn",
}

# 名单相关关键词
KEYWORDS = [
    "拟录取", "录取名单", "录取公示", "录取结果",
    "复试名单", "复试结果", "复试成绩",
    "硕士研究生.*录取", "硕士.*拟录取",
]


class AutoCrawler:
    """自动爬虫：给定学校名称，自动完成全流程。"""

    def __init__(self, ai_extractor: AIExtractor | None = None):
        self.ai = ai_extractor
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def crawl(self, university: str, year: int = 2025) -> dict[str, Any]:
        """一键采集：给定学校名称，自动完成所有步骤。

        Returns:
            {
                "success": True/False,
                "university": "学校名称",
                "year": 2025,
                "steps": ["步骤1完成", "步骤2完成", ...],
                "results": [...],
                "errors": [...]
            }
        """
        result = {
            "success": False,
            "university": university,
            "year": year,
            "steps": [],
            "results": [],
            "errors": [],
        }

        # 步骤1：找到研究生院官网
        grad_url = GRAD_SCHOOL_URLS.get(university)
        if not grad_url:
            # 尝试搜索
            grad_url = await self._search_grad_school(university)

        if not grad_url:
            result["errors"].append(f"未找到 {university} 的研究生院官网，请手动提供URL")
            return result

        result["steps"].append(f"找到研究生院官网: {grad_url}")

        # 步骤2：发现名单页面
        list_pages = await self._discover_list_pages(grad_url)
        if not list_pages:
            result["errors"].append("未在研究生院官网找到名单页面，尝试搜索学院官网...")
            # 尝试搜索更广范围
            list_pages = await self._search_list_pages(university)

        if not list_pages:
            result["errors"].append("未找到名单页面")
            return result

        result["steps"].append(f"发现 {len(list_pages)} 个候选页面")

        # 步骤3：逐个页面提取数据
        for page in list_pages[:5]:  # 最多处理5个页面
            try:
                extracted = await self._extract_from_page(page, university, year)
                if extracted.get("found"):
                    result["results"].append(extracted)
                    result["steps"].append(f"从 {page['text']} 提取到 {extracted.get('count', 0)} 条数据")
            except Exception as e:
                result["errors"].append(f"处理 {page['text']} 失败: {e}")

        result["success"] = len(result["results"]) > 0
        return result

    async def _search_grad_school(self, university: str) -> str | None:
        """通过搜索找到研究生院官网。"""
        # 简单的URL猜测策略
        patterns = [
            f"https://yz.{university.replace('大学', '').replace('学院', '')}.edu.cn",
            f"https://grs.{university.replace('大学', '').replace('学院', '')}.edu.cn",
            f"https://gs.{university.replace('大学', '').replace('学院', '')}.edu.cn",
        ]

        for url in patterns:
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                    resp = await client.head(url, headers=self.headers)
                    if resp.status_code < 400:
                        return url
            except Exception:
                continue

        return None

    async def _discover_list_pages(self, base_url: str) -> list[dict[str, str]]:
        """从研究生院官网发现名单页面。"""
        pages = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(base_url, headers=self.headers)
                resp.raise_for_status()
                content = resp.text

            tree = HTMLParser(content)

            for link in tree.css("a"):
                href = link.attributes.get("href", "")
                text = link.text(strip=True)

                if not href or not text or len(text) < 2:
                    continue

                # 检查是否匹配关键词
                for pattern in KEYWORDS:
                    if re.search(pattern, text):
                        full_url = urljoin(base_url, href)
                        pages.append({
                            "url": full_url,
                            "text": text,
                            "source": base_url,
                        })
                        break

        except Exception as e:
            logger.error(f"发现页面失败: {e}")

        return pages

    async def _search_list_pages(self, university: str) -> list[dict[str, str]]:
        """更广范围搜索名单页面（可以扩展为使用搜索引擎）。"""
        # 目前返回空，后续可以集成搜索引擎API
        return []

    async def _extract_from_page(self, page: dict, university: str, year: int) -> dict:
        """从页面提取数据。"""
        url = page["url"]

        # 获取页面内容
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            content = resp.text

        # 如果有AI提取器，使用AI
        if self.ai:
            result = await self.ai.extract_admission_list(url, content)
            if result.get("found"):
                result["source_url"] = url
                result["source_text"] = page["text"]
                result["university"] = university
                result["year"] = year
                result["count"] = len(result.get("records", []))
                return result

        # 否则使用规则提取（简单匹配）
        return {"found": False}
