"""PDF表格解析器。"""

from __future__ import annotations

import io

import pdfplumber
from loguru import logger


class PDFParser:
    """从PDF文件中提取表格数据。"""

    def extract_table(self, content: bytes) -> list[dict[str, str]]:
        """提取PDF中的表格，返回行列表。

        自动检测表头行，将其余行映射为字典。
        """
        results = []

        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        parsed = self._parse_table(table)
                        results.extend(parsed)
        except Exception as e:
            logger.error(f"PDF解析失败: {e}")

        return results

    def _parse_table(self, table: list[list]) -> list[dict[str, str]]:
        """将原始表格数据转换为字典列表。

        第一行作为表头，其余行为数据。
        """
        if not table or len(table) < 2:
            return []

        headers = table[0]
        if not headers:
            return []

        # 清理表头
        headers = [self._clean_cell(h) for h in headers]

        results = []
        for row in table[1:]:
            if not row or all(cell is None or cell == "" for cell in row):
                continue

            record = {}
            for i, cell in enumerate(row):
                if i < len(headers) and headers[i]:
                    record[headers[i]] = self._clean_cell(cell)

            if record:
                results.append(record)

        return results

    @staticmethod
    def _clean_cell(cell) -> str:
        """清理单元格内容。"""
        if cell is None:
            return ""
        return str(cell).strip().replace("\n", " ")
