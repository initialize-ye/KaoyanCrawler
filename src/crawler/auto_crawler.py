"""自动爬虫：BFS + AI Agent 驱动的多级采集。

使用 async generator 逐步 yield 进度事件，供 SSE 流式推送。
AI Agent 分析每个页面决定：提取数据 / 跟进链接 / 跳过。
"""

from __future__ import annotations

import asyncio
import io
import random
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urljoin, urlparse

import httpx
from loguru import logger
from selectolax.parser import HTMLParser

from src.crawler.ai_extractor import AIExtractor

# ── 常量 ──

MAX_DEPTH = 2          # homepage=0, department=1, list page=2
MAX_TOTAL_PAGES = 15   # 硬上限：总页面访问数
MAX_CONCURRENT = 3     # 每层最大并发数
MAX_LINKS_PER_PAGE = 5 # 每页最多跟进链接数

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

# 名单相关关键词（用于无AI时的回退匹配）
KEYWORDS = [
    "拟录取", "录取名单", "录取公示", "录取结果",
    "复试名单", "复试结果", "复试成绩",
    "硕士研究生.*录取", "硕士.*拟录取",
]

# 专业目录相关关键词
CATALOG_KEYWORDS = [
    "专业目录", "招生目录", "考试科目", "招生简章",
    "招生专业", "硕士招生目录", "研究生招生专业",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# 登录/验证码页面特征
_LOGIN_PATTERNS = re.compile(
    r"统一身份认证|CAS|单点登录|登录系统|请输入密码|验证码|captcha|recaptcha|"
    r"请完成安全验证|访问被拒绝|Access Denied|403 Forbidden",
    re.IGNORECASE,
)
_LOGIN_URL_SEGMENTS = ("/cas/", "/login", "/sso/", "/auth/", "/passport/", "/verify")

# JS渲染页面特征
_JS_RENDER_MARKERS = ('id="app"', "id='app'", 'id="root"', "id='root'", "__nuxt", "__next")


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


@dataclass
class CrawlTask:
    """BFS 队列中的一个待处理页面。"""
    url: str
    text: str           # 链接文字或页面标题
    depth: int          # 0=homepage, 1=department, 2=list page
    source: str = ""    # 父页面URL


class AutoCrawler:
    """自动爬虫：BFS + AI Agent 驱动。"""

    def __init__(self, ai_extractor: AIExtractor | None = None):
        self.ai = ai_extractor
        self.crawl_mode = "admission"  # "admission" or "catalog"

    async def crawl(self, university: str, year: int = 2025, major: str = "", mode: str = "admission"):
        """一键采集：async generator，逐步 yield 进度事件。

        Args:
            mode: "admission" 录取名单, "catalog" 招生专业目录

        Yields:
            {"event": "step", "data": {"step": "...", "status": "...", "detail": "..."}}
            {"event": "result", "data": {...}}
        """
        self.crawl_mode = mode
        results = []
        errors = []
        visited: set[str] = set()
        page_count = 0

        # ── 步骤1：定位研究生院官网 ──
        yield _step_event("定位研究生院官网", "running")

        # 精确匹配 → 模糊匹配
        grad_url = GRAD_SCHOOL_URLS.get(university)
        if not grad_url:
            for name, url in GRAD_SCHOOL_URLS.items():
                if university in name or name in university:
                    grad_url = url
                    logger.info(f"模糊匹配: {university} -> {name}")
                    break
        if not grad_url:
            grad_url = await self._search_grad_school(university)

        if not grad_url:
            msg = f"未找到 {university} 的研究生院官网，请手动提供URL"
            errors.append(msg)
            yield _step_event("定位研究生院官网", "error", msg)
            yield _result_event(False, university, year, [], errors)
            return

        yield _step_event("定位研究生院官网", "done", f"已找到: {grad_url}")

        # ── 步骤2：BFS 遍历 ──
        queue: list[CrawlTask] = [
            CrawlTask(url=grad_url, text="研究生院首页", depth=0)
        ]

        for depth in range(MAX_DEPTH + 1):
            current_level = [t for t in queue if t.depth == depth]
            if not current_level:
                continue

            level_name = ["首页", "学院页面", "名单页面"][depth] if depth < 3 else f"第{depth}层"
            yield _step_event(
                f"AI分析{level_name}", "running",
                f"正在分析 {len(current_level)} 个页面",
            )

            # 并发处理当前层（受 Semaphore 控制）
            semaphore = asyncio.Semaphore(MAX_CONCURRENT)

            async def process_task(task: CrawlTask):
                nonlocal page_count
                if page_count >= MAX_TOTAL_PAGES:
                    return None
                if task.url in visited:
                    return None
                visited.add(task.url)
                page_count += 1

                page_data = await self._fetch_page(task.url)
                if not page_data:
                    return {"action": "skip", "task": task, "reason": "无法获取页面"}

                if page_data.get("blocked"):
                    return {"action": "skip", "task": task, "reason": "页面需要登录/验证码或为JS渲染页面"}

                # PDF 直接进入提取
                if task.url.lower().endswith(".pdf") or page_data.get("is_pdf"):
                    return {"action": "extract", "task": task, "page_data": page_data}

                # AI 导航决策
                links = self._extract_links(task.url, page_data["html"])
                nav = await self._ai_navigate(task.url, page_data["title"], links, major=major)
                nav["task"] = task
                nav["page_data"] = page_data
                return nav

            async def sem_task(task):
                async with semaphore:
                    return await process_task(task)

            nav_results = await asyncio.gather(
                *[sem_task(t) for t in current_level],
                return_exceptions=True,
            )

            # 串行处理结果
            for result in nav_results:
                if isinstance(result, Exception):
                    errors.append(str(result)[:100])
                    continue
                if result is None:
                    continue

                action = result.get("action", "skip")
                task = result["task"]

                if action == "extract":
                    step_name = f"提取数据: {task.text}"
                    yield _step_event(step_name, "running", task.url)
                    try:
                        extracted = await self._extract_page_or_pdf(
                            task, result.get("page_data"), university, year, major=major
                        )
                        if extracted.get("found"):
                            results.append(extracted)
                            count = extracted.get("count", 0)
                            yield _step_event(step_name, "done", f"成功提取 {count} 条数据")
                            # 分页链接检测
                            page_html = result.get("page_data", {}).get("html", "")
                            if page_html and page_count < MAX_TOTAL_PAGES:
                                page_links = self._find_pagination_links(task.url, page_html)
                                for plink in page_links:
                                    if plink not in visited and page_count + len(queue) < MAX_TOTAL_PAGES:
                                        queue.append(CrawlTask(url=plink, text=f"分页: {task.text}", depth=task.depth, source=task.url))
                        else:
                            reason = extracted.get("reason") or extracted.get("error") or "未发现名单数据"
                            yield _step_event(step_name, "error", reason)
                    except Exception as e:
                        yield _step_event(step_name, "error", str(e)[:100])

                elif action == "follow":
                    links_to_follow = result.get("links", [])
                    if links_to_follow:
                        names = ", ".join(lnk.get("text", "")[:20] for lnk in links_to_follow[:5])
                        yield _step_event(
                            f"AI发现 {len(links_to_follow)} 个相关链接: {task.text}",
                            "done", names,
                        )
                    for link in links_to_follow[:MAX_LINKS_PER_PAGE]:
                        if page_count >= MAX_TOTAL_PAGES:
                            break
                        url = link.get("url", "")
                        if url and url not in visited:
                            queue.append(CrawlTask(
                                url=url,
                                text=link.get("text", url),
                                depth=depth + 1,
                                source=task.url,
                            ))

                elif action == "skip":
                    reason = result.get("reason", "页面不相关")
                    if depth > 0:
                        yield _step_event(f"跳过: {task.text}", "done", reason)

            yield _step_event(
                f"AI分析{level_name}", "done",
                f"已访问 {page_count}/{MAX_TOTAL_PAGES} 个页面",
            )

        # ── 步骤3：BFS未找到数据时，搜索学院官网 ──
        if not results and page_count < MAX_TOTAL_PAGES:
            # 优先用搜索引擎发现真实URL（避免AI幻觉）
            yield _step_event("搜索引擎发现学院", "running", "正在搜索相关学院录取名单页面...")
            dept_urls = await self._search_dept_urls(university, major=major)

            if dept_urls:
                yield _step_event("搜索引擎发现学院", "done", f"找到 {len(dept_urls)} 个相关页面")
            else:
                yield _step_event("搜索引擎发现学院", "done", "搜索引擎未找到，尝试AI推断...")
                # 搜索无结果时，回退到AI推断（带URL验证）
                if self.ai:
                    visited_titles = [t.text for t in queue if t.text != "研究生院首页"]
                    dept_urls = await self.ai.infer_dept_urls(university, visited_titles, major=major)

            if dept_urls:
                names = ", ".join(d.get("name", "")[:15] for d in dept_urls[:5])
                source = "搜索引擎" if dept_urls[0].get("source") == "search" else "AI推断"
                yield _step_event("发现学院页面", "done", f"[{source}] 找到 {len(dept_urls)} 个: {names}")

                for dept in dept_urls[:5]:
                    if page_count >= MAX_TOTAL_PAGES:
                        break

                    dept_url = dept["url"]
                    dept_name = dept.get("name", dept_url)
                    if dept_url in visited:
                        continue

                    step_name = f"搜索学院: {dept_name}"
                    yield _step_event(step_name, "running", dept_url)

                    try:
                        dept_result = await self._crawl_dept_site(
                            dept_url, dept_name, university, year,
                            visited, results, errors, major=major,
                        )
                    except Exception as e:
                        logger.error(f"搜索学院失败 {dept_name}: {e}")
                        errors.append(f"{dept_name}: {e}")
                        dept_result = {"found": False, "reason": str(e)}

                    page_count = len(visited)

                    if dept_result.get("found"):
                        yield _step_event(step_name, "done", dept_result.get("reason", f"从 {dept_name} 找到数据"))
                    else:
                        yield _step_event(step_name, "error", dept_result.get("reason", f"{dept_name} 未找到名单"))
            else:
                yield _step_event("发现学院页面", "done", "未找到相关学院页面")

        # ── 去重 ──
        seen_sources: set[str] = set()
        unique_results = []
        for r in results:
            source = r.get("source_url", "")
            if source and source in seen_sources:
                continue
            if source:
                seen_sources.add(source)
            unique_results.append(r)
        results = unique_results

        # ── 汇总 ──
        yield _result_event(len(results) > 0, university, year, results, errors)

    # ── 页面获取 ──

    async def _fetch_page(self, url: str) -> dict | None:
        """获取页面内容，返回 {html, title, is_pdf, blocked} 或 None。"""
        headers = _get_headers()
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers=headers)
                    content_type = resp.headers.get("content-type", "")

                    # 429/503 等待重试
                    if resp.status_code in (429, 503):
                        wait = 2 ** attempt + random.uniform(0, 1)
                        logger.warning(f"HTTP {resp.status_code} for {url}, retry in {wait:.1f}s")
                        await asyncio.sleep(wait)
                        headers = _get_headers()
                        continue

                    resp.raise_for_status()

                    if "pdf" in content_type:
                        return {"html": "", "title": url, "is_pdf": True}

                    text = resp.text
                    final_url = str(resp.url)

                    # 登录/验证码检测
                    if _LOGIN_PATTERNS.search(text[:5000]) or any(
                        seg in final_url.lower() for seg in _LOGIN_URL_SEGMENTS
                    ):
                        logger.warning(f"检测到登录/验证码页面: {url} -> {final_url}")
                        return {"html": text, "title": "", "blocked": True}

                    # JS渲染检测
                    body_stripped = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S)
                    body_stripped = re.sub(r"<style[^>]*>.*?</style>", "", body_stripped, flags=re.S)
                    text_content = re.sub(r"<[^>]+>", "", body_stripped).strip()
                    if len(text_content) < 100 and any(m in text for m in _JS_RENDER_MARKERS):
                        logger.warning(f"疑似JS渲染页面，文本极少: {url}")
                        return {"html": text, "title": "", "blocked": True}

                    tree = HTMLParser(text)
                    title_el = tree.css_first("title")
                    return {
                        "html": text,
                        "title": title_el.text(strip=True) if title_el else url,
                    }
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503) and attempt < 2:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"HTTP {e.response.status_code} for {url}, retry in {wait:.1f}s")
                    await asyncio.sleep(wait)
                    headers = _get_headers()
                    continue
                logger.error(f"获取页面失败 {url}: {e}")
                return None
            except Exception as e:
                logger.error(f"获取页面失败 {url}: {e}")
                return None
        return None

    # ── 链接提取 ──

    def _extract_links(self, base_url: str, html: str) -> list[dict[str, str]]:
        """从HTML提取链接，按相关性排序。"""
        tree = HTMLParser(html)
        links = []
        seen: set[str] = set()

        for a in tree.css("a"):
            href = a.attributes.get("href", "")
            text = a.text(strip=True)
            if not href or not text or len(text) < 2:
                continue
            full_url = urljoin(base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            links.append({"text": text, "href": full_url})

        return links

    _PAGE_RE = re.compile(r"(?:page|p|pg|PageIndex|currentPage)[=\s]*(\d+)", re.I)
    _NEXT_TEXTS = {"下一页", "下页", "next", "›", "»", ">>", ">"}

    def _find_pagination_links(self, base_url: str, html: str) -> list[str]:
        """提取分页链接（下一页 + 页码），返回最多3个URL。"""
        tree = HTMLParser(html)
        results: list[str] = []
        seen: set[str] = set()

        for a in tree.css("a"):
            href = a.attributes.get("href", "")
            text = a.text(strip=True).lower()
            if not href:
                continue
            full = urljoin(base_url, href)
            if full in seen:
                continue

            is_next = text in self._NEXT_TEXTS
            is_page_num = text.isdigit() and 2 <= int(text) <= 50

            if is_next or is_page_num:
                if full != base_url and full not in seen:
                    seen.add(full)
                    results.append(full)
                    if len(results) >= 3:
                        break

        return results

    # ── AI 导航 ──

    async def _ai_navigate(self, url: str, title: str, links: list[dict], major: str = "") -> dict:
        """用AI决定页面下一步操作。无AI时回退到关键词匹配。"""
        if not self.ai:
            return self._keyword_navigate(url, title, links)
        try:
            if self.crawl_mode == "catalog":
                return await self.ai.navigate_for_catalog(url, title, links, major=major)
            return await self.ai.navigate_page(url, title, links, major=major)
        except Exception as e:
            logger.error(f"AI导航失败 {url}: {e}")
            return {"action": "skip", "reason": f"AI导航失败: {e}"}

    def _keyword_navigate(self, url: str, title: str, links: list[dict]) -> dict:
        """无AI时的关键词回退导航。"""
        keywords = CATALOG_KEYWORDS if self.crawl_mode == "catalog" else KEYWORDS
        matched = []
        for link in links:
            for pattern in keywords:
                if re.search(pattern, link.get("text", "")):
                    matched.append({"url": link["href"], "text": link["text"]})
                    break
        if matched:
            return {
                "action": "follow",
                "links": matched[:MAX_LINKS_PER_PAGE],
                "reason": f"关键词匹配到 {len(matched)} 个链接",
            }
        return {"action": "skip", "reason": "未匹配到相关关键词"}

    # ── 数据提取 ──

    async def _extract_page_or_pdf(
        self, task: CrawlTask, page_data: dict | None, university: str, year: int, major: str = ""
    ) -> dict:
        """统一提取调度：HTML 或 PDF。"""
        if not page_data:
            page_data = await self._fetch_page(task.url)
        if not page_data:
            return {"found": False, "reason": "无法获取页面内容"}
        if page_data.get("blocked"):
            return {"found": False, "reason": "页面需要登录/验证码或为JS渲染页面"}

        page_dict = {"url": task.url, "text": task.text}

        if task.url.lower().endswith(".pdf") or page_data.get("is_pdf"):
            return await self._extract_from_pdf(page_dict, university, year, major=major)
        return await self._extract_from_page(page_dict, university, year, major=major, html_content=page_data.get("html"))

    async def _extract_from_page(self, page: dict, university: str, year: int, major: str = "", html_content: str | None = None) -> dict:
        """从HTML页面提取数据。"""
        url = page["url"]

        if html_content:
            content = html_content
        else:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=_get_headers())
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                content = resp.text

            # 检查是否实际上是PDF
            if "pdf" in content_type or content[:5] == "%PDF-":
                return await self._extract_from_pdf(page, university, year)

        if self.ai:
            if self.crawl_mode == "catalog":
                result = await self.ai.extract_catalog(url, content)
            else:
                result = await self.ai.extract_admission_list(url, content, major=major)
            if result.get("found"):
                result["source_url"] = url
                result["source_text"] = page["text"]
                result["university"] = university
                result["year"] = year
                if self.crawl_mode == "catalog":
                    result["count"] = len(result.get("subjects", []))
                else:
                    result["count"] = len(result.get("records", []))
                return result
            if not result.get("reason"):
                result["reason"] = "AI未能从该页面识别出数据"
            return result

        return {"found": False, "reason": "未配置AI提取器"}

    async def _extract_from_pdf(self, page: dict, university: str, year: int, major: str = "") -> dict:
        """下载PDF并用 pdfplumber + AI 提取数据。"""
        url = page["url"]

        try:
            import pdfplumber
        except ImportError:
            return {"found": False, "reason": "未安装pdfplumber，无法处理PDF文件"}

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=_get_headers())
                resp.raise_for_status()
                pdf_bytes = resp.content
        except Exception as e:
            return {"found": False, "reason": f"下载PDF失败: {e}"}

        # 大小检查：超过15MB可能不是名单文件
        if len(pdf_bytes) > 15 * 1024 * 1024:
            return {"found": False, "reason": f"PDF文件过大 ({len(pdf_bytes) // 1024 // 1024}MB)，跳过"}

        try:
            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                max_pages = min(len(pdf.pages), 20)
                for p in pdf.pages[:max_pages]:
                    t = p.extract_text()
                    if t:
                        text_parts.append(t)
            pdf_text = "\n".join(text_parts)
        except Exception as e:
            return {"found": False, "reason": f"解析PDF失败: {e}"}

        if not pdf_text.strip():
            return {"found": False, "reason": "PDF中未提取到文本内容（可能是扫描件）"}

        # 文本质量检查：过多乱码说明是扫描件或加密PDF
        printable_ratio = sum(1 for c in pdf_text[:2000] if c.isprintable() or c.isspace()) / max(len(pdf_text[:2000]), 1)
        if printable_ratio < 0.7:
            return {"found": False, "reason": "PDF文本质量差（可能是扫描件），无法提取"}

        if not pdf_text.strip():
            return {"found": False, "reason": "PDF中未提取到文本内容"}

        if self.ai:
            if self.crawl_mode == "catalog":
                result = await self.ai.extract_catalog(url, pdf_text)
            else:
                result = await self.ai.extract_admission_list(url, pdf_text, major=major)
            if result.get("found"):
                result["source_url"] = url
                result["source_text"] = page["text"]
                result["university"] = university
                result["year"] = year
                if self.crawl_mode == "catalog":
                    result["count"] = len(result.get("subjects", []))
                else:
                    result["count"] = len(result.get("records", []))
                return result
            if not result.get("reason"):
                result["reason"] = "AI未能从PDF中识别出数据"
            return result

        return {"found": False, "reason": "未配置AI提取器，无法处理PDF"}

    # ── 研究生院官网搜索 ──

    async def _search_grad_school(self, university: str) -> str | None:
        """通过URL猜测找到研究生院官网。"""
        short = university.replace("大学", "").replace("学院", "")
        patterns = [
            f"https://yz.{short}.edu.cn",
            f"https://grs.{short}.edu.cn",
            f"https://gs.{short}.edu.cn",
            f"https://yjs.{short}.edu.cn",
            f"https://pgs.{short}.edu.cn",
            f"https://yzb.{short}.edu.cn",
            f"https://gra.{short}.edu.cn",
            f"https://gsas.{short}.edu.cn",
            f"https://yjsc.{short}.edu.cn",
        ]

        async def _check_url(url: str) -> str | None:
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers=_get_headers())
                    if resp.status_code < 400:
                        return url
            except Exception:
                pass
            return None

        # 并发检查所有URL
        results = await asyncio.gather(*[_check_url(u) for u in patterns], return_exceptions=True)
        for r in results:
            if isinstance(r, str):
                return r

        return None

    # ── 搜索引擎发现真实 URL ──

    async def _search_urls(self, query: str, domain_filter: str = ".edu.cn") -> list[str]:
        """通过搜索引擎获取真实URL，避免AI幻觉。"""
        encoded = quote(query)
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        urls = []

        # 尝试 Bing 搜索
        try:
            bing_url = f"https://www.bing.com/search?q={encoded}&count=20"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(bing_url, headers={
                    "User-Agent": ua,
                    "Accept-Language": "zh-CN,zh;q=0.9",
                })
                resp.raise_for_status()
                html = resp.text

            tree = HTMLParser(html)
            for a in tree.css("a[href]"):
                href = a.attributes.get("href") or ""
                if not href or domain_filter not in href or not href.startswith("http"):
                    continue
                # 清理 Bing 重定向链接
                clean = href
                if "&u=" in href:
                    match = re.search(r'&u=a?1?(https?%3A%2F%2F[^\s&]+)', href)
                    if match:
                        clean = unquote(match.group(1))
                    else:
                        clean = unquote(href.split("&u=")[-1])
                if clean.startswith("http") and domain_filter in clean:
                    urls.append(clean.split("?")[0].split("#")[0])
        except Exception as e:
            logger.warning(f"Bing搜索失败: {e}")

        # 尝试 Baidu 搜索
        if not urls:
            try:
                baidu_url = f"https://www.baidu.com/s?wd={encoded}&rn=20"
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(baidu_url, headers={
                        "User-Agent": ua,
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    })
                    resp.raise_for_status()
                    html = resp.text

                tree = HTMLParser(html)
                for a in tree.css("a[href]"):
                    href = a.attributes.get("href") or ""
                    if href and domain_filter in href and href.startswith("http"):
                        urls.append(href.split("?")[0].split("#")[0])
            except Exception as e:
                logger.warning(f"Baidu搜索失败: {e}")

        # 去重
        seen = set()
        unique = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique[:15]

    async def _search_dept_urls(self, university: str, major: str = "") -> list[dict[str, str]]:
        """通过搜索引擎发现学院录取名单/招生目录页面的真实URL。"""
        # 构建搜索词
        queries = []
        if self.crawl_mode == "catalog":
            if major:
                queries.append(f"{university} {major} 招生专业目录 site:edu.cn")
                queries.append(f"{university} {major} 硕士招生目录 site:edu.cn")
            queries.append(f"{university} 研究生 招生专业目录 site:edu.cn")
            queries.append(f"{university} 硕士招生目录 考试科目 site:edu.cn")
        else:
            if major:
                queries.append(f"{university} {major} 研究生 录取名单 site:edu.cn")
                queries.append(f"{university} {major} 复试名单 site:edu.cn")
            queries.append(f"{university} 学院 研究生 录取名单 site:edu.cn")
            queries.append(f"{university} 硕士 复试 拟录取 site:edu.cn")

        # 收集搜索结果中的URL
        raw_urls = []
        for q in queries:
            found = await self._search_urls(q, domain_filter=".edu.cn")
            raw_urls.extend(found)
            if len(raw_urls) >= 10:
                break

        if not raw_urls:
            return []

        # 验证URL可达性，提取标题
        results = []
        seen_domains = set()
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for url in raw_urls[:10]:
                # 去掉同一域名下的重复
                domain = urlparse(url).netloc
                if domain in seen_domains:
                    continue

                try:
                    resp = await client.get(url, headers=_get_headers())
                    if resp.status_code >= 400:
                        continue
                    # 从 <title> 提取名称
                    tree = HTMLParser(resp.text)
                    title_el = tree.css_first("title")
                    title = title_el.text(strip=True) if title_el else url
                    # 只保留和学校相关的
                    if university[:2] not in title and university[:2] not in url:
                        continue
                    seen_domains.add(domain)
                    results.append({"url": url, "name": title[:30], "source": "search"})
                    logger.info(f"搜索引擎发现: {title[:30]} → {url}")
                except Exception:
                    continue

        return results[:5]

    # ── 子站搜索 ──

    async def _crawl_dept_site(
        self,
        dept_url: str,
        dept_name: str,
        university: str,
        year: int,
        visited: set[str],
        results: list,
        errors: list,
        major: str = "",
    ) -> dict:
        """对一个学院官网做1层BFS，尝试提取录取名单。返回 {found, reason}。"""
        if dept_url in visited:
            return {"found": False, "reason": "已访问过"}
        visited.add(dept_url)

        page_data = await self._fetch_page(dept_url)
        if not page_data:
            return {"found": False, "reason": f"无法访问页面: {dept_url}"}
        if page_data.get("blocked"):
            return {"found": False, "reason": f"页面需要登录/验证码: {dept_url}"}

        # PDF 直接提取
        if dept_url.lower().endswith(".pdf") or page_data.get("is_pdf"):
            page_dict = {"url": dept_url, "text": dept_name}
            result = await self._extract_from_pdf(page_dict, university, year, major=major)
            if result.get("found"):
                results.append(result)
                return {"found": True, "reason": f"从PDF提取到 {result.get('count', 0)} 条数据"}
            return {"found": False, "reason": result.get("reason", "PDF中未找到名单数据")}

        # AI 导航决策
        links = self._extract_links(dept_url, page_data["html"])
        nav = await self._ai_navigate(dept_url, page_data["title"], links, major=major)
        action = nav.get("action", "skip")
        nav_reason = nav.get("reason", "")

        if action == "extract":
            page_dict = {"url": dept_url, "text": dept_name}
            result = await self._extract_from_page(page_dict, university, year, major=major, html_content=page_data.get("html"))
            if result.get("found"):
                results.append(result)
                # 分页链接检测
                page_links = self._find_pagination_links(dept_url, page_data.get("html", ""))
                for plink in page_links[:2]:
                    if plink not in visited:
                        visited.add(plink)
                        sub_task = CrawlTask(url=plink, text=f"分页: {dept_name}", depth=2, source=dept_url)
                        try:
                            sub_result = await self._extract_page_or_pdf(sub_task, None, university, year, major=major)
                            if sub_result.get("found"):
                                results.append(sub_result)
                        except Exception:
                            pass
                return {"found": True, "reason": f"提取到 {result.get('count', 0)} 条数据"}
            return {"found": False, "reason": f"AI判定需提取但未找到数据: {result.get('reason', '')}"}

        elif action == "follow":
            sub_links = nav.get("links", [])[:MAX_LINKS_PER_PAGE]
            valid_links = []
            for link in sub_links:
                url = link.get("url", "")
                if not url or url in visited:
                    continue
                visited.add(url)
                valid_links.append(link)

            if not valid_links:
                return {"found": False, "reason": "AI发现了链接但均无效"}

            async def process_sub_link(link):
                link_text = link.get("text", link["url"])
                sub_task = CrawlTask(url=link["url"], text=link_text, depth=2, source=dept_url)
                try:
                    return await self._extract_page_or_pdf(sub_task, None, university, year, major=major)
                except Exception as e:
                    return {"found": False, "reason": str(e)}

            semaphore = asyncio.Semaphore(MAX_CONCURRENT)
            async def sem_sub(link):
                async with semaphore:
                    return await process_sub_link(link)

            sub_results = await asyncio.gather(*[sem_sub(lnk) for lnk in valid_links], return_exceptions=True)

            tried = [lnk.get("text", lnk["url"]) for lnk in valid_links]
            for r in sub_results:
                if isinstance(r, Exception):
                    continue
                if r.get("found"):
                    results.append(r)
                    return {"found": True, "reason": "从子页面提取到数据"}

            return {"found": False, "reason": f"尝试了 {len(tried)} 个子链接均未找到数据: {', '.join(t[:20] for t in tried[:3])}"}

        # action == "skip"
        return {"found": False, "reason": f"AI判定页面不相关: {nav_reason}"}


# ── SSE 事件构造 ──

def _step_event(step: str, status: str, detail: str = "") -> dict:
    return {
        "event": "step",
        "data": {"step": step, "status": status, "detail": detail},
    }


def _result_event(success: bool, university: str, year: int, results: list, errors: list) -> dict:
    return {
        "event": "result",
        "data": {
            "success": success,
            "university": university,
            "year": year,
            "results": results,
            "errors": errors,
        },
    }
