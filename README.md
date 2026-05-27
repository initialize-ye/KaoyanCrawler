# KaoyanCrawler

中国985/211院校研究生复试名单与录取名单数据采集系统。

## 功能特性

- 配置驱动架构，每所学校一个YAML配置文件
- 支持HTML和PDF两种数据源解析
- SQLite本地存储，支持SQL查询
- FastAPI + Vue.js Web展示界面
- 定时任务自动采集

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 安装

```bash
# 克隆项目
git clone https://github.com/yourname/KaoyanCrawler.git
cd KaoyanCrawler

# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd web/frontend
npm install
cd ../..
```

### 运行

```bash
# 运行爬虫
python -m src.main crawl --university 清华大学

# 运行所有985院校
python -m src.main crawl --scope 985

# 启动Web服务
python -m src.main serve
```

## 项目结构

```
KaoyanCrawler/
├── configs/              # 学校配置文件（每校一个YAML）
├── data/                 # SQLite数据库文件
├── src/
│   ├── crawler/          # 爬虫引擎
│   ├── parsers/          # HTML/PDF解析器
│   ├── db/               # 数据库操作
│   ├── models/           # 数据模型
│   └── api/              # FastAPI后端
├── web/
│   └── frontend/         # Vue.js前端
├── tests/                # 测试
├── scripts/              # 工具脚本
└── docs/                 # 文档
```

## 贡献指南

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可证

[MIT License](LICENSE)
