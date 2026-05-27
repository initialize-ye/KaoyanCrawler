"""学校配置加载器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TargetConfig:
    """单个爬取目标的配置。"""

    name: str
    type: str  # admission_list | program_catalog
    url: str
    format: str = "html"  # html | pdf
    selectors: dict = field(default_factory=dict)
    parse_rules: dict = field(default_factory=dict)


@dataclass
class UniversityConfig:
    """单所学校的配置。"""

    name: str
    code: str
    graduate_school_url: str
    tags: list[str] = field(default_factory=list)
    targets: list[TargetConfig] = field(default_factory=list)


class ConfigLoader:
    """从YAML文件加载学校配置。"""

    def __init__(self, configs_dir: str | Path):
        self.configs_dir = Path(configs_dir)

    def load(self, university_code: str) -> UniversityConfig:
        """加载单个学校的配置。"""
        config_file = self.configs_dir / f"{university_code}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        targets = [TargetConfig(**t) for t in raw.get("targets", [])]

        return UniversityConfig(
            name=raw["name"],
            code=raw["code"],
            graduate_school_url=raw["graduate_school_url"],
            tags=raw.get("tags", []),
            targets=targets,
        )

    def load_all(self, tag: str | None = None) -> list[UniversityConfig]:
        """加载所有学校配置，可选按标签过滤。"""
        configs = []
        for config_file in sorted(self.configs_dir.glob("*.yaml")):
            if config_file.name == "template.yaml":
                continue
            config = self.load(config_file.stem)
            if tag is None or tag in config.tags:
                configs.append(config)
        return configs

    def list_universities(self, tag: str | None = None) -> list[str]:
        """列出所有可用的学校代码。"""
        codes = []
        for config_file in sorted(self.configs_dir.glob("*.yaml")):
            if config_file.name == "template.yaml":
                continue
            if tag:
                with open(config_file, encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                    if tag in raw.get("tags", []):
                        codes.append(config_file.stem)
            else:
                codes.append(config_file.stem)
        return codes
