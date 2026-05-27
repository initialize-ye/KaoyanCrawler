"""FastAPI Web应用。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import Database

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "kaoyan.db"

app = FastAPI(
    title="KaoyanCrawler API",
    description="考研数据采集系统 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Database:
    return Database(DB_PATH)


@app.get("/api/stats")
async def get_stats():
    """获取数据库统计信息。"""
    db = get_db()
    return await db.get_stats()


@app.get("/api/admissions")
async def get_admissions(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    major: str = Query(None, description="专业关键词"),
    list_type: str = Query(None, description="名单类型: 复试名单/录取名单"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
):
    """查询录取记录。"""
    db = get_db()
    records = await db.query_admissions(
        university=university, year=year, major=major, list_type=list_type
    )

    total = len(records)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": records[start:end],
    }


@app.get("/api/subjects")
async def get_subjects(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    major_name: str = Query(None, description="专业名称关键词"),
):
    """查询考试科目。"""
    db = get_db()
    return await db.query_subjects(
        university=university, year=year, major_name=major_name
    )


@app.get("/api/universities")
async def get_universities():
    """获取已采集的学校列表。"""
    db = get_db()
    records = await db.query_admissions()
    universities = sorted(set(r["university"] for r in records))
    return {"universities": universities}
