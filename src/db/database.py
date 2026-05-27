"""SQLite数据库操作。"""

from __future__ import annotations

import aiosqlite
from loguru import logger
from pathlib import Path

from src.models.schemas import AdmissionRecord, ExamSubject

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS admission_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university TEXT NOT NULL,
    year INTEGER NOT NULL,
    list_type TEXT NOT NULL,
    exam_id TEXT NOT NULL,
    name TEXT NOT NULL,
    major TEXT NOT NULL,
    initial_score REAL,
    retest_score REAL,
    total_score REAL,
    admission_status TEXT,
    admission_type TEXT,
    study_mode TEXT,
    source_url TEXT,
    crawl_time TEXT NOT NULL,
    UNIQUE(university, year, list_type, exam_id)
);

CREATE TABLE IF NOT EXISTS exam_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university TEXT NOT NULL,
    year INTEGER NOT NULL,
    major_code TEXT NOT NULL,
    major_name TEXT NOT NULL,
    subject1 TEXT,
    subject2 TEXT,
    subject3 TEXT,
    subject4 TEXT,
    source_url TEXT,
    crawl_time TEXT NOT NULL,
    UNIQUE(university, year, major_code)
);

CREATE INDEX IF NOT EXISTS idx_admission_university ON admission_records(university);
CREATE INDEX IF NOT EXISTS idx_admission_year ON admission_records(year);
CREATE INDEX IF NOT EXISTS idx_admission_major ON admission_records(major);
CREATE INDEX IF NOT EXISTS idx_subjects_university ON exam_subjects(university);
CREATE INDEX IF NOT EXISTS idx_subjects_year ON exam_subjects(year);
"""


class Database:
    """SQLite数据库管理。"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    async def init(self):
        """初始化数据库，创建表结构。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(DB_SCHEMA)
            await db.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    async def insert_admission_records(self, records: list[AdmissionRecord]):
        """批量插入录取记录，冲突时忽略。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT OR IGNORE INTO admission_records
                (university, year, list_type, exam_id, name, major,
                 initial_score, retest_score, total_score,
                 admission_status, admission_type, study_mode,
                 source_url, crawl_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        r.university, r.year, r.list_type.value,
                        r.exam_id, r.name, r.major,
                        r.initial_score, r.retest_score, r.total_score,
                        r.admission_status, r.admission_type, r.study_mode,
                        r.source_url, r.crawl_time.isoformat(),
                    )
                    for r in records
                ],
            )
            await db.commit()
        logger.info(f"插入 {len(records)} 条录取记录")

    async def insert_exam_subjects(self, subjects: list[ExamSubject]):
        """批量插入考试科目，冲突时忽略。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT OR IGNORE INTO exam_subjects
                (university, year, major_code, major_name,
                 subject1, subject2, subject3, subject4,
                 source_url, crawl_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        s.university, s.year, s.major_code, s.major_name,
                        s.subject1, s.subject2, s.subject3, s.subject4,
                        s.source_url, s.crawl_time.isoformat(),
                    )
                    for s in subjects
                ],
            )
            await db.commit()
        logger.info(f"插入 {len(subjects)} 条科目记录")

    async def query_admissions(
        self,
        university: str | None = None,
        year: int | None = None,
        major: str | None = None,
        list_type: str | None = None,
    ) -> list[dict]:
        """查询录取记录。"""
        conditions = []
        params = []

        if university:
            conditions.append("university = ?")
            params.append(university)
        if year:
            conditions.append("year = ?")
            params.append(year)
        if major:
            conditions.append("major LIKE ?")
            params.append(f"%{major}%")
        if list_type:
            conditions.append("list_type = ?")
            params.append(list_type)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM admission_records WHERE {where} ORDER BY university, major"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def query_subjects(
        self,
        university: str | None = None,
        year: int | None = None,
        major_name: str | None = None,
    ) -> list[dict]:
        """查询考试科目。"""
        conditions = []
        params = []

        if university:
            conditions.append("university = ?")
            params.append(university)
        if year:
            conditions.append("year = ?")
            params.append(year)
        if major_name:
            conditions.append("major_name LIKE ?")
            params.append(f"%{major_name}%")

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM exam_subjects WHERE {where} ORDER BY university, major_code"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_stats(self) -> dict:
        """获取数据库统计信息。"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM admission_records") as cur:
                admission_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM exam_subjects") as cur:
                subject_count = (await cur.fetchone())[0]
            async with db.execute(
                "SELECT COUNT(DISTINCT university) FROM admission_records"
            ) as cur:
                uni_count = (await cur.fetchone())[0]

            return {
                "admission_records": admission_count,
                "exam_subjects": subject_count,
                "universities": uni_count,
            }
