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

        支持检测：
        1. HTML table标签
        2. div模拟的表格布局（class含table、grid等）
        3. 有序列表结构

        返回格式:
        [
            {
                "index": 0,
                "type": "table" | "div-table" | "list",
                "headers": ["姓名", "考号", "专业"],
                "row_count": 25,
                "sample_rows": [第一行数据, 第二行数据],
                "selector": "table:nth-of-type(1)",
            }
        ]
        """
        tree = SelectolaxParser(content)
        results = []

        # 1. 检测标准HTML table
        tables = tree.css("table")
        for i, table in enumerate(tables):
            rows = table.css("tr")
            if not rows:
                continue

            headers = []
            first_row_cells = rows[0].css("th") or rows[0].css("td")
            for cell in first_row_cells:
                headers.append(cell.text(strip=True))

            data_rows = []
            for row in rows[1:]:
                cells = row.css("td")
                if cells:
                    row_data = [cell.text(strip=True) for cell in cells]
                    if any(row_data):
                        data_rows.append(row_data)

            if not data_rows:
                continue

            if table.attributes.get("id"):
                selector = f"#{table.attributes['id']}"
            elif table.attributes.get("class"):
                cls = table.attributes["class"].split()[0]
                selector = f"table.{cls}"
            else:
                selector = f"table:nth-of-type({i + 1})"

            results.append({
                "index": len(results),
                "type": "table",
                "headers": headers,
                "row_count": len(data_rows),
                "sample_rows": data_rows[:3],
                "selector": selector,
            })

        # 2. 检测div模拟的表格（常见于中国高校网站）
        div_table_selectors = [
            "div[class*='table']",
            "div[class*='list']",
            "div[class*='grid']",
            "div[class*='content'] table",
            "div.vxe-table",
            ".el-table",
        ]
        for sel in div_table_selectors:
            div_tables = tree.css(sel)
            for div_table in div_tables:
                rows = div_table.css("div[class*='row'], div[class*='tr'], li")
                if len(rows) < 2:
                    continue

                # 尝试从第一行提取表头
                headers = []
                first_row = rows[0]
                header_cells = first_row.css("div[class*='col'], div[class*='td'], span, th")
                if header_cells:
                    headers = [cell.text(strip=True) for cell in header_cells if cell.text(strip=True)]

                # 提取数据行
                data_rows = []
                for row in rows[1:]:
                    cells = row.css("div[class*='col'], div[class*='td'], span, td")
                    if cells:
                        row_data = [cell.text(strip=True) for cell in cells]
                        if any(row_data):
                            data_rows.append(row_data)

                if data_rows and len(data_rows[0]) >= 2:
                    cls = div_table.attributes.get("class", "").split()[0] if div_table.attributes.get("class") else ""
                    selector = f".{cls}" if cls else sel

                    results.append({
                        "index": len(results),
                        "type": "div-table",
                        "headers": headers if headers else [f"列{i+1}" for i in range(len(data_rows[0]))],
                        "row_count": len(data_rows),
                        "sample_rows": data_rows[:3],
                        "selector": selector,
                    })

        # 3. 检测纯文本中的结构化数据（如空格/制表符分隔的内容）
        body = tree.css_first("body")
        if body:
            text = body.text(strip=False)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            # 检测是否有大量相似结构的行（可能是名单）
            if len(lines) > 10:
                # 检测是否有分隔符模式
                for sep in ['\t', '  ', ' | ']:
                    sep_lines = [line for line in lines if sep in line]
                    if len(sep_lines) > 5:
                        sample_rows = [line.split(sep) for line in sep_lines[:5]]
                        results.append({
                            "index": len(results),
                            "type": "text-table",
                            "headers": [f"列{i+1}" for i in range(len(sample_rows[0]))],
                            "row_count": len(sep_lines),
                            "sample_rows": sample_rows,
                            "selector": "body",
                        })
                        break

        return results

    def preview_page_content(self, content: bytes) -> dict:
        """预览页面内容，返回页面摘要信息。

        用于表格检测失败时，让用户手动识别内容结构。
        """
        tree = SelectolaxParser(content)

        # 提取页面标题
        title_el = tree.css_first("title, h1, h2")
        title = title_el.text(strip=True) if title_el else ""

        # 提取正文区域
        content_selectors = [
            "div[class*='content']",
            "div[class*='article']",
            "div[class*='main']",
            "article",
            "main",
            ".wp_articlecontent",
        ]

        main_content = ""
        for sel in content_selectors:
            el = tree.css_first(sel)
            if el:
                main_content = el.text(strip=False)[:3000]
                break

        if not main_content:
            body = tree.css_first("body")
            main_content = body.text(strip=False)[:3000] if body else ""

        # 提取所有文本行
        lines = [line.strip() for line in main_content.split('\n') if line.strip()]

        # 检测可能的链接（PDF下载等）
        pdf_links = []
        for a in tree.css("a[href$='.pdf'], a[href*='.pdf']"):
            href = a.attributes.get("href", "")
            text = a.text(strip=True)
            if href and text:
                pdf_links.append({"url": href, "text": text})

        return {
            "title": title,
            "line_count": len(lines),
            "sample_lines": lines[:30],
            "pdf_links": pdf_links,
            "has_table_tag": bool(tree.css("table")),
            "has_div_table": bool(tree.css("div[class*='table'], div[class*='list']")),
        }

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
