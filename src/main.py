"""KaoyanCrawler主入口。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from loguru import logger

from src.crawler.config_loader import ConfigLoader
from src.crawler.engine import CrawlerEngine
from src.db.database import Database

app = typer.Typer(help="KaoyanCrawler - 考研数据采集系统")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIGS_DIR = BASE_DIR / "configs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "kaoyan.db"


@app.command()
def crawl(
    university: str = typer.Option(None, "--university", "-u", help="学校代码"),
    scope: str = typer.Option(None, "--scope", "-s", help="范围: 985/211/all"),
):
    """运行爬虫。"""
    asyncio.run(_crawl(university, scope))


async def _crawl(university: str | None, scope: str | None):
    loader = ConfigLoader(CONFIGS_DIR)
    engine = CrawlerEngine()
    db = Database(DB_PATH)
    await db.init()

    if university:
        configs = [loader.load(university)]
    elif scope:
        configs = loader.load_all(tag=scope)
    else:
        logger.error("请指定 --university 或 --scope")
        return

    logger.info(f"开始爬取 {len(configs)} 所学校")

    for config in configs:
        logger.info(f"正在爬取: {config.name}")
        results = await engine.crawl_university(config, DATA_DIR)

        if results["admission_records"]:
            await db.insert_admission_records(results["admission_records"])
        if results["exam_subjects"]:
            await db.insert_exam_subjects(results["exam_subjects"])

        logger.info(
            f"{config.name} 完成: "
            f"录取记录 {len(results['admission_records'])} 条, "
            f"科目记录 {len(results['exam_subjects'])} 条"
        )

    stats = await db.get_stats()
    logger.info(f"爬取完成! 数据库统计: {stats}")


@app.command()
def query(
    university: str = typer.Option(None, "--university", "-u", help="学校名称"),
    year: int = typer.Option(None, "--year", "-y", help="年份"),
    major: str = typer.Option(None, "--major", "-m", help="专业关键词"),
):
    """查询数据。"""
    asyncio.run(_query(university, year, major))


async def _query(university: str | None, year: int | None, major: str | None):
    db = Database(DB_PATH)

    records = await db.query_admissions(
        university=university, year=year, major=major
    )

    if not records:
        print("未找到匹配的记录")
        return

    print(f"共 {len(records)} 条记录:\n")
    for r in records[:50]:
        score_info = ""
        if r.get("initial_score"):
            score_info = f" | 初试: {r['initial_score']}"
        print(
            f"  {r['university']} | {r['year']} | {r['major']} | "
            f"{r['name']} | {r['list_type']}{score_info}"
        )

    if len(records) > 50:
        print(f"\n  ... 还有 {len(records) - 50} 条记录")


@app.command()
def stats():
    """显示数据库统计。"""
    asyncio.run(_stats())


async def _stats():
    db = Database(DB_PATH)
    s = await db.get_stats()
    print("数据库统计:")
    print(f"  学校数量: {s['universities']}")
    print(f"  录取记录: {s['admission_records']}")
    print(f"  科目记录: {s['exam_subjects']}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
):
    """启动Web服务。"""
    import uvicorn
    uvicorn.run("src.api.app:app", host=host, port=port, reload=True)


def cli():
    app()


if __name__ == "__main__":
    cli()
