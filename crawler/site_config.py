"""站点配置加载器 - 从 JSON 加载站点规则"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractStep:
    """提取链中的一个步骤。"""
    name: str
    extract_js: str  # 在页面执行的 JS，返回 JSON


@dataclass
class ExtractChain:
    """提取链（如 video 链：detail → play → stream）。"""
    name: str
    steps: list[ExtractStep] = field(default_factory=list)


@dataclass
class LinkPatterns:
    """列表页链接分类规则。"""
    video_detail: list[str] = field(default_factory=list)   # 正则
    art_detail: list[str] = field(default_factory=list)     # 正则
    exclude: list[str] = field(default_factory=list)        # 正则

    # 编译后的正则（初始化后填充）
    _video_detail_re: list[re.Pattern] = field(default_factory=list, repr=False)
    _art_detail_re: list[re.Pattern] = field(default_factory=list, repr=False)
    _exclude_re: list[re.Pattern] = field(default_factory=list, repr=False)

    def compile(self):
        """编译所有正则。"""
        self._video_detail_re = [re.compile(p) for p in self.video_detail]
        self._art_detail_re = [re.compile(p) for p in self.art_detail]
        self._exclude_re = [re.compile(p) for p in self.exclude]

    def is_video_detail(self, url_path: str) -> bool:
        return any(r.search(url_path) for r in self._video_detail_re)

    def is_art_detail(self, url_path: str) -> bool:
        return any(r.search(url_path) for r in self._art_detail_re)

    def is_excluded(self, url_path: str) -> bool:
        return any(r.search(url_path) for r in self._exclude_re)


@dataclass
class EntryPoint:
    """爬取入口。"""
    name: str
    url: str
    type: str  # "video" | "art"


@dataclass
class SiteConfig:
    """单个站点的完整配置。"""
    name: str
    base_url: str
    link_patterns: LinkPatterns = field(default_factory=LinkPatterns)
    extract_chains: dict[str, ExtractChain] = field(default_factory=dict)
    entry_points: list[EntryPoint] = field(default_factory=list)


def load_site_config(site_key: str, config_path: str = "") -> SiteConfig:
    """从 JSON 文件加载指定站点的配置。"""
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "..", "sites.json")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    sites = raw.get("sites", {})
    if site_key not in sites:
        available = list(sites.keys())
        raise ValueError(f"Site '{site_key}' not found. Available: {available}")

    s = sites[site_key]
    config = SiteConfig(
        name=s.get("name", site_key),
        base_url=s.get("base_url", ""),
    )

    # 解析 link_patterns
    lp = s.get("link_patterns", {})
    config.link_patterns = LinkPatterns(
        video_detail=lp.get("video_detail", []),
        art_detail=lp.get("art_detail", []),
        exclude=lp.get("exclude", []),
    )
    config.link_patterns.compile()

    # 解析 extract_chains
    for chain_name, chain_data in s.get("extract_chains", {}).items():
        steps = []
        for step_data in chain_data.get("steps", []):
            steps.append(ExtractStep(
                name=step_data["name"],
                extract_js=step_data["extract_js"],
            ))
        config.extract_chains[chain_name] = ExtractChain(name=chain_name, steps=steps)

    # 解析 entry_points
    for ep in s.get("entry_points", []):
        config.entry_points.append(EntryPoint(
            name=ep["name"],
            url=ep["url"],
            type=ep.get("type", "video"),
        ))

    return config


def list_available_sites(config_path: str = "") -> list[str]:
    """列出所有可用站点。"""
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "..", "sites.json")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return list(raw.get("sites", {}).keys())
