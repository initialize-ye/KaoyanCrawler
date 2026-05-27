"""FastAPI Web应用。"""

from __future__ import annotations

from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.crawler.discovery import discover_links
from src.db.database import Database
from src.parsers.html_parser import HTMLParser

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "kaoyan.db"
CONFIGS_DIR = BASE_DIR / "configs"

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

html_parser = HTMLParser()


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


# ========== 配置向导 API ==========

@app.get("/api/discover")
async def discover(url: str = Query(..., description="研究生院首页URL")):
    """自动发现页面中的相关链接。"""
    results = await discover_links(url)
    return results


@app.get("/api/preview-tables")
async def preview_tables(url: str = Query(..., description="页面URL")):
    """预览页面中的所有表格。"""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            content = resp.content

        tables = html_parser.preview_tables(content)
        return {"url": url, "tables": tables}
    except Exception as e:
        return {"url": url, "tables": [], "error": str(e)}


class ConfigGenerateRequest(BaseModel):
    university_name: str
    university_code: str
    graduate_school_url: str
    targets: list[dict]


@app.post("/api/generate-config")
async def generate_config(req: ConfigGenerateRequest):
    """生成并保存学校配置文件。"""
    config = {
        "name": req.university_name,
        "code": req.university_code,
        "graduate_school_url": req.graduate_school_url,
        "tags": ["985"],
        "targets": req.targets,
    }

    config_file = CONFIGS_DIR / f"{req.university_code}.yaml"

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return {"status": "ok", "file": str(config_file.name)}


@app.get("/api/configs")
async def list_configs():
    """列出所有已有的配置文件。"""
    configs = []
    for f in sorted(CONFIGS_DIR.glob("*.yaml")):
        if f.name == "template.yaml":
            continue
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            configs.append({
                "code": data.get("code", f.stem),
                "name": data.get("name", f.stem),
                "target_count": len(data.get("targets", [])),
            })
    return {"configs": configs}
