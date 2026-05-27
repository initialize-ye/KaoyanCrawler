"""HTML表格解析器。"""

from __future__ import annotations

from loguru import logger
from selectolax.parser import HTMLParser as SelectolaxParser


class HTMLParser:
    """从HTML页面中提取表格数据。"""

    def extract_table(self, content: bytes, selectors: dict) -> list[dict[str, str]]:
        """提取HTML表格，返回行列表。

        selectors结构:
            table: "table.list"  # 表格CSS选择器
            row: "tr"            # 行选择器
            columns:             # 列映射
                0: "exam_id"
                1: "name"
                2: "major"
        """
        tree = SelectolaxParser(content)

        table_sel = selectors.get("table", "table")
        row_sel = selectors.get("row", "tr")
        columns = selectors.get("columns", {})

        table = tree.css_first(table_sel)
        if not table:
            logger.warning(f"未找到表格: {table_sel}")
            return []

        rows = table.css(row_sel)
        results = []

        for row in rows:
            cells = row.css("td")
            if not cells:
                continue

            record = {}
            for col_idx, field_name in columns.items():
                idx = int(col_idx)
                if idx < len(cells):
                    record[field_name] = cells[idx].text(strip=True)

            if record:
                results.append(record)

        return results

    def extract_links(self, content: bytes, base_url: str = "") -> list[dict[str, str]]:
        """提取页面中的链接，用于发现子页面。"""
        tree = SelectolaxParser(content)
        links = []

        for a in tree.css("a"):
            href = a.attributes.get("href", "")
            text = a.text(strip=True)
            if href and text:
                if not href.startswith("http") and base_url:
                    href = base_url.rstrip("/") + "/" + href.lstrip("/")
                links.append({"url": href, "text": text})

        return links
