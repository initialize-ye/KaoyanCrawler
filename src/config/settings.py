"""配置管理：存储和读取用户设置。"""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "settings.json"

# 支持的AI模型配置
AI_PROVIDERS = {
    "claude": {
        "name": "Claude (Anthropic)",
        "base_url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-20250514",
        "key_placeholder": "sk-ant-...",
        "description": "Anthropic的Claude模型，擅长中文理解和结构化提取",
    },
    "openai": {
        "name": "OpenAI GPT",
        "base_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o",
        "key_placeholder": "sk-...",
        "description": "OpenAI的GPT-4o模型",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-v4-flash",
        "key_placeholder": "sk-...",
        "description": "DeepSeek V4模型，支持 deepseek-v4-flash / deepseek-v4-pro",
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.0-flash",
        "key_placeholder": "AIza...",
        "description": "Google的Gemini模型",
    },
    "qwen": {
        "name": "通义千问 (阿里云)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-plus",
        "key_placeholder": "sk-...",
        "description": "阿里云的通义千问模型",
    },
    "zhipu": {
        "name": "智谱AI (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4-flash",
        "key_placeholder": "...",
        "description": "智谱AI的GLM-4模型",
    },
    "moonshot": {
        "name": "月之暗面 (Kimi)",
        "base_url": "https://api.moonshot.cn/v1/chat/completions",
        "model": "moonshot-v1-8k",
        "key_placeholder": "sk-...",
        "description": "月之暗面的Kimi模型",
    },
    "siliconflow": {
        "name": "硅基流动",
        "base_url": "https://api.siliconflow.cn/v1/chat/completions",
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "key_placeholder": "sk-...",
        "description": "硅基流动平台，支持多种开源模型",
    },
    "custom": {
        "name": "自定义OpenAI兼容接口",
        "base_url": "",
        "model": "",
        "key_placeholder": "",
        "description": "支持任何OpenAI兼容的API接口",
    },
}


def load_settings() -> dict:
    """加载设置。"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
    return {}


def save_settings(settings: dict):
    """保存设置。"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    logger.info("设置已保存")


def get_ai_config() -> dict | None:
    """获取当前AI配置。"""
    settings = load_settings()
    provider = settings.get("ai_provider", "")
    api_key = settings.get("ai_api_key", "")

    if not provider or not api_key:
        return None

    provider_config = AI_PROVIDERS.get(provider, {}).copy()
    if not provider_config:
        return None

    # 用户自定义的base_url和model
    if settings.get("ai_base_url"):
        provider_config["base_url"] = settings["ai_base_url"]
    if settings.get("ai_model"):
        provider_config["model"] = settings["ai_model"]

    return {
        "provider": provider,
        "api_key": api_key,
        **provider_config,
    }
