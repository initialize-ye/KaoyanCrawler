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

    def preview_tables(self, content: bytes) -> list[dict]:
        """预览页面中所有表格，返回表格摘要。

        返回格式:
        [
            {
                "index": 0,
                "headers": ["姓名", "考号", "专业"],
                "row_count": 25,
                "sample_rows": [第一行数据, 第二行数据],
                "selector": "table:nth-of-type(1)",
            }
        ]
        """
        tree = SelectolaxParser(content)
        tables = tree.css("table")
        results = []

        for i, table in enumerate(tables):
            rows = table.css("tr")
            if not rows:
                continue

            # 提取表头（第一行）
            headers = []
            first_row_cells = rows[0].css("th") or rows[0].css("td")
            for cell in first_row_cells:
                headers.append(cell.text(strip=True))

            # 提取数据行
            data_rows = []
            for row in rows[1:]:
                cells = row.css("td")
                if cells:
                    row_data = [cell.text(strip=True) for cell in cells]
                    if any(row_data):  # 跳过空行
                        data_rows.append(row_data)

            if not data_rows:
                continue

            # 生成CSS选择器
            if table.attributes.get("id"):
                selector = f"#{table.attributes['id']}"
            elif table.attributes.get("class"):
                cls = table.attributes["class"].split()[0]
                selector = f"table.{cls}"
            else:
                selector = f"table:nth-of-type({i + 1})"

            results.append({
                "index": i,
                "headers": headers,
                "row_count": len(data_rows),
                "sample_rows": data_rows[:3],  # 最多显示3行示例
                "selector": selector,
            })

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
