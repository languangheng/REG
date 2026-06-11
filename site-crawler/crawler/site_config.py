"""站点配置加载器 - 从 JSON 加载站点规则（分组架构）

配置结构:
  sites.json → {sites: {key: {name, base_url, groups: [GroupConfig]}}}
  每个站点包含多个分组（GroupConfig），每个分组定义一种资源采集模式。
  分组包含: name, resource_type, entry_points, link_patterns, extract_chains, pagination
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional


# ── 提取步骤 ──────────────────────────────────────────────


@dataclass
class ExtractStep:
    """提取链中的一个步骤。

    支持多种执行方式（method 字段）:
      - "eval_js":         执行 extract_js 中的 JS 代码（原有方式）
      - "network_capture":  从 network_requests 中按 filter 捕获流地址
      - "css_selector":     用 selector 从 DOM 提取元素
      - "interaction":      点击交互 + 网络捕获（点击 selector 指定的元素后捕获 filter 指定的流）

    向后兼容: 无 method 字段时，如果有 extract_js 则视为 "eval_js"。
    """
    name: str
    method: str = "eval_js"       # 执行方式
    extract_js: str = ""           # eval_js 方法时执行的 JS 代码
    filter: str = ""               # network_capture / interaction 方法的 URL 过滤器
    selector: str = ""              # css_selector / interaction 方法的 CSS 选择器
    wait_seconds: float = 0        # 执行后等待秒数（interaction 需要等待流出现）


@dataclass
class ExtractChain:
    """提取链（如 video 链：detail → play → stream）。"""
    name: str
    steps: list[ExtractStep] = field(default_factory=list)


# ── 链接分类规则 ──────────────────────────────────────────


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


# ── 入口点 ──────────────────────────────────────────────


@dataclass
class EntryPoint:
    """爬取入口。"""
    name: str
    url: str
    type: str  # "video" | "art" | "novel"


# ── 翻页配置 ──────────────────────────────────────────────


@dataclass
class PaginationConfig:
    """翻页配置。"""
    method: str = "auto"            # "auto" | "url_template" | "click_next" | "click_number" | "load_more" | "infinite_scroll"
    url_template: str = ""           # url_template 方法的 URL 模板（含 {page} 占位符）
    start_page: int = 1             # 起始页码
    max_pages: int = 100            # 最大翻页数
    click_selector: str = ""        # click_next / click_number 方法的按钮选择器


# ── 分组配置 ──────────────────────────────────────────────


@dataclass
class GroupConfig:
    """站点的一个资源采集分组。

    每个分组定义一种资源类型的完整采集模式:
    - 视频分组: entry_points 列表页 → link_patterns 识别详情页 → extract_chains 提取流地址
    - 图片分组: entry_points 列表页 → link_patterns 识别详情页 → extract_chains 提取图片
    - 小说分组: entry_points 列表页 → link_patterns 识别详情页 → extract_chains 提取正文
    """
    name: str                                     # 分组名称，如 "电影视频"、"漫画图片"
    resource_type: str                            # "video" | "art" | "novel"
    entry_points: list[EntryPoint] = field(default_factory=list)
    link_patterns: LinkPatterns = field(default_factory=LinkPatterns)
    extract_chains: dict[str, ExtractChain] = field(default_factory=dict)
    pagination: PaginationConfig = field(default_factory=PaginationConfig)


# ── 站点配置 ──────────────────────────────────────────────


@dataclass
class SiteConfig:
    """单个站点的完整配置。"""
    name: str
    base_url: str
    groups: list[GroupConfig] = field(default_factory=list)

    def get_group(self, group_name: str) -> Optional[GroupConfig]:
        """按名称查找分组。"""
        for g in self.groups:
            if g.name == group_name:
                return g
        return None

    def get_groups_by_type(self, resource_type: str) -> list[GroupConfig]:
        """按资源类型查找分组。"""
        return [g for g in self.groups if g.resource_type == resource_type]


# ── 序列化 / 反序列化 ────────────────────────────────────


def _parse_extract_step(step_data: dict) -> ExtractStep:
    """解析单个提取步骤，兼容旧格式。"""
    method = step_data.get("method", "")
    extract_js = step_data.get("extract_js", "")

    # 向后兼容：无 method 但有 extract_js → eval_js
    if not method:
        method = "eval_js" if extract_js else "network_capture"

    return ExtractStep(
        name=step_data.get("name", ""),
        method=method,
        extract_js=extract_js,
        filter=step_data.get("filter", ""),
        selector=step_data.get("selector", ""),
        wait_seconds=float(step_data.get("wait_seconds", 0)),
    )


def _parse_link_patterns(lp_data: dict) -> LinkPatterns:
    """解析链接分类规则。"""
    lp = LinkPatterns(
        video_detail=lp_data.get("video_detail", []),
        art_detail=lp_data.get("art_detail", []),
        exclude=lp_data.get("exclude", []),
    )
    lp.compile()
    return lp


def _parse_entry_points(ep_list: list) -> list[EntryPoint]:
    """解析入口点列表。"""
    entry_points = []
    for ep in ep_list:
        if isinstance(ep, dict):
            entry_points.append(EntryPoint(
                name=ep.get("name", ""),
                url=ep.get("url", ""),
                type=ep.get("type", "video"),
            ))
    return entry_points


def _parse_pagination(pag_data: dict) -> PaginationConfig:
    """解析翻页配置。"""
    return PaginationConfig(
        method=pag_data.get("method", "auto"),
        url_template=pag_data.get("url_template", ""),
        start_page=int(pag_data.get("start_page", 1)),
        max_pages=int(pag_data.get("max_pages", 100)),
        click_selector=pag_data.get("click_selector", ""),
    )


def _parse_extract_chains(chains_data: dict) -> dict[str, ExtractChain]:
    """解析提取链。"""
    chains = {}
    for chain_name, chain_data in chains_data.items():
        if not isinstance(chain_data, dict):
            continue
        steps = []
        for step_data in chain_data.get("steps", []):
            if isinstance(step_data, dict):
                steps.append(_parse_extract_step(step_data))
        chains[chain_name] = ExtractChain(name=chain_name, steps=steps)
    return chains


def _parse_group(group_data: dict) -> GroupConfig:
    """解析单个分组配置。"""
    group = GroupConfig(
        name=group_data.get("name", "默认分组"),
        resource_type=group_data.get("resource_type", "video"),
    )

    # 入口点
    group.entry_points = _parse_entry_points(group_data.get("entry_points", []))

    # 链接分类
    group.link_patterns = _parse_link_patterns(group_data.get("link_patterns", {}))

    # 提取链
    group.extract_chains = _parse_extract_chains(group_data.get("extract_chains", {}))

    # 翻页
    pag_data = group_data.get("pagination", {})
    if pag_data:
        group.pagination = _parse_pagination(pag_data)

    return group


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

    # 解析分组
    for group_data in s.get("groups", []):
        config.groups.append(_parse_group(group_data))

    return config


# ── 序列化（配置对象 → dict）──────────────────────────────


def _serialize_extract_step(step: ExtractStep) -> dict:
    """序列化单个提取步骤。"""
    d = {"name": step.name, "method": step.method}
    if step.extract_js:
        d["extract_js"] = step.extract_js
    if step.filter:
        d["filter"] = step.filter
    if step.selector:
        d["selector"] = step.selector
    if step.wait_seconds > 0:
        # 用 int 避免二次序列化时 3 vs 3.0 不一致
        d["wait_seconds"] = int(step.wait_seconds) if step.wait_seconds == int(step.wait_seconds) else step.wait_seconds
    return d


def _serialize_link_patterns(lp: LinkPatterns) -> dict:
    """序列化链接分类规则。"""
    d = {}
    if lp.video_detail:
        d["video_detail"] = lp.video_detail
    if lp.art_detail:
        d["art_detail"] = lp.art_detail
    if lp.exclude:
        d["exclude"] = lp.exclude
    return d


def _serialize_entry_point(ep: EntryPoint) -> dict:
    """序列化入口点。"""
    return {"name": ep.name, "url": ep.url, "type": ep.type}


def _serialize_pagination(pag: PaginationConfig) -> dict:
    """序列化翻页配置。"""
    d = {"method": pag.method}
    if pag.url_template:
        d["url_template"] = pag.url_template
    if pag.start_page != 1:
        d["start_page"] = pag.start_page
    if pag.max_pages != 100:
        d["max_pages"] = pag.max_pages
    if pag.click_selector:
        d["click_selector"] = pag.click_selector
    return d


def _serialize_extract_chain(chain: ExtractChain) -> dict:
    """序列化提取链。"""
    return {"steps": [_serialize_extract_step(s) for s in chain.steps]}


def _serialize_group(group: GroupConfig) -> dict:
    """序列化单个分组。"""
    d = {
        "name": group.name,
        "resource_type": group.resource_type,
    }

    if group.entry_points:
        d["entry_points"] = [_serialize_entry_point(ep) for ep in group.entry_points]

    lp = _serialize_link_patterns(group.link_patterns)
    if lp:
        d["link_patterns"] = lp

    if group.extract_chains:
        d["extract_chains"] = {
            name: _serialize_extract_chain(chain)
            for name, chain in group.extract_chains.items()
        }

    # 翻页配置：有非默认值时才序列化
    pag = group.pagination
    has_custom_pagination = (
        pag.method != "auto"
        or pag.url_template
        or pag.start_page != 1
        or pag.max_pages != 100
        or pag.click_selector
    )
    if has_custom_pagination:
        d["pagination"] = _serialize_pagination(pag)

    return d


def serialize_site_config(config: SiteConfig) -> dict:
    """将 SiteConfig 序列化为 dict（可直接 json.dump）。"""
    d = {
        "name": config.name,
        "base_url": config.base_url,
    }
    if config.groups:
        d["groups"] = [_serialize_group(g) for g in config.groups]
    return d


# ── 辅助函数 ──────────────────────────────────────────────


def list_available_sites(config_path: str = "") -> list[str]:
    """列出所有可用站点。"""
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "..", "sites.json")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return list(raw.get("sites", {}).keys())


def all_site_configs(config_path: str = "") -> dict[str, SiteConfig]:
    """加载所有站点配置。"""
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "..", "sites.json")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    configs = {}
    for site_key in raw.get("sites", {}):
        try:
            configs[site_key] = load_site_config(site_key, config_path)
        except Exception:
            pass
    return configs
