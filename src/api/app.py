"""FastAPI Web应用。"""

from __future__ import annotations

from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
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
from src.models.schemas import AdmissionRecord, ExamSubject, ListType
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


def get_ai_extractor() -> AIExtractor | None:
    """根据用户配置获取AI提取器。"""
    config = get_ai_config()
    if not config:
        return None
    return AIExtractor(config)


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

class AIExtractRequest(BaseModel):
    university: str
    url: str
    extract_type: str = "admission_list"  # admission_list 或 program_catalog


@app.post("/api/ai-extract")
async def ai_extract(req: AIExtractRequest):
    """使用AI智能提取页面中的名单数据。"""
    extractor = get_ai_extractor()
    if not extractor:
        return {
            "success": False,
            "error": "未配置API Key。请设置环境变量 ANTHROPIC_API_KEY 或 DEEPSEEK_API_KEY"
        }

    try:
        # 1. 获取页面内容
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(req.url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            content = resp.text

        # 2. AI提取
        if req.extract_type == "admission_list":
            result = await extractor.extract_admission_list(req.url, content)
        else:
            result = await extractor.extract_catalog(req.url, content)

        # 3. 如果提取成功，保存到数据库
        if result.get("found"):
            db = get_db()
            await db.init()

            if req.extract_type == "admission_list":
                records = []
                for r in result.get("records", []):
                    try:
                        record = AdmissionRecord(
                            university=req.university,
                            year=result.get("year", 2025),
                            list_type=ListType(result.get("list_type", "录取名单")),
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
                    "list_type": result.get("list_type"),
                    "year": result.get("year"),
                    "count": len(records),
                    "sample": [r.to_dict() for r in records[:5]],
                }
            else:
                subjects = []
                for s in result.get("subjects", []):
                    try:
                        subject = ExamSubject(
                            university=req.university,
                            year=result.get("year", 2025),
                            major_code=str(s.get("major_code", "")),
                            major_name=str(s.get("major_name", "")),
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
                    "year": result.get("year"),
                    "count": len(subjects),
                    "sample": [s.to_dict() for s in subjects[:5]],
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


def _to_float(value) -> float | None:
    if value is None or value == "" or value == "null":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


@app.get("/api/ai-status")
async def ai_status():
    """检查AI功能是否可用。"""
    extractor = get_ai_extractor()
    return {
        "available": extractor is not None,
        "provider": extractor.provider if extractor else None,
        "message": "AI功能可用" if extractor else "请设置环境变量 ANTHROPIC_API_KEY 或 DEEPSEEK_API_KEY",
    }


# ========== 一键采集 API ==========

class AutoCrawlRequest(BaseModel):
    university: str
    year: int = 2025


@app.post("/api/auto-crawl")
async def auto_crawl(req: AutoCrawlRequest):
    """一键采集：只输入学校名称，自动完成全流程。"""
    from src.crawler.auto_crawler import AutoCrawler

    extractor = get_ai_extractor()
    crawler = AutoCrawler(ai_extractor=extractor)

    result = await crawler.crawl(req.university, req.year)

    # 如果有结果，保存到数据库
    if result.get("results"):
        db = get_db()
        await db.init()

        for extracted in result["results"]:
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

    return result


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
