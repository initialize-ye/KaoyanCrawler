"""URL自动发现：从研究生院首页找到复试/录取名单链接。"""

from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from loguru import logger
from selectolax.parser import HTMLParser

# 关键词匹配规则
KEYWORDS = {
    "admission_list": [
        "拟录取", "录取名单", "录取公示", "录取结果",
        "复试名单", "复试结果", "复试成绩",
        "硕士研究生.*录取", "硕士.*拟录取",
    ],
    "program_catalog": [
        "招生专业目录", "专业目录", "招生目录",
        "考试科目", "初试科目",
    ],
}


async def discover_links(base_url: str) -> dict[str, list[dict[str, str]]]:
    """从给定URL页面中发现相关链接。

    返回格式:
    {
        "admission_list": [{"url": "...", "text": "...", "keyword": "..."}],
        "program_catalog": [{"url": "...", "text": "...", "keyword": "..."}],
    }
    """
    results: dict[str, list[dict[str, str]]] = {
        "admission_list": [],
        "program_catalog": [],
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(base_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            content = resp.text
    except Exception as e:
        logger.error(f"获取页面失败: {e}")
        return results

    tree = HTMLParser(content)
    links = tree.css("a")

    seen_urls = set()

    for link in links:
        href = link.attributes.get("href", "")
        text = link.text(strip=True)

        if not href or not text or len(text) < 2:
            continue

        # 构建完整URL
        full_url = urljoin(base_url, href)

        # 去重
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # 匹配关键词
        for category, patterns in KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    results[category].append({
                        "url": full_url,
                        "text": text,
                        "matched_keyword": pattern,
                    })
                    break

    # 按相关性排序（关键词匹配度高的在前）
    for category in results:
        results[category].sort(key=lambda x: len(x["text"]), reverse=True)

    return results


async def discover_multi_page(base_url: str, max_depth: int = 2) -> dict[str, list[dict]]:
    """多层页面发现：先访问首页，再对候选链接做二次发现。

    适用于首页只列出年份/分类入口，实际名单在子页面的情况。
    """
    results = await discover_links(base_url)

    # 如果首页已经找到足够多的结果，直接返回
    total = sum(len(v) for v in results.values())
    if total >= 3:
        return results

    # 否则，对首页发现的链接做二次探索
    if max_depth > 0:
        candidate_urls = set()
        for category_results in results.values():
            for item in category_results:
                candidate_urls.add(item["url"])

        # 也探索首页中可能的子页面入口
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(base_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                tree = HTMLParser(resp.text)
                for link in tree.css("a"):
                    href = link.attributes.get("href", "")
                    text = link.text(strip=True)
                    if any(kw in text for kw in ["招生", "通知", "公告", "信息"]):
                        full_url = urljoin(base_url, href)
                        candidate_urls.add(full_url)
        except Exception:
            pass

        # 二次探索
        for url in list(candidate_urls)[:5]:  # 最多探索5个子页面
            sub_results = await discover_links(url)
            for category, items in sub_results.items():
                existing_urls = {r["url"] for r in results[category]}
                for item in items:
                    if item["url"] not in existing_urls:
                        results[category].append(item)

    return results
