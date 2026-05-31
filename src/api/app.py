"""FastAPI Web应用。"""

from __future__ import annotations

from pathlib import Path

import json
import re

import aiosqlite
import httpx
import yaml
from fastapi import FastAPI, Query, UploadFile, File
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config.settings import (
    AI_PROVIDERS,
    get_ai_config,
    load_settings,
    save_settings,
)
from src.crawler.ai_extractor import AIExtractor
from src.crawler.discovery import discover_links
from src.db.database import Database
from src.models.schemas import AdmissionRecord, ExamSubject, ListType, RetestRule, ScoreLine
from src.parsers.html_parser import HTMLParser

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "kaoyan.db"
CONFIGS_DIR = BASE_DIR / "configs"

app = FastAPI(
    title="KaoyanCrawler API",
    description="考研数据采集系统 API",
    version="0.2.0",
)

# 添加GZip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

html_parser = HTMLParser()


@app.get("/api/health")
async def health_check():
    """健康检查端点。"""
    db = get_db()
    try:
        stats = await db.get_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "records": sum(stats.values()),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库。"""
    db = get_db()
    await db.init()


def get_ai_extractor() -> AIExtractor | None:
    """根据用户配置获取AI提取器。"""
    config = get_ai_config()
    if not config:
        return None
    return AIExtractor(
        api_key=config["api_key"],
        provider=config.get("provider", "deepseek"),
        base_url=config.get("base_url", ""),
        model=config.get("model", ""),
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
    records, total = await db.query_admissions(
        university=university, year=year, major=major, list_type=list_type,
        page=page, page_size=page_size,
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": records,
    }


@app.delete("/api/admissions/{record_id}")
async def delete_admission(record_id: int):
    """删除录取记录。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM admission_records WHERE id = ?", (record_id,))
        await conn.commit()
    return {"status": "ok", "message": "已删除"}


@app.get("/api/subjects")
async def get_subjects(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    major_name: str = Query(None, description="专业名称关键词"),
    department: str = Query(None, description="学院名称关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
):
    """查询考试科目。"""
    db = get_db()
    records, total = await db.query_subjects(
        university=university, year=year, major_name=major_name, department=department,
        page=page, page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": records,
    }


@app.get("/api/retest-rules")
async def get_retest_rules(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    department: str = Query(None, description="学院名称关键词"),
    major: str = Query(None, description="专业名称关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
):
    """查询复试细则。"""
    db = get_db()
    records, total = await db.query_retest_rules(
        university=university, year=year, department=department, major=major,
        page=page, page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": records,
    }


@app.get("/api/score-lines")
async def get_score_lines(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    category: str = Query(None, description="学位类别"),
    discipline: str = Query(None, description="学科门类关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
):
    """查询分数线。"""
    db = get_db()
    records, total = await db.query_score_lines(
        university=university, year=year, category=category, discipline=discipline,
        page=page, page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": records,
    }


@app.delete("/api/score-lines/{line_id}")
async def delete_score_line(line_id: int):
    """删除分数线记录。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM score_lines WHERE id = ?", (line_id,))
        await conn.commit()
    return {"status": "ok", "message": "已删除"}


@app.delete("/api/retest-rules/{rule_id}")
async def delete_retest_rule(rule_id: int):
    """删除复试细则记录。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM retest_rules WHERE id = ?", (rule_id,))
        await conn.commit()
    return {"status": "ok", "message": "已删除"}


# ========== 数据导出 API ==========

@app.get("/api/export/admissions")
async def export_admissions(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    format: str = Query("json", description="导出格式: json/csv"),
):
    """导出录取数据。"""
    db = get_db()
    records, _ = await db.query_admissions(
        university=university, year=year, page=1, page_size=100000,
    )

    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=admissions.csv"},
        )
    return {"data": records, "total": len(records)}


@app.get("/api/export/subjects")
async def export_subjects(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    format: str = Query("json", description="导出格式: json/csv"),
):
    """导出招生目录数据。"""
    db = get_db()
    records, _ = await db.query_subjects(
        university=university, year=year, page=1, page_size=100000,
    )

    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=subjects.csv"},
        )
    return {"data": records, "total": len(records)}


@app.get("/api/export/score-lines")
async def export_score_lines(
    university: str = Query(None, description="学校名称"),
    year: int = Query(None, description="年份"),
    format: str = Query("json", description="导出格式: json/csv"),
):
    """导出分数线数据。"""
    db = get_db()
    records, _ = await db.query_score_lines(
        university=university, year=year, page=1, page_size=100000,
    )

    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=score_lines.csv"},
        )
    return {"data": records, "total": len(records)}


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@app.post("/api/subjects/batch-delete")
async def batch_delete_subjects(req: BatchDeleteRequest):
    """批量删除招生目录记录。"""
    if not req.ids:
        return {"status": "error", "message": "没有要删除的记录"}
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        placeholders = ",".join("?" * len(req.ids))
        await conn.execute(f"DELETE FROM exam_subjects WHERE id IN ({placeholders})", req.ids)
        await conn.commit()
    return {"status": "ok", "message": f"已删除 {len(req.ids)} 条记录"}


@app.post("/api/admissions/batch-delete")
async def batch_delete_admissions(req: BatchDeleteRequest):
    """批量删除录取记录。"""
    if not req.ids:
        return {"status": "error", "message": "没有要删除的记录"}
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        placeholders = ",".join("?" * len(req.ids))
        await conn.execute(f"DELETE FROM admission_records WHERE id IN ({placeholders})", req.ids)
        await conn.commit()
    return {"status": "ok", "message": f"已删除 {len(req.ids)} 条记录"}


class DeleteBySchoolRequest(BaseModel):
    university: str
    year: int | None = None


@app.post("/api/subjects/delete-by-school")
async def delete_subjects_by_school(req: DeleteBySchoolRequest):
    """按学校+年份删除全部招生目录记录。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        if req.year:
            cursor = await conn.execute(
                "DELETE FROM exam_subjects WHERE university = ? AND year = ?",
                (req.university, req.year),
            )
        else:
            cursor = await conn.execute(
                "DELETE FROM exam_subjects WHERE university = ?",
                (req.university,),
            )
        await conn.commit()
        deleted = cursor.rowcount
    return {"status": "ok", "message": f"已删除 {deleted} 条记录"}


@app.post("/api/admissions/delete-by-school")
async def delete_admissions_by_school(req: DeleteBySchoolRequest):
    """按学校+年份删除全部录取记录。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        if req.year:
            cursor = await conn.execute(
                "DELETE FROM admission_records WHERE university = ? AND year = ?",
                (req.university, req.year),
            )
        else:
            cursor = await conn.execute(
                "DELETE FROM admission_records WHERE university = ?",
                (req.university,),
            )
        await conn.commit()
        deleted = cursor.rowcount
    return {"status": "ok", "message": f"已删除 {deleted} 条记录"}


@app.post("/api/delete-all-by-school")
async def delete_all_by_school(req: DeleteBySchoolRequest):
    """按学校+年份删除全部数据（招生目录、录取名单、分数线、复试规则）。"""
    db = get_db()
    total_deleted = 0
    async with aiosqlite.connect(db.db_path) as conn:
        # 删除招生目录
        if req.year:
            cursor = await conn.execute(
                "DELETE FROM exam_subjects WHERE university = ? AND year = ?",
                (req.university, req.year),
            )
        else:
            cursor = await conn.execute(
                "DELETE FROM exam_subjects WHERE university = ?",
                (req.university,),
            )
        total_deleted += cursor.rowcount

        # 删除录取记录
        if req.year:
            cursor = await conn.execute(
                "DELETE FROM admission_records WHERE university = ? AND year = ?",
                (req.university, req.year),
            )
        else:
            cursor = await conn.execute(
                "DELETE FROM admission_records WHERE university = ?",
                (req.university,),
            )
        total_deleted += cursor.rowcount

        # 删除分数线
        if req.year:
            cursor = await conn.execute(
                "DELETE FROM score_lines WHERE university = ? AND year = ?",
                (req.university, req.year),
            )
        else:
            cursor = await conn.execute(
                "DELETE FROM score_lines WHERE university = ?",
                (req.university,),
            )
        total_deleted += cursor.rowcount

        # 删除复试规则
        if req.year:
            cursor = await conn.execute(
                "DELETE FROM retest_rules WHERE university = ? AND year = ?",
                (req.university, req.year),
            )
        else:
            cursor = await conn.execute(
                "DELETE FROM retest_rules WHERE university = ?",
                (req.university,),
            )
        total_deleted += cursor.rowcount

        await conn.commit()
    return {"status": "ok", "message": f"已删除 {total_deleted} 条记录"}


@app.delete("/api/subjects/{subject_id}")
async def delete_subject(subject_id: int):
    """删除招生目录记录。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM exam_subjects WHERE id = ?", (subject_id,))
        await conn.commit()
    return {"status": "ok", "message": "已删除"}


@app.put("/api/subjects/{subject_id}")
async def update_subject(subject_id: int, data: dict):
    """更新招生目录记录。"""
    db = get_db()
    fields = []
    values = []
    for key in ["university", "year", "major_code", "major_name", "department",
                 "research_direction", "subject1", "subject2", "subject3", "subject4"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        return {"status": "error", "message": "没有要更新的字段"}
    values.append(subject_id)
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute(f"UPDATE exam_subjects SET {', '.join(fields)} WHERE id = ?", values)
        await conn.commit()
    return {"status": "ok", "message": "已更新"}


@app.get("/api/universities")
async def get_universities():
    """获取已采集的学校列表（从所有表中查询）。"""
    db = get_db()
    async with aiosqlite.connect(db.db_path) as conn:
        cursor = await conn.execute("""
            SELECT DISTINCT university FROM (
                SELECT university FROM admission_records
                UNION
                SELECT university FROM exam_subjects
                UNION
                SELECT university FROM retest_rules
                UNION
                SELECT university FROM score_lines
            ) ORDER BY university
        """)
        rows = await cursor.fetchall()
        universities = [r[0] for r in rows]
    return {"universities": universities}


# ========== 学校管理 API ==========

@app.get("/api/schools")
async def get_schools():
    """获取所有学校及数据统计。"""
    db = get_db()
    schools = await db.get_all_schools()
    return {"schools": schools}


@app.get("/api/schools/{university}")
async def get_school_detail(university: str):
    """获取单个学校的详细信息。"""
    db = get_db()
    school = await db.get_school_detail(university)
    if not school:
        return {"error": "学校不存在"}
    return school


class SchoolInfoRequest(BaseModel):
    name: str
    website: str = ""
    duration: str = ""
    tuition: str = ""
    scholarship: str = ""
    notes: str = ""


@app.post("/api/schools")
async def create_or_update_school(req: SchoolInfoRequest):
    """创建或更新学校信息。"""
    db = get_db()
    school = await db.upsert_school(
        name=req.name,
        website=req.website,
        duration=req.duration,
        tuition=req.tuition,
        scholarship=req.scholarship,
        notes=req.notes,
    )
    return {"status": "ok", "school": school}


@app.delete("/api/schools/{university}")
async def delete_school(university: str):
    """删除学校及所有关联数据。"""
    db = get_db()
    deleted = await db.delete_school(university)
    return {"status": "ok", "message": f"已删除 {deleted} 条记录"}


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
        page_info = html_parser.preview_page_content(content)
        return {"url": url, "tables": tables, "page_info": page_info}
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


# ========== AI智能提取 API ==========

# 数据链接关键词映射
_DATA_LINK_KEYWORDS = {
    "program_catalog": ["专业目录", "招生目录", "考试科目", "点击查看", "Zsml_view", "zsml"],
    "admission_list": ["录取名单", "拟录取", "复试名单", "点击查看", "下载"],
    "retest_list": ["复试名单", "复试细则", "复试办法", "点击查看", "下载"],
    "retest_rules": ["复试细则", "复试办法", "复试录取", "点击查看", "下载"],
}

# 文件扩展名模式
_FILE_URL_PATTERN = re.compile(r'https?://[^\s"\'<>]+\.(pdf|xlsx?|docx?)', re.IGNORECASE)


def _detect_data_link(html: str, extract_type: str, current_url: str = "") -> str | None:
    """用关键词检测页面中可能的数据链接。"""
    from selectolax.parser import HTMLParser
    from urllib.parse import urljoin

    tree = HTMLParser(html)
    keywords = _DATA_LINK_KEYWORDS.get(extract_type, [])
    candidates = []

    for a in tree.css("a[href]"):
        href = a.attributes.get("href") or ""
        text = a.text(strip=True) or ""
        if not href:
            continue

        # 转为绝对路径
        full_url = urljoin(current_url, href) if current_url and not href.startswith("http") else href

        # 排除当前页面URL
        if current_url and full_url.rstrip('/') == current_url.rstrip('/'):
            continue

        # 检查是否是文件链接
        if _FILE_URL_PATTERN.search(full_url):
            score = 10
        else:
            # 根据关键词匹配计算分数
            score = 0
            combined = full_url + " " + text
            for kw in keywords:
                if kw.lower() in combined.lower():
                    score += 5
            # 额外加分：链接文字包含"点击查看"或"下载"
            if "点击查看" in text or "点击进入" in text:
                score += 8
            # 额外加分：链接包含具体数据路径特征
            if any(p in full_url.lower() for p in ["zsml", "catalog", "list", "view"]):
                score += 3

        if score > 0:
            # 排除导航链接、页脚链接等
            if any(skip in full_url.lower() for skip in ["javascript:", "mailto:", "#", "login", "signin"]):
                continue
            candidates.append((score, full_url, text))

    if not candidates:
        return None

    # 按分数排序，返回最高分的链接
    candidates.sort(key=lambda x: -x[0])
    best = candidates[0][1]

    return best


def _parse_table_data(rows: list, university: str, source_url: str) -> dict | None:
    """从PDF表格数据解析，精度更高。"""
    if not rows or len(rows) < 2:
        return None

    # 清理行数据
    cleaned_rows = []
    for row in rows:
        if not row:
            continue
        cleaned = [str(cell).strip() if cell else "" for cell in row]
        if any(cleaned):
            cleaned_rows.append(cleaned)

    if len(cleaned_rows) < 2:
        return None

    # 检测数据类型
    header = " ".join(cleaned_rows[0])

    # 分数线格式：类别 学科门类 总分 单科1 单科2
    if "总分" in header and ("单科" in header or "分=100" in header or "满分=100" in header):
        return _parse_score_table(cleaned_rows, university, source_url)

    # 招生目录格式：专业代码 专业名称 考试科目
    if "学科代码" in header or "专业代码" in header or "考试科目" in header:
        return _parse_catalog_table(cleaned_rows, university, source_url)

    # 名单格式：序号 考生编号 姓名
    if "考生编号" in header or "准考证" in header or "姓名" in header:
        return _parse_admission_table(cleaned_rows, university, source_url)

    return None


def _parse_score_table(rows: list, university: str, source_url: str) -> dict:
    """从表格解析分数线。"""
    from datetime import datetime

    year = datetime.now().year
    year_match = re.search(r'20(\d{2})', " ".join(rows[0]))
    if year_match:
        year = 2000 + int(year_match.group(1))

    score_lines = []
    category = "学术学位"

    for row in rows[1:]:  # 跳过表头
        if len(row) < 3:
            continue

        # 尝试匹配：学科名称[代码] 总分 单科1 单科2
        name = row[0] if row[0] else ""
        code = ""
        total = None
        s1 = None
        s2 = None

        # 从名称中提取代码
        code_match = re.search(r'\[(\d+[A-Z]?\d*)\]', name)
        if code_match:
            code = code_match.group(1)
            name = re.sub(r'\[\d+[A-Z]?\d*\]', '', name).strip()
        elif len(row) > 1 and re.match(r'^\d+[A-Z]?\d*$', row[1]):
            code = row[1]

        # 提取分数
        for i, cell in enumerate(row):
            if i == 0:
                continue
            if re.match(r'^\d{3}$', cell):
                if total is None:
                    total = int(cell)
                elif s1 is None:
                    s1 = int(cell)
                elif s2 is None:
                    s2 = int(cell)

        # 判断类别
        if "单独考试" in name:
            category = "单独考试"
        elif "专业" in " ".join(rows[0][:2]):
            category = "专业学位"

        if name and total:
            score_lines.append({
                "category": category,
                "discipline": name,
                "discipline_code": code,
                "total_score": total,
                "score1": s1,
                "score2": s2,
            })

    if not score_lines:
        return None

    return {
        "found": True,
        "list_type": "复试分数线",
        "year": year,
        "university": university,
        "score_lines": score_lines,
    }


def _parse_catalog_table(rows: list, university: str, source_url: str) -> dict:
    """从表格解析招生目录。"""
    from datetime import datetime

    year = datetime.now().year
    year_match = re.search(r'20(\d{2})', " ".join(rows[0]))
    if year_match:
        year = 2000 + int(year_match.group(1))

    subjects = []
    current_dept = ""
    last_major = None  # 上一个专业代码，用于继承科目
    last_major_name = ""  # 上一个专业名称
    last_subj = [None, None, None, None]
    major_records = {}  # 记录每个专业的第一个条目，用于跨页更新

    for row in rows[1:]:
        if not row or not row[0]:
            continue

        first_cell = str(row[0]).strip()

        # 检测学院（3位数字开头 + 学院名称）
        dept_match = re.match(r'^(\d{3})\s+(.+)', first_cell)
        if dept_match and len(dept_match.group(1)) == 3 and not re.match(r'^\d{6}', first_cell):
            current_dept = dept_match.group(2).strip()
            continue

        # 检测专业（6位代码开头）
        major_match = re.match(r'^(\d{6})\s+(.+)', first_cell)
        if major_match:
            code = major_match.group(1)
            name = major_match.group(2).strip()
            enrollment = None

            # 提取招生人数
            if len(row) > 1 and row[1]:
                try:
                    enrollment = int(row[1])
                except (ValueError, TypeError):
                    pass

            # 检查是否仅招收推免生
            notes = str(row[3]) if len(row) > 3 and row[3] else ""
            if "仅招收推免生" in notes:
                # 记录为仅招收推免生
                record = {
                    "major_code": code,
                    "major_name": name,
                    "department": current_dept,
                    "research_direction": "",
                    "enrollment": enrollment,
                    "subject1": "仅招收推免生",
                    "subject2": None,
                    "subject3": None,
                    "subject4": None,
                }
                subjects.append(record)
                major_records[code] = record
                last_major = code
                last_major_name = name
                last_subj = [None, None, None, None]
                continue

            # 提取考试科目：合并所有列的内容
            all_text = ""
            for cell in row[2:]:
                if cell:
                    all_text += " " + str(cell)
            subj = _parse_exam_subjects(all_text.strip())

            # 如果是同一个专业的补充行（有科目），更新已有记录
            if subj[0] is not None and code in major_records:
                existing = major_records[code]
                if existing.get("subject1") is None:
                    existing["subject1"] = subj[0]
                    existing["subject2"] = subj[1]
                    existing["subject3"] = subj[2]
                    existing["subject4"] = subj[3]
                    if enrollment and not existing.get("enrollment"):
                        existing["enrollment"] = enrollment
                    last_major = code
                    last_major_name = name
                    last_subj = subj
                    continue

            # 如果没有科目，检查备注中是否有"仅招收推免生"以外的信息
            if subj[0] is None:
                # 检查是否是补充行（已有该专业的记录但无科目）
                if code in major_records:
                    existing = major_records[code]
                    if existing.get("subject1") is not None:
                        # 已有该专业且有科目，跳过此行
                        continue

            last_major = code
            last_major_name = name
            last_subj = subj

            record = {
                "major_code": code,
                "major_name": name,
                "department": current_dept,
                "research_direction": "",
                "enrollment": enrollment,
                "subject1": subj[0],
                "subject2": subj[1],
                "subject3": subj[2],
                "subject4": subj[3],
            }
            subjects.append(record)
            if code not in major_records:
                major_records[code] = record
        else:
            # 检测研究方向行（2位代码开头）
            dir_match = re.match(r'^(\d{2})\s+(.+?)(?:\s*\((.+)\))?$', first_cell)
            if dir_match and last_major:
                dir_name = dir_match.group(2).strip()
                full_time = dir_match.group(3) or ""
                # 如果是"不分方向"，使用上一个专业的名称
                if dir_name == "不分方向":
                    dir_name = last_major_name

                # 提取招生人数
                enrollment = None
                if len(row) > 1 and row[1]:
                    try:
                        enrollment = int(row[1])
                    except (ValueError, TypeError):
                        pass

                # 尝试从当前行提取科目
                all_text = ""
                for cell in row[2:]:
                    if cell:
                        all_text += " " + str(cell)
                subj = _parse_exam_subjects(all_text.strip())

                # 如果没有科目，继承上一个专业的
                if subj[0] is None:
                    subj = last_subj

                subjects.append({
                    "major_code": last_major,
                    "major_name": dir_name,
                    "department": current_dept,
                    "research_direction": full_time,
                    "enrollment": enrollment,
                    "subject1": subj[0],
                    "subject2": subj[1],
                    "subject3": subj[2],
                    "subject4": subj[3],
                })

    if not subjects:
        return None

    return {
        "found": True,
        "university": university,
        "year": year,
        "subjects": subjects,
    }


def _parse_exam_subjects(text: str) -> list:
    """解析考试科目文本，返回4门科目。"""
    if not text:
        return [None, None, None, None]

    # 清理文本：合并换行
    text = re.sub(r'\n+', ' ', text)

    # 匹配 ①②③④ 编号的科目
    # 科目名称可以包含中文、数字、括号、"或"、"含"等
    pattern = re.compile(
        r'[①②③④]\s*\d{3}\s*'  # 编号和代码
        r'([一-龥（）\(\)、·\s\d]+?)(?=\s*[①②③④]|\s*复试|\s*$)'  # 科目名称
    )
    matches = pattern.findall(text)

    if matches:
        subjects = []
        for m in matches[:4]:
            name = m.strip()
            # 去掉末尾的"或xxx"选项部分
            name = re.sub(r'\s*或\s*$', '', name)
            if name:
                subjects.append(name)
        # 补齐4门
        while len(subjects) < 4:
            subjects.append(None)
        return subjects

    # 尝试按行解析（每行一个科目）
    lines = text.split('\n')
    subjects = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 去掉编号前缀
        line = re.sub(r'^[①②③④]\s*\d{3}\s*', '', line)
        # 跳过非科目行
        if any(skip in line for skip in ['复试', '备注', '仅招收', '方向']):
            continue
        if line and len(line) >= 2:
            subjects.append(line)
            if len(subjects) >= 4:
                break

    if subjects:
        while len(subjects) < 4:
            subjects.append(None)
        return subjects[:4]

    return [None, None, None, None]


def _parse_admission_table(rows: list, university: str, source_url: str) -> dict:
    """从表格解析名单。"""
    from datetime import datetime

    year = datetime.now().year
    year_match = re.search(r'20(\d{2})', " ".join(rows[0]))
    if year_match:
        year = 2000 + int(year_match.group(1))

    records = []
    for row in rows[1:]:
        if len(row) < 3:
            continue

        # 查找考生编号（10-15位数字）
        exam_id = ""
        name = ""
        major = ""
        score = None

        for i, cell in enumerate(row):
            if re.match(r'^\d{10,15}$', cell):
                exam_id = cell
                # 姓名通常在下一个
                if i + 1 < len(row):
                    name = row[i + 1]
                # 专业在再下一个
                if i + 2 < len(row):
                    major = row[i + 2]
                # 成绩在后面
                for j in range(i + 3, len(row)):
                    if re.match(r'^\d{2,3}(\.\d+)?$', row[j]):
                        score = float(row[j])
                        break
                break

        if exam_id and name:
            records.append({
                "exam_id": exam_id,
                "name": name,
                "major": major,
                "initial_score": score,
                "retest_score": None,
                "total_score": None,
                "admission_status": None,
            })

    if not records:
        return None

    list_type = "复试名单" if "复试" in " ".join(rows[0]) else "录取名单"

    return {
        "found": True,
        "list_type": list_type,
        "year": year,
        "university": university,
        "records": records,
    }


def _parse_score_lines(text: str, university: str, source_url: str) -> dict | None:
    """直接从文本解析分数线数据，不依赖AI。"""
    from datetime import datetime

    # 提取学校名
    uni_match = re.search(r'([一-龥]+大学)', text)
    if uni_match and university == "未知学校":
        university = uni_match.group(1)

    # 提取年份
    year_match = re.search(r'20(\d{2})\s*年', text)
    year = 2000 + int(year_match.group(1)) if year_match else datetime.now().year

    # 清理文本：合并换行，但保留[代码]前的换行用于分割
    # 先将 "学\n术" 这种拆字合并
    cleaned = re.sub(r'([一-龥])\n([一-龥])', r'\1\2', text)
    # 合续行（不以[开头的行合并到上一行）
    lines = cleaned.split('\n')
    merged_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 如果这行以数字开头且上一行以]结尾，可能是续行（成绩部分）
        if merged_lines and re.match(r'^\d+\s+\d+\s+\d+$', line):
            merged_lines[-1] += ' ' + line
        elif merged_lines and not re.search(r'\[\d', line) and re.match(r'^[一-龥]', line):
            # 普通续行
            merged_lines[-1] += line
        else:
            merged_lines.append(line)

    text_cleaned = '\n'.join(merged_lines)

    # 匹配模式：学科名称[代码] 总分 单科1 单科2
    # 支持多行学科名，如 "城乡规划[0853]、电子信息[0854]、机械[0855]"
    pattern = re.compile(
        r'([一-龥（）\(\)、·\s]+?)\[(\d+[A-Z]?\d*)\]\s+(\d+)\s+(\d+)\s+(\d+)',
    )

    matches = pattern.findall(text_cleaned)
    if not matches:
        # 尝试更宽松的模式：代码 总分 单科1 单科2（无学科名）
        pattern2 = re.compile(r'\[(\d+[A-Z]?\d*)\]\s+(\d+)\s+(\d+)\s+(\d+)')
        matches2 = pattern2.findall(text_cleaned)
        if matches2:
            matches = [(f"专业{code}", code, total, s1, s2) for code, total, s1, s2 in matches2]

    if not matches:
        return None

    score_lines = []
    for name, code, total, s1, s2 in matches:
        name = name.strip()
        # 跳过表头行
        if any(kw in name for kw in ['学科门类', '学位类别', '类别', '总分', '单科']):
            continue
        # 清理学科名：去掉开头的脏数据（如 "分）\n", "学", "术" 等）
        name = re.sub(r'^[分）\)\s\n]+', '', name)
        name = re.sub(r'^[学术位\s]+(?=[一-龥])', '', name)
        name = name.strip()
        if not name or len(name) < 2:
            continue

        # 判断类别
        category = "学术学位"
        pos = text_cleaned.find(f'[{code}]')
        if pos > 0:
            prefix = text_cleaned[:pos]
            if '单独考试' in prefix[-300:]:
                category = "单独考试"
            elif '专业学位' in prefix[-300:]:
                category = "专业学位"

        score_lines.append({
            "category": category,
            "discipline": name,
            "discipline_code": code,
            "total_score": int(total),
            "score1": int(s1),
            "score2": int(s2),
        })

    if not score_lines:
        return None

    return {
        "found": True,
        "list_type": "复试分数线",
        "year": year,
        "university": university,
        "score_lines": score_lines,
    }


def _parse_admission_list(text: str, university: str, source_url: str) -> dict | None:
    """直接从文本解析复试名单/录取名单数据。"""
    from datetime import datetime

    # 清理文本
    text = re.sub(r'\n\s*', ' ', text)

    # 提取学校名
    uni_match = re.search(r'([一-龥]+大学)', text)
    if uni_match and university == "未知学校":
        university = uni_match.group(1)

    # 提取年份
    year_match = re.search(r'20(\d{2})\s*年', text)
    year = 2000 + int(year_match.group(1)) if year_match else datetime.now().year

    # 匹配名单格式：序号 考生编号 姓名 专业 成绩...
    # 常见格式：
    # 1 100012025000001 张三 计算机科学与技术 350 85 435
    # 100012025000001 张三 计算机科学与技术 350
    pattern = re.compile(
        r'(\d{10,15})\s+'  # 考生编号（10-15位数字）
        r'([一-龥]{2,4})\s+'  # 姓名（2-4个汉字）
        r'([一-龥（）\(\)、·]+?)\s+'  # 专业
        r'(\d{2,3}(?:\.\d+)?)',  # 成绩
    )

    matches = pattern.findall(text)
    if not matches:
        return None

    records = []
    for exam_id, name, major, score in matches:
        records.append({
            "exam_id": exam_id,
            "name": name,
            "major": major.strip(),
            "initial_score": float(score),
            "retest_score": None,
            "total_score": None,
            "admission_status": None,
        })

    if not records:
        return None

    # 判断名单类型
    list_type = "录取名单"
    if "复试" in text and "录取" not in text:
        list_type = "复试名单"

    return {
        "found": True,
        "list_type": list_type,
        "year": year,
        "university": university,
        "records": records,
    }


def _parse_catalog(text: str, university: str, source_url: str) -> dict | None:
    """直接从文本解析招生专业目录数据。"""
    from datetime import datetime

    # 提取学校名
    uni_match = re.search(r'([一-龥]+大学)', text)
    if uni_match and university == "未知学校":
        university = uni_match.group(1)

    # 提取年份
    year_match = re.search(r'20(\d{2})\s*年', text)
    year = 2000 + int(year_match.group(1)) if year_match else datetime.now().year

    # 匹配专业代码行：6位代码 专业名称 [人数]
    # 例如：020100 理论经济学 10
    code_pattern = re.compile(r'^(\d{6})\s+([一-龥（）\(\)、·A-Z]+)', re.MULTILINE)

    # 匹配考试科目：①②③④开头
    # 例如：①101 思想政治理论
    subject_pattern = re.compile(r'[①②③④](\d{3})\s*([一-龥（）\(\)、·\s]+?)(?=[①②③④]|复试|$)')

    subjects = []
    for match in code_pattern.finditer(text):
        code = match.group(1)
        name = match.group(2).strip()

        # 跳过表头
        if '学科代码' in name or '备注' in name:
            continue

        # 在该专业代码后查找考试科目
        start_pos = match.end()
        # 找到下一个专业代码的位置（或文本结束）
        next_code = code_pattern.search(text, start_pos)
        end_pos = next_code.start() if next_code else len(text)

        section = text[start_pos:end_pos]

        # 提取4门考试科目
        exam_subjects = []
        for sm in subject_pattern.finditer(section):
            subj_name = sm.group(2).strip()
            # 清理科目名
            subj_name = re.sub(r'\s+', '', subj_name)
            if subj_name and '复试' not in subj_name:
                exam_subjects.append(subj_name)

        # 如果没找到带编号的科目，尝试其他格式
        if not exam_subjects:
            # 尝试匹配 "思想政治理论" 等直接出现的科目名
            common_subjects = ['思想政治理论', '英语', '数学', '日语', '俄语', '法语', '德语']
            for subj in common_subjects:
                if subj in section:
                    exam_subjects.append(subj)

        # 补齐4门科目
        while len(exam_subjects) < 4:
            exam_subjects.append(None)
        exam_subjects = exam_subjects[:4]

        # 提取学院（在专业代码前面找）
        dept = ""
        dept_match = re.search(r'(\d{3})\s+([一-龥]+(?:学院|系|部|中心))', text[:match.start()])
        if dept_match:
            dept = dept_match.group(2)

        subjects.append({
            "major_code": code,
            "major_name": name,
            "department": dept,
            "research_direction": "",
            "subject1": exam_subjects[0],
            "subject2": exam_subjects[1],
            "subject3": exam_subjects[2],
            "subject4": exam_subjects[3],
        })

    if not subjects:
        return None

    return {
        "found": True,
        "university": university,
        "year": year,
        "subjects": subjects,
    }


async def _ocr_pdf(pdf_bytes: bytes) -> str:
    """使用OCR识别PDF中的文字（用于扫描件）。"""
    try:
        import easyocr
        import fitz  # PyMuPDF

        # 初始化OCR读取器（中文+英文）
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

        # 将PDF转为图片
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []

        for page_num in range(min(len(doc), 20)):  # 最多处理20页
            page = doc[page_num]
            # 提高分辨率
            mat = fitz.Matrix(2, 2)  # 2倍缩放
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # OCR识别
            results = reader.readtext(img_bytes)
            page_text = " ".join([r[1] for r in results])
            if page_text.strip():
                text_parts.append(page_text)

        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("未安装easyocr或PyMuPDF，无法进行OCR识别")
        return ""
    except Exception as e:
        logger.error(f"OCR识别失败: {e}")
        return ""


class AIExtractRequest(BaseModel):
    university: str = ""
    url: str
    extract_type: str = "admission_list"  # admission_list, retest_list, program_catalog, retest_rules


@app.post("/api/ai-extract")
async def ai_extract(req: AIExtractRequest):
    """使用AI智能提取页面中的名单数据。"""
    extractor = get_ai_extractor()
    if not extractor:
        return {
            "success": False,
            "error": "未配置API Key。请在设置中配置API Key"
        }

    try:
        # 1. 获取页面内容
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(req.url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            # 检查是否是PDF
            if "pdf" in content_type:
                return {
                    "success": False,
                    "is_pdf": True,
                    "message": "该链接指向PDF文件，请使用AI智能采集功能处理PDF"
                }

            content = resp.text

        # 2. AI提取
        if req.extract_type == "program_catalog":
            result = await extractor.extract_catalog(req.url, content)
        elif req.extract_type == "retest_rules":
            result = await extractor.extract_retest_rules(req.url, content)
        else:
            # admission_list 和 retest_list 都用同一个提取方法
            result = await extractor.extract_admission_list(req.url, content)

        # 2.1 如果AI返回data_url，跟进链接提取
        data_url = result.get("data_url")

        # 2.2 兜底：如果AI没返回data_url，用关键词检测可能的数据链接
        if not result.get("found") and not data_url:
            data_url = _detect_data_link(content, req.extract_type, req.url)
            if data_url:
                logger.info(f"关键词检测到数据链接: {data_url}")

        if not result.get("found") and data_url:
            logger.info(f"跟进数据链接提取: {data_url}")
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(data_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "")

                    # 检查是否是PDF
                    if "pdf" in content_type:
                        return {
                            "success": False,
                            "is_pdf": True,
                            "pdf_url": data_url,
                            "message": "数据在PDF文件中，请使用AI智能采集功能处理"
                        }

                    content = resp.text

                # 对新页面重新提取
                if req.extract_type == "program_catalog":
                    result = await extractor.extract_catalog(data_url, content)
                elif req.extract_type == "retest_rules":
                    result = await extractor.extract_retest_rules(data_url, content)
                else:
                    result = await extractor.extract_admission_list(data_url, content)

                # 更新source_url
                if result.get("found"):
                    req.url = data_url
            except Exception as e:
                logger.warning(f"跟进数据链接失败: {e}")

        # 3. 如果提取成功，保存到数据库
        if result.get("found"):
            db = get_db()
            # 优先使用用户提供的学校名，其次使用AI识别的学校名
            university = req.university or result.get("university", "未知学校")

            if req.extract_type == "program_catalog":
                subjects = []
                for s in result.get("subjects", []):
                    try:
                        subject = ExamSubject(
                            university=university,
                            year=result.get("year", 2025),
                            major_code=str(s.get("major_code", "")),
                            major_name=str(s.get("major_name", "")),
                            department=str(s.get("department", "")),
                            research_direction=str(s.get("research_direction", "")),
                            enrollment=s.get("enrollment"),
                            subject1=s.get("subject1"),
                            subject2=s.get("subject2"),
                            subject3=s.get("subject3"),
                            subject4=s.get("subject4"),
                            source_url=req.url,
                        )
                        subjects.append(subject)
                    except Exception as e:
                        logger.warning(f"科目解析失败: {e}")

                if subjects:
                    await db.insert_exam_subjects(subjects)

                return {
                    "success": True,
                    "university": university,
                    "year": result.get("year"),
                    "count": len(subjects),
                    "sample": [s.to_dict() for s in subjects[:5]],
                }
            elif req.extract_type == "retest_rules":
                rule = RetestRule(
                    university=university,
                    year=result.get("year", 2025),
                    title=result.get("title", ""),
                    department=result.get("department", ""),
                    major=result.get("major", ""),
                    content_summary=result.get("content_summary", ""),
                    retest_format=result.get("retest_format", ""),
                    score_composition=result.get("score_composition", ""),
                    retest_content=result.get("retest_content", ""),
                    other_requirements=result.get("other_requirements", ""),
                    source_url=req.url,
                )
                await db.insert_retest_rules([rule])
                return {
                    "success": True,
                    "university": university,
                    "year": result.get("year"),
                    "count": 1,
                    "sample": [rule.to_dict()],
                }
            else:
                # 检查是否是分数线数据
                if result.get("score_lines"):
                    lines = []
                    for s in result.get("score_lines", []):
                        try:
                            line = ScoreLine(
                                university=university,
                                year=result.get("year", 2025),
                                category=s.get("category", ""),
                                discipline=s.get("discipline", ""),
                                discipline_code=s.get("discipline_code", ""),
                                total_score=_to_float(s.get("total_score")),
                                score1=_to_float(s.get("score1")),
                                score2=_to_float(s.get("score2")),
                                source_url=req.url,
                            )
                            lines.append(line)
                        except Exception as e:
                            logger.warning(f"分数线解析失败: {e}")

                    if lines:
                        await db.insert_score_lines(lines)

                    return {
                        "success": True,
                        "university": university,
                        "list_type": "复试分数线",
                        "year": result.get("year"),
                        "count": len(lines),
                        "sample": [sl.to_dict() for sl in lines[:5]],
                    }

                # admission_list 和 retest_list 处理逻辑相同
                default_type = "复试名单" if req.extract_type == "retest_list" else "录取名单"
                records = []
                for r in result.get("records", []):
                    try:
                        record = AdmissionRecord(
                            university=university,
                            year=result.get("year", 2025),
                            list_type=ListType(result.get("list_type", default_type)),
                            exam_id=str(r.get("exam_id", "")),
                            name=str(r.get("name", "")),
                            major=str(r.get("major", "")),
                            initial_score=_to_float(r.get("initial_score")),
                            retest_score=_to_float(r.get("retest_score")),
                            total_score=_to_float(r.get("total_score")),
                            admission_status=r.get("admission_status"),
                            source_url=req.url,
                        )
                        records.append(record)
                    except Exception as e:
                        logger.warning(f"记录解析失败: {e}")

                if records:
                    await db.insert_admission_records(records)

                return {
                    "success": True,
                    "university": university,
                    "list_type": result.get("list_type", default_type),
                    "year": result.get("year"),
                    "count": len(records),
                    "sample": [r.to_dict() for r in records[:5]],
                }

        # 4. 如果是PDF链接，返回提示
        if result.get("pdf_url"):
            return {
                "success": False,
                "is_pdf": True,
                "pdf_url": result["pdf_url"],
                "message": "该页面指向PDF文件，请直接提供PDF链接或下载后处理",
            }

        return {"success": False, "message": "页面中未找到相关数据"}

    except Exception as e:
        logger.error(f"AI提取失败: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/manual-extract")
async def manual_extract(req: AIExtractRequest):
    """人工采集：SSE流式返回进度。"""
    extractor = get_ai_extractor()
    if not extractor:
        return StreamingResponse(
            iter([f'event: result\ndata: {json.dumps({"success": False, "error": "未配置API Key"}, ensure_ascii=False)}\n\n']),
            media_type="text/event-stream",
        )

    def step_event(step: str, status: str, detail: str = "") -> str:
        return f"event: step\ndata: {json.dumps({'step': step, 'status': status, 'detail': detail}, ensure_ascii=False)}\n\n"

    def result_event(data: dict) -> str:
        return f"event: result\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_stream():
        try:
            # 步骤1：获取页面
            yield step_event("获取页面内容", "running")
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(req.url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")

                if "pdf" in content_type:
                    yield step_event("获取页面内容", "done", "检测到PDF文件")
                    yield result_event({"success": False, "is_pdf": True, "message": "该链接指向PDF文件，请使用AI智能采集功能处理"})
                    return

                content = resp.text
                yield step_event("获取页面内容", "done", f"页面大小: {len(content)} 字符")

            # 步骤2：AI分析
            yield step_event("AI分析页面内容", "running")
            if req.extract_type == "program_catalog":
                result = await extractor.extract_catalog(req.url, content)
            elif req.extract_type == "retest_rules":
                result = await extractor.extract_retest_rules(req.url, content)
            else:
                result = await extractor.extract_admission_list(req.url, content)

            # 步骤2.1：跟进数据链接
            data_url = result.get("data_url")
            if not result.get("found") and not data_url:
                data_url = _detect_data_link(content, req.extract_type, req.url)

            # 标记AI分析步骤完成
            if result.get("found"):
                count = len(result.get("records", result.get("subjects", [])))
                yield step_event("AI分析页面内容", "done", f"找到 {count} 条数据")
            elif data_url:
                yield step_event("AI分析页面内容", "done", "检测到数据链接")
            else:
                yield step_event("AI分析页面内容", "done", "页面无直接数据")

            if not result.get("found") and data_url:
                yield step_event("跟进数据链接", "running", data_url[:80])
                try:
                    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                        resp = await client.get(data_url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        })
                        resp.raise_for_status()

                        # 检查是否是PDF
                        if "pdf" in resp.headers.get("content-type", "") or data_url.lower().endswith(".pdf"):
                            yield step_event("跟进数据链接", "done", "下载PDF文件")
                            pdf_bytes = resp.content
                            yield step_event("解析PDF内容", "running", f"文件大小: {len(pdf_bytes) // 1024}KB")

                            # 使用pdfplumber提取数据
                            try:
                                import io
                                import pdfplumber

                                # 先尝试表格提取
                                yield step_event("解析PDF内容", "running", "提取表格数据...")
                                all_tables = []
                                text_parts = []
                                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                                    total_pages = len(pdf.pages)
                                    for p in pdf.pages:
                                        # 提取表格
                                        tables = p.extract_tables()
                                        for table in tables:
                                            if table and len(table) > 1:
                                                all_tables.extend(table)
                                        # 同时提取文本作为备用
                                        t = p.extract_text()
                                        if t:
                                            text_parts.append(t)

                                content = "\n".join(text_parts)

                                # 如果pdfplumber提取不到文本，尝试OCR
                                if not content.strip() and not all_tables:
                                    yield step_event("解析PDF内容", "running", "文本提取失败，尝试OCR识别...")
                                    content = await _ocr_pdf(pdf_bytes)
                                    if content:
                                        yield step_event("解析PDF内容", "done", f"OCR识别 {len(content)} 字符，{total_pages} 页")
                                    else:
                                        yield step_event("解析PDF内容", "error", "OCR识别失败")
                                        yield result_event({"success": False, "message": "PDF中未提取到文本，OCR识别也失败了"})
                                        return
                                else:
                                    table_info = f"，{len(all_tables)} 行表格" if all_tables else ""
                                    yield step_event("解析PDF内容", "done", f"提取 {len(content)} 字符，{total_pages} 页{table_info}")

                                # 直接解析数据（不依赖AI）
                                yield step_event("解析数据", "running")
                                result = None
                                university = req.university or "未知学校"

                                # 优先使用表格数据解析
                                if all_tables:
                                    result = _parse_table_data(all_tables, university, data_url)

                                # 表格解析失败，回退到文本解析
                                if not result or not result.get("found"):
                                    parsers = [
                                        ("分数线", _parse_score_lines),
                                        ("名单", _parse_admission_list),
                                        ("招生目录", _parse_catalog),
                                    ]
                                    for parser_name, parser_func in parsers:
                                        result = parser_func(content, university, data_url)
                                        if result and result.get("found"):
                                            break

                                if result and result.get("found"):
                                    data_type = result.get("list_type", "招生目录")
                                    count = len(result.get("records", result.get("score_lines", result.get("subjects", []))))
                                    yield step_event("解析数据", "done", f"识别为{data_type}，解析 {count} 条数据")
                                    req.url = data_url
                                else:
                                    yield step_event("解析数据", "error", "未能识别数据格式")
                                    result = {"found": False, "message": "PDF文本未能匹配已知数据格式"}
                            except ImportError:
                                yield step_event("解析PDF内容", "error", "未安装pdfplumber")
                                yield result_event({"success": False, "message": "未安装pdfplumber，无法处理PDF文件"})
                                return
                            except Exception as e:
                                yield step_event("解析PDF内容", "error", str(e)[:100])
                                yield result_event({"success": False, "message": f"PDF解析失败: {e}"})
                                return
                        else:
                            content = resp.text

                    # PDF已在上面处理完毕，跳过HTML分析
                    is_pdf = "pdf" in resp.headers.get("content-type", "") or data_url.lower().endswith(".pdf")

                    if not is_pdf:
                        # 检测是否是动态系统（ASP.NET、PHP等）
                        is_dynamic_system = any(marker in content for marker in [
                            '__VIEWSTATE', '__EVENTVALIDATION',  # ASP.NET
                            'angular', 'ng-app', 'vue', 'react',  # 前端框架
                            'ajax', 'XMLHttpRequest', 'fetch(',  # AJAX动态加载
                        ])

                        if is_dynamic_system:
                            yield step_event("跟进数据链接", "done", "检测到动态查询系统")
                            yield step_event("提示", "running", "该链接指向动态查询系统，数据需要通过浏览器交互获取")

                            # 尝试从页面中提取专业列表供用户参考
                            from selectolax.parser import HTMLParser as SHP
                            tree = SHP(content)
                            select_options = []
                            for option in tree.css("select option"):
                                val = option.attributes.get("value", "")
                                text = option.text(strip=True)
                                if val and text and "--" not in text:
                                    select_options.append({"value": val, "text": text})

                            if select_options:
                                yield step_event("提示", "done", f"发现 {len(select_options)} 个专业选项")

                            yield result_event({
                                "success": False,
                                "is_dynamic": True,
                                "message": "该链接指向动态查询系统，数据需要在浏览器中选择条件后动态加载，无法直接提取",
                                "data_url": data_url,
                                "suggestion": "建议：1) 使用自动采集功能 2) 或直接提供PDF/静态页面链接",
                                "options": select_options[:20] if select_options else [],
                            })
                            return

                        yield step_event("跟进数据链接", "done", f"页面大小: {len(content)} 字符")
                        yield step_event("AI分析链接页面", "running")
                        if req.extract_type == "program_catalog":
                            result = await extractor.extract_catalog(data_url, content)
                        elif req.extract_type == "retest_rules":
                            result = await extractor.extract_retest_rules(data_url, content)
                        else:
                            result = await extractor.extract_admission_list(data_url, content)
                        if result.get("found"):
                            req.url = data_url
                            count = len(result.get("records", result.get("subjects", [])))
                            yield step_event("AI分析链接页面", "done", f"成功提取 {count} 条数据")
                        else:
                            yield step_event("AI分析链接页面", "error", result.get("reason", "未找到数据"))
                except Exception as e:
                    yield step_event("跟进数据链接", "error", str(e)[:100])

            if not result.get("found"):
                yield result_event({"success": False, "message": "页面中未找到相关数据"})
                return

            # 步骤3：保存数据
            yield step_event("保存数据到数据库", "running")
            db = get_db()
            university = req.university or result.get("university", "未知学校")

            if req.extract_type == "program_catalog":
                subjects = []
                for s in result.get("subjects", []):
                    try:
                        subject = ExamSubject(
                            university=university, year=result.get("year", 2025),
                            major_code=str(s.get("major_code", "")), major_name=str(s.get("major_name", "")),
                            department=str(s.get("department", "")), research_direction=str(s.get("research_direction", "")),
                            enrollment=s.get("enrollment"),
                            subject1=s.get("subject1"), subject2=s.get("subject2"),
                            subject3=s.get("subject3"), subject4=s.get("subject4"),
                            source_url=req.url,
                        )
                        subjects.append(subject)
                    except Exception:
                        pass
                if subjects:
                    await db.insert_exam_subjects(subjects)
                yield step_event("保存数据到数据库", "done", f"保存 {len(subjects)} 条记录")
                yield result_event({"success": True, "university": university, "year": result.get("year"), "count": len(subjects), "sample": [s.to_dict() for s in subjects[:5]]})

            elif req.extract_type == "retest_rules":
                rule = RetestRule(
                    university=university, year=result.get("year", 2025),
                    title=result.get("title", ""), department=result.get("department", ""),
                    major=result.get("major", ""), content_summary=result.get("content_summary", ""),
                    retest_format=result.get("retest_format", ""), score_composition=result.get("score_composition", ""),
                    retest_content=result.get("retest_content", ""), other_requirements=result.get("other_requirements", ""),
                    source_url=req.url,
                )
                await db.insert_retest_rules([rule])
                yield step_event("保存数据到数据库", "done", "保存 1 条细则")
                yield result_event({"success": True, "university": university, "year": result.get("year"), "count": 1, "sample": [rule.to_dict()]})

            else:
                # 检查是否是分数线数据
                if result.get("score_lines"):
                    lines = []
                    for s in result.get("score_lines", []):
                        try:
                            line = ScoreLine(
                                university=university, year=result.get("year", 2025),
                                category=s.get("category", ""), discipline=s.get("discipline", ""),
                                discipline_code=s.get("discipline_code", ""),
                                total_score=_to_float(s.get("total_score")),
                                score1=_to_float(s.get("score1")), score2=_to_float(s.get("score2")),
                                source_url=req.url,
                            )
                            lines.append(line)
                        except Exception:
                            pass
                    if lines:
                        await db.insert_score_lines(lines)
                    yield step_event("保存数据到数据库", "done", f"保存 {len(lines)} 条分数线")
                    yield result_event({"success": True, "university": university, "list_type": "复试分数线", "year": result.get("year"), "count": len(lines), "sample": [sl.to_dict() for sl in lines[:5]]})
                    return

                default_type = "复试名单" if req.extract_type == "retest_list" else "录取名单"
                records = []
                for r in result.get("records", []):
                    try:
                        record = AdmissionRecord(
                            university=university, year=result.get("year", 2025),
                            list_type=ListType(result.get("list_type", default_type)),
                            exam_id=str(r.get("exam_id", "")), name=str(r.get("name", "")),
                            major=str(r.get("major", "")),
                            initial_score=_to_float(r.get("initial_score")),
                            retest_score=_to_float(r.get("retest_score")),
                            total_score=_to_float(r.get("total_score")),
                            admission_status=r.get("admission_status"), source_url=req.url,
                        )
                        records.append(record)
                    except Exception:
                        pass
                if records:
                    await db.insert_admission_records(records)
                yield step_event("保存数据到数据库", "done", f"保存 {len(records)} 条记录")
                yield result_event({"success": True, "university": university, "list_type": result.get("list_type", default_type), "year": result.get("year"), "count": len(records), "sample": [r.to_dict() for r in records[:5]]})

        except Exception as e:
            logger.error(f"人工采集失败: {e}")
            yield step_event("采集失败", "error", str(e)[:100])
            yield result_event({"success": False, "error": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _to_float(value) -> float | None:
    if value is None or value == "" or value == "null":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None



# ========== 一键采集 API ==========

class AutoCrawlRequest(BaseModel):
    university: str
    year: int = 2025
    major: str = ""
    extract_type: str = "admission_list"  # "admission_list" 或 "program_catalog"


@app.post("/api/auto-crawl")
async def auto_crawl(req: AutoCrawlRequest):
    """一键采集：SSE流式返回进度。"""
    from src.crawler.auto_crawler import AutoCrawler

    extractor = get_ai_extractor()
    crawler = AutoCrawler(ai_extractor=extractor)
    crawl_mode = "catalog" if req.extract_type == "program_catalog" else "admission"

    async def event_stream():
        final_result = None
        async for event in crawler.crawl(req.university, req.year, major=req.major, mode=crawl_mode):
            if event["event"] == "result":
                final_result = event["data"]
            else:
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

        # 保存到数据库
        if final_result and final_result.get("results"):
            db = get_db()
            for extracted in final_result["results"]:
                if crawl_mode == "catalog":
                    subjects = []
                    for s in extracted.get("subjects", []):
                        try:
                            subject = ExamSubject(
                                university=req.university,
                                year=extracted.get("year", req.year),
                                major_code=str(s.get("major_code", "")),
                                major_name=str(s.get("major_name", "")),
                                department=str(s.get("department", "")),
                                research_direction=str(s.get("research_direction", "")),
                                enrollment=s.get("enrollment"),
                                subject1=s.get("subject1"),
                                subject2=s.get("subject2"),
                                subject3=s.get("subject3"),
                                subject4=s.get("subject4"),
                                source_url=extracted.get("source_url", ""),
                            )
                            subjects.append(subject)
                        except Exception as e:
                            logger.warning(f"科目解析失败: {e}")
                    if subjects:
                        await db.insert_exam_subjects(subjects)
                        extracted["saved_count"] = len(subjects)
                else:
                    records = []
                    for r in extracted.get("records", []):
                        try:
                            record = AdmissionRecord(
                                university=req.university,
                                year=extracted.get("year", req.year),
                                list_type=ListType(extracted.get("list_type", "录取名单")),
                                exam_id=str(r.get("exam_id", "")),
                                name=str(r.get("name", "")),
                                major=str(r.get("major", "")),
                                initial_score=_to_float(r.get("initial_score")),
                                retest_score=_to_float(r.get("retest_score")),
                                total_score=_to_float(r.get("total_score")),
                                admission_status=r.get("admission_status"),
                                source_url=extracted.get("source_url", ""),
                            )
                            records.append(record)
                        except Exception as e:
                            logger.warning(f"记录解析失败: {e}")
                    if records:
                        await db.insert_admission_records(records)
                        extracted["saved_count"] = len(records)

        # 发送最终结果（含saved_count）
        if final_result:
            yield f"event: result\ndata: {json.dumps(final_result, ensure_ascii=False)}\n\n"
        else:
            error_result = {"success": False, "university": req.university, "year": req.year, "results": [], "errors": ["采集过程异常终止"]}
            yield f"event: result\ndata: {json.dumps(error_result, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/grad-schools")
async def get_grad_schools():
    """获取所有已知的研究生院官网列表。"""
    from src.crawler.auto_crawler import GRAD_SCHOOL_URLS
    return {
        "schools": [
            {"name": name, "url": url}
            for name, url in GRAD_SCHOOL_URLS.items()
        ]
    }


# ========== 设置 API ==========

class SaveSettingsRequest(BaseModel):
    ai_provider: str
    ai_api_key: str
    ai_base_url: str = ""
    ai_model: str = ""


@app.get("/api/settings")
async def get_settings():
    """获取当前设置。"""
    settings = load_settings()
    return {
        "ai_provider": settings.get("ai_provider", ""),
        "ai_api_key": settings.get("ai_api_key", ""),
        "ai_base_url": settings.get("ai_base_url", ""),
        "ai_model": settings.get("ai_model", ""),
    }


@app.post("/api/settings")
async def update_settings(req: SaveSettingsRequest):
    """保存设置。"""
    settings = {
        "ai_provider": req.ai_provider,
        "ai_api_key": req.ai_api_key,
        "ai_base_url": req.ai_base_url,
        "ai_model": req.ai_model,
    }
    save_settings(settings)
    return {"status": "ok", "message": "设置已保存"}


@app.get("/api/ai-providers")
async def get_ai_providers():
    """获取支持的AI模型列表。"""
    return {"providers": AI_PROVIDERS}


@app.get("/api/ai-status")
async def ai_status():
    """检查AI功能是否可用。"""
    config = get_ai_config()
    if not config:
        return {
            "available": False,
            "message": "未配置AI，请在设置中配置API Key",
        }

    return {
        "available": True,
        "provider": config.get("provider"),
        "model": config.get("model"),
        "message": f"已配置 {AI_PROVIDERS.get(config.get('provider'), {}).get('name', config.get('provider'))}",
    }


# ========== 图片识别 API ==========

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}


@app.get("/api/ocr-status")
async def ocr_status():
    """检查 OCR 引擎是否可用。"""
    import importlib.util

    if importlib.util.find_spec("rapidocr_onnxruntime") is not None:
        return {"available": True, "engine": "RapidOCR", "install_hint": ""}
    if importlib.util.find_spec("easyocr") is not None:
        return {"available": True, "engine": "EasyOCR", "install_hint": ""}
    return {
        "available": False,
        "engine": None,
        "install_hint": "pip install rapidocr-onnxruntime",
    }


@app.post("/api/extract-image")
async def extract_image(file: UploadFile = File(...)):
    """从考研招生图片中提取结构化数据（SSE 流式返回进度）。"""
    from src.crawler.image_extractor import ImageExtractor

    # 验证文件类型
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        return {
            "success": False,
            "error": f"不支持的文件类型: {file.content_type}，支持: PNG, JPEG, GIF, WebP, BMP",
        }

    # 验证AI配置
    extractor = ImageExtractor.from_settings()
    if not extractor:
        return {
            "success": False,
            "error": "未配置AI，请在设置中配置API Key",
        }

    # 读取图片
    try:
        image_bytes = await file.read()
        if len(image_bytes) > 20 * 1024 * 1024:  # 20MB限制
            return {"success": False, "error": "图片文件过大，最大支持20MB"}
    except Exception as e:
        return {"success": False, "error": f"读取图片失败: {e}"}

    # 使用 SSE 流式返回进度
    import asyncio
    from queue import Queue

    progress_queue = Queue()

    def progress_callback(step, status, detail, progress):
        progress_queue.put({
            "step": step,
            "status": status,
            "detail": detail,
            "progress": progress,
        })

    async def event_stream():
        # 启动识别任务
        task = asyncio.create_task(
            extractor.extract_from_image(image_bytes, file.content_type, progress_callback)
        )

        # 流式返回进度
        while not task.done():
            while not progress_queue.empty():
                event = progress_queue.get_nowait()
                yield f"event: progress\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

        # 获取最终结果
        result = task.result()
        logger.info(
            f"图片识别完成: success={result.get('success', False)}, "
            f"precision={result.get('precision_mode', 'unknown')}, "
            f"passes={result.get('ocr_passes', 0)}"
        )
        yield f"event: result\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/save-image-data")
async def save_image_data(data: dict):
    """保存图片识别结果到数据库（按学校分类）。"""
    from datetime import datetime

    db = get_db()
    school_name = data.get("schoolName", "")
    if not school_name:
        return {"success": False, "error": "缺少学校名称"}

    saved_count = 0
    errors = []
    year = datetime.now().year

    async with aiosqlite.connect(db.db_path) as conn:
        # 支持新的 rows 格式（可编辑表格）
        rows = data.get("rows", [])
        if rows:
            for row in rows:
                major_name = row.get("majorName", "").strip()
                if not major_name:
                    continue

                college_name = row.get("collegeName", "").strip()
                major_code = row.get("majorCode", "").strip()
                subjects_str = row.get("subjects", "")
                subjects = [s.strip() for s in subjects_str.split("、") if s.strip()] if subjects_str else []

                subject1 = subjects[0] if len(subjects) > 0 else None
                subject2 = subjects[1] if len(subjects) > 1 else None
                subject3 = subjects[2] if len(subjects) > 2 else None
                subject4 = subjects[3] if len(subjects) > 3 else None

                enrollment = None
                if row.get("plannedEnrollment"):
                    try:
                        enrollment = int(row["plannedEnrollment"])
                    except ValueError:
                        pass

                try:
                    await conn.execute(
                        """INSERT OR REPLACE INTO exam_subjects
                        (university, year, major_code, major_name, department,
                         research_direction, enrollment, subject1, subject2, subject3, subject4,
                         source_url, crawl_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            school_name, year, major_code, major_name,
                            college_name, '', enrollment,
                            subject1, subject2, subject3, subject4,
                            '', datetime.now().isoformat(),
                        )
                    )
                    saved_count += 1
                except Exception as e:
                    errors.append(f"{major_name}: {str(e)}")
        else:
            # 兼容旧的 colleges/majors 格式
            for college in data.get("colleges", []):
                college_name = college.get("collegeName", "")
                for major in college.get("majors", []):
                    major_name = major.get("majorName", "")
                    major_code = major.get("majorCode", "")
                    if not major_name:
                        continue

                    subjects = major.get("subjects", [])
                    subject1 = subjects[0] if len(subjects) > 0 else None
                    subject2 = subjects[1] if len(subjects) > 1 else None
                    subject3 = subjects[2] if len(subjects) > 2 else None
                    subject4 = subjects[3] if len(subjects) > 3 else None

                    try:
                        await conn.execute(
                            """INSERT OR REPLACE INTO exam_subjects
                            (university, year, major_code, major_name, department,
                             research_direction, enrollment, subject1, subject2, subject3, subject4,
                             source_url, crawl_time)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                school_name, year, major_code or '', major_name,
                                college_name, '', major.get("plannedEnrollment"),
                                subject1, subject2, subject3, subject4,
                                '', datetime.now().isoformat(),
                            )
                        )
                        saved_count += 1
                    except Exception as e:
                        errors.append(f"{major_name}: {str(e)}")

        await conn.commit()

    if errors:
        return {"success": True, "message": f"保存完成: {saved_count} 条成功, {len(errors)} 条失败", "errors": errors}
    return {"success": True, "message": f"成功保存 {saved_count} 条数据到 {school_name}"}
