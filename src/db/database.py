"""SQLite数据库操作。"""

from __future__ import annotations

import aiosqlite
from loguru import logger
from pathlib import Path

from src.models.schemas import AdmissionRecord, ExamSubject, RetestRule, ScoreLine

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
    department TEXT NOT NULL DEFAULT '',
    research_direction TEXT NOT NULL DEFAULT '',
    enrollment INTEGER,
    subject1 TEXT,
    subject2 TEXT,
    subject3 TEXT,
    subject4 TEXT,
    source_url TEXT,
    crawl_time TEXT NOT NULL,
    UNIQUE(university, year, major_code, department, research_direction)
);

CREATE TABLE IF NOT EXISTS retest_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university TEXT NOT NULL,
    year INTEGER NOT NULL,
    title TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT '',
    major TEXT NOT NULL DEFAULT '',
    content_summary TEXT NOT NULL DEFAULT '',
    retest_format TEXT NOT NULL DEFAULT '',
    score_composition TEXT NOT NULL DEFAULT '',
    retest_content TEXT NOT NULL DEFAULT '',
    other_requirements TEXT NOT NULL DEFAULT '',
    source_url TEXT,
    crawl_time TEXT NOT NULL,
    UNIQUE(university, year, title, department)
);

CREATE TABLE IF NOT EXISTS score_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university TEXT NOT NULL,
    year INTEGER NOT NULL,
    category TEXT NOT NULL,
    discipline TEXT NOT NULL,
    discipline_code TEXT NOT NULL DEFAULT '',
    total_score REAL,
    score1 REAL,
    score2 REAL,
    source_url TEXT,
    crawl_time TEXT NOT NULL,
    UNIQUE(university, year, category, discipline)
);

CREATE INDEX IF NOT EXISTS idx_admission_university ON admission_records(university);
CREATE INDEX IF NOT EXISTS idx_admission_year ON admission_records(year);
CREATE INDEX IF NOT EXISTS idx_admission_major ON admission_records(major);
CREATE INDEX IF NOT EXISTS idx_admission_uni_year ON admission_records(university, year);
CREATE INDEX IF NOT EXISTS idx_subjects_university ON exam_subjects(university);
CREATE INDEX IF NOT EXISTS idx_subjects_year ON exam_subjects(year);
CREATE INDEX IF NOT EXISTS idx_subjects_uni_year ON exam_subjects(university, year);
CREATE INDEX IF NOT EXISTS idx_rules_university ON retest_rules(university);
CREATE INDEX IF NOT EXISTS idx_rules_year ON retest_rules(year);
CREATE INDEX IF NOT EXISTS idx_rules_uni_year ON retest_rules(university, year);
CREATE INDEX IF NOT EXISTS idx_scorelines_university ON score_lines(university);
CREATE INDEX IF NOT EXISTS idx_scorelines_year ON score_lines(year);
CREATE INDEX IF NOT EXISTS idx_scorelines_uni_year ON score_lines(university, year);
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
            # 迁移：为旧表添加新列
            for column, col_def in [
                ("department", "TEXT NOT NULL DEFAULT ''"),
                ("research_direction", "TEXT NOT NULL DEFAULT ''"),
                ("enrollment", "INTEGER"),
            ]:
                try:
                    await db.execute(f"ALTER TABLE exam_subjects ADD COLUMN {column} {col_def}")
                except Exception:
                    pass  # 列已存在
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
        """批量插入考试科目，冲突时更新。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT INTO exam_subjects
                (university, year, major_code, major_name,
                 department, research_direction, enrollment,
                 subject1, subject2, subject3, subject4,
                 source_url, crawl_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(university, year, major_code, department, research_direction)
                DO UPDATE SET
                    major_name = excluded.major_name,
                    enrollment = COALESCE(excluded.enrollment, enrollment),
                    subject1 = COALESCE(excluded.subject1, subject1),
                    subject2 = COALESCE(excluded.subject2, subject2),
                    subject3 = COALESCE(excluded.subject3, subject3),
                    subject4 = COALESCE(excluded.subject4, subject4),
                    source_url = excluded.source_url,
                    crawl_time = excluded.crawl_time""",
                [
                    (
                        s.university, s.year, s.major_code, s.major_name,
                        s.department, s.research_direction, s.enrollment,
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
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """查询录取记录（支持分页）。"""
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM admission_records WHERE {where}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"SELECT * FROM admission_records WHERE {where} ORDER BY university, major LIMIT ? OFFSET ?"
            async with db.execute(sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows], total

    async def query_subjects(
        self,
        university: str | None = None,
        year: int | None = None,
        major_name: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """查询考试科目（支持分页）。"""
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
        if department:
            conditions.append("department LIKE ?")
            params.append(f"%{department}%")

        where = " AND ".join(conditions) if conditions else "1=1"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM exam_subjects WHERE {where}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"SELECT * FROM exam_subjects WHERE {where} ORDER BY university, department, major_code LIMIT ? OFFSET ?"
            async with db.execute(sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows], total

    async def get_stats(self) -> dict:
        """获取数据库统计信息。"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM admission_records") as cur:
                admission_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM exam_subjects") as cur:
                subject_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM retest_rules") as cur:
                rules_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM score_lines") as cur:
                scorelines_count = (await cur.fetchone())[0]
            async with db.execute(
                "SELECT COUNT(DISTINCT university) FROM admission_records"
            ) as cur:
                uni_count = (await cur.fetchone())[0]

            return {
                "admission_records": admission_count,
                "exam_subjects": subject_count,
                "retest_rules": rules_count,
                "score_lines": scorelines_count,
                "universities": uni_count,
            }

    async def insert_retest_rules(self, rules: list[RetestRule]):
        """批量插入复试细则，冲突时忽略。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT OR IGNORE INTO retest_rules
                (university, year, title, department, major,
                 content_summary, retest_format, score_composition,
                 retest_content, other_requirements,
                 source_url, crawl_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        r.university, r.year, r.title, r.department, r.major,
                        r.content_summary, r.retest_format, r.score_composition,
                        r.retest_content, r.other_requirements,
                        r.source_url, r.crawl_time.isoformat(),
                    )
                    for r in rules
                ],
            )
            await db.commit()
        logger.info(f"插入 {len(rules)} 条复试细则")

    async def query_retest_rules(
        self,
        university: str | None = None,
        year: int | None = None,
        department: str | None = None,
        major: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """查询复试细则（支持分页）。"""
        conditions = []
        params = []

        if university:
            conditions.append("university = ?")
            params.append(university)
        if year:
            conditions.append("year = ?")
            params.append(year)
        if department:
            conditions.append("department LIKE ?")
            params.append(f"%{department}%")
        if major:
            conditions.append("major LIKE ?")
            params.append(f"%{major}%")

        where = " AND ".join(conditions) if conditions else "1=1"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM retest_rules WHERE {where}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"SELECT * FROM retest_rules WHERE {where} ORDER BY university, department LIMIT ? OFFSET ?"
            async with db.execute(sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows], total

    async def insert_score_lines(self, lines: list[ScoreLine]):
        """批量插入分数线，冲突时忽略。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT OR IGNORE INTO score_lines
                (university, year, category, discipline, discipline_code,
                 total_score, score1, score2,
                 source_url, crawl_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        sl.university, sl.year, sl.category, sl.discipline, sl.discipline_code,
                        sl.total_score, sl.score1, sl.score2,
                        sl.source_url, sl.crawl_time.isoformat(),
                    )
                    for sl in lines
                ],
            )
            await db.commit()
        logger.info(f"插入 {len(lines)} 条分数线")

    async def query_score_lines(
        self,
        university: str | None = None,
        year: int | None = None,
        category: str | None = None,
        discipline: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """查询分数线（支持分页）。"""
        conditions = []
        params = []

        if university:
            conditions.append("university = ?")
            params.append(university)
        if year:
            conditions.append("year = ?")
            params.append(year)
        if category:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")
        if discipline:
            conditions.append("discipline LIKE ?")
            params.append(f"%{discipline}%")

        where = " AND ".join(conditions) if conditions else "1=1"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM score_lines WHERE {where}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"SELECT * FROM score_lines WHERE {where} ORDER BY university, category, discipline LIMIT ? OFFSET ?"
            async with db.execute(sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows], total
