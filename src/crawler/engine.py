"""爬虫引擎核心。"""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

import httpx
from fake_useragent import UserAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.crawler.config_loader import UniversityConfig
from src.models.schemas import AdmissionRecord, ExamSubject, ListType
from src.parsers.html_parser import HTMLParser
from src.parsers.pdf_parser import PDFParser


class CrawlerEngine:
    """通用爬虫引擎。"""

    def __init__(self):
        self.ua = UserAgent()
        self.html_parser = HTMLParser()
        self.pdf_parser = PDFParser()

    def _get_headers(self) -> dict[str, str]:
        return {"User-Agent": self.ua.random}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _fetch(self, url: str, client: httpx.AsyncClient) -> bytes:
        """获取页面内容，带重试。"""
        logger.info(f"请求: {url}")
        resp = await client.get(url, headers=self._get_headers(), follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    async def _random_delay(self):
        """随机延迟，避免请求过快。"""
        delay = random.uniform(3, 8)
        await asyncio.sleep(delay)

    async def crawl_university(
        self, config: UniversityConfig, output_dir: Path
    ) -> dict[str, list]:
        """爬取单个学校的所有目标。"""
        results: dict[str, list] = {"admission_records": [], "exam_subjects": []}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for target in config.targets:
                try:
                    content = await self._fetch(target.url, client)

                    if target.type == "admission_list":
                        records = await self._parse_admission_list(
                            content, config, target
                        )
                        results["admission_records"].extend(records)
                    elif target.type == "program_catalog":
                        subjects = await self._parse_program_catalog(
                            content, config, target
                        )
                        results["exam_subjects"].extend(subjects)

                    await self._random_delay()

                except Exception as e:
                    logger.error(f"爬取失败 {config.name} - {target.name}: {e}")

        return results

    async def _parse_admission_list(
        self, content: bytes, config: UniversityConfig, target
    ) -> list[AdmissionRecord]:
        """解析复试/录取名单。"""
        if target.format == "pdf":
            rows = self.pdf_parser.extract_table(content)
        else:
            rows = self.html_parser.extract_table(content, target.selectors)

        records = []
        for row in rows:
            try:
                record = AdmissionRecord(
                    university=config.name,
                    year=target.parse_rules.get("year", 2025),
                    list_type=ListType(target.parse_rules.get("list_type", "录取名单")),
                    exam_id=row.get("exam_id", ""),
                    name=row.get("name", ""),
                    major=row.get("major", ""),
                    initial_score=self._to_float(row.get("initial_score")),
                    retest_score=self._to_float(row.get("retest_score")),
                    total_score=self._to_float(row.get("total_score")),
                    admission_status=row.get("admission_status"),
                    admission_type=row.get("admission_type"),
                    study_mode=row.get("study_mode"),
                    source_url=target.url,
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"解析行失败: {row} - {e}")

        return records

    async def _parse_program_catalog(
        self, content: bytes, config: UniversityConfig, target
    ) -> list[ExamSubject]:
        """解析招生专业目录。"""
        if target.format == "pdf":
            rows = self.pdf_parser.extract_table(content)
        else:
            rows = self.html_parser.extract_table(content, target.selectors)

        subjects = []
        for row in rows:
            try:
                subject = ExamSubject(
                    university=config.name,
                    year=target.parse_rules.get("year", 2025),
                    major_code=row.get("major_code", ""),
                    major_name=row.get("major_name", ""),
                    subject1=row.get("subject1"),
                    subject2=row.get("subject2"),
                    subject3=row.get("subject3"),
                    subject4=row.get("subject4"),
                    source_url=target.url,
                )
                subjects.append(subject)
            except Exception as e:
                logger.warning(f"解析行失败: {row} - {e}")

        return subjects

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
