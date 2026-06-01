# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KaoyanCrawler is a data collection system for Chinese graduate school (考研) admission data. It scrapes retest lists (复试名单), admission lists (录取名单), exam subject catalogs, retest rules, and score lines from 985/211 universities. Two modes: config-driven crawling via per-university YAML files, and AI-powered auto-crawling using BFS traversal with LLM agents.

## Commands

### Backend (Python 3.10+)

```bash
pip install -r requirements.txt        # install dependencies
python -m src.main crawl -u 清华大学   # crawl single university
python -m src.main crawl -s 985        # crawl all 985 universities
python -m src.main serve               # start FastAPI (default port 8000)
python -m src.main serve --port 8004   # start on port 8004 (matches frontend proxy)
python -m src.main query -u 北京大学 -y 2025
python -m src.main stats
```

### Frontend (Node 18+)

```bash
cd web/frontend
npm install
npm run dev       # Vite dev server on port 3000, proxies /api to localhost:8004
npm run build     # production build → dist/
```

### Linting

```bash
ruff check .      # Python linting (line-length 100, target py310)
ruff format .     # Python formatting
```

### Testing

```bash
pytest            # pytest + pytest-asyncio (tests/ directory is currently empty)
```

## Architecture

### Monorepo Layers

```
src/                    # Python backend
  main.py               # Typer CLI: crawl, query, stats, serve
  crawler/
    engine.py           # Config-driven crawler (HTML/PDF from YAML targets)
    auto_crawler.py     # AI-driven BFS crawler (SSE streaming, search engine fallback)
    ai_extractor.py     # Multi-provider LLM calls (navigation, extraction, catalog, URL inference)
    image_extractor.py  # OCR pipeline: multi-pass OCR (RapidOCR + EasyOCR) → LLM structuring
    config_loader.py    # Loads per-university YAML configs
    discovery.py        # Keyword-based link discovery
  parsers/
    html_parser.py      # selectolax-based table extraction + preview_tables()
    pdf_parser.py       # pdfplumber-based PDF table extraction
  models/schemas.py     # Dataclasses: AdmissionRecord, ExamSubject, RetestRule, ScoreLine
  db/database.py        # Async SQLite (aiosqlite), 5 tables
  api/app.py            # FastAPI REST API with CORS (all endpoints in one file)
  config/settings.py    # AI provider config, settings.json management

web/frontend/           # Vue 3 + Element Plus frontend
  src/
    App.vue             # Main layout (header, stats sidebar, search, data tables)
    components/         # AIExtractor, ImageExtractor, ConfigWizard, SettingsDialog, etc.
    composables/        # useResponsive, useDialog, useToast
    styles/tokens.css   # Design tokens (blue/teal/amber color system)

configs/                # Per-university YAML configs (~39 files, most have empty targets)
data/                   # SQLite DB (kaoyan.db) + runtime settings (settings.json)
scripts/                # University list helpers (universities_985.py, generate_configs.py)
```

### Data Flow

1. **Config-driven mode**: YAML config → `engine.py` fetches URLs → `html_parser.py`/`pdf_parser.py` extracts tables → `database.py` stores records
2. **AI auto-crawl mode**: User inputs university name → `auto_crawler.py` resolves grad school URL (search engine or hardcoded map) → BFS traversal (max depth 2, max 15 pages) → `ai_extractor.py` calls LLM for navigation decisions and data extraction → SSE streams progress to frontend → results stored in SQLite
3. **Image OCR mode**: User uploads image → `image_extractor.py` runs multi-pass OCR (contrast/denoise/binarize/sharpen) with RapidOCR + EasyOCR → watermark removal → LLM structures OCR text into JSON → user reviews → saved to database
4. **Frontend**: Vue app queries `/api/*` → FastAPI reads from SQLite → Element Plus tables display data

### AI Provider Integration

9 providers supported (Claude, OpenAI, DeepSeek, Gemini, Qwen, Zhipu, Moonshot, SiliconFlow, Custom). All use direct HTTP API calls — no SDK dependency. Claude uses native Anthropic Messages API format; others use OpenAI-compatible format. Settings stored in `data/settings.json`. Response caching uses MD5 hash keys with 1-hour TTL.

Key AI functions in `ai_extractor.py`:
- `navigate_page()` — LLM decides: extract data, follow links, or skip
- `extract_admission_list()` — LLM extracts structured student records from HTML/PDF
- `extract_catalog()` — LLM extracts exam subject catalogs
- `extract_retest_rules()` — LLM extracts retest procedure documents
- `infer_dept_urls()` — LLM guesses department URLs where admission lists might be

### Database Schema

Five SQLite tables in `data/kaoyan.db`:

- `admission_records`: university, year, list_type (复试名单/录取名单), exam_id, name, major, initial_score, retest_score, total_score, admission_status, admission_type, study_mode. UNIQUE on (university, year, list_type, exam_id).
- `exam_subjects`: university, year, major_code, major_name, department, research_direction, enrollment, subject1-4, score statistics (retest_score_line, admission_count, admission_min/median/max/avg_score, etc.). UNIQUE on (university, year, major_code, department, research_direction).
- `retest_rules`: university, year, title, department, major, content_summary, retest_format, score_composition. UNIQUE on (university, year, title, department).
- `score_lines`: university, year, category, discipline, discipline_code, total_score, score1, score2. UNIQUE on (university, year, category, discipline).
- `schools`: name (UNIQUE), website, duration, tuition, scholarship, notes.

All tables use `INSERT OR IGNORE` for deduplication and are indexed on (university, year).

### Frontend Notes

- Element Plus components are auto-imported via `unplugin-vue-components` — no manual imports needed
- Vite dev server proxies `/api/*` to `localhost:8004` — backend `serve` defaults to port 8000, so start with `--port 8004` or change the proxy target
- `AIExtractor.vue` consumes SSE streams from `/api/auto-crawl` for real-time progress
- `ImageExtractor.vue` handles image upload, OCR preview, and LLM-structured extraction
- `ConfigWizard.vue` provides visual table-scanning for adding universities without writing YAML

## Coding Conventions

- Python: PEP 8, type hints required, line-length 100 (ruff config)
- Frontend: Vue 3 Composition API with `<script setup>` syntax
- Commit messages: Chinese or English, clearly describe the change
- New university configs go in `configs/` following `configs/template.yaml` schema
