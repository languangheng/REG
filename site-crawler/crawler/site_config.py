"""站点配置加载器 - 从 JSON 加载站点规则（分组架构 + 链式操作路径）

配置结构:
  sites.json → {sites: {key: {name, base_url, site_type?, groups: [GroupConfig]}}}
  每个站点包含多个分组（GroupConfig），每个分组定义一种资源采集模式。

每个分组必须有 crawl_pattern（链式操作路径），引擎直接执行链配置。
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional


# ── 链式操作路径 ────────────────────────────────────────


@dataclass
class CrawlAction:
    """链式操作路径中的一个动作步骤。

    支持的 action 类型:
      - "navigate":       导航到 URL，url_template 或 url_from 指定来源
      - "smart_wait":     智能等待页面加载，selector + timeout + state
      - "extract_links":  从 markdown 提取链接，按 link_type 分类
      - "extract_images": 从页面提取图片 URL
      - "network_capture": 捕获网络请求中的流地址，filter 过滤
      - "click":          点击元素，selector 或 index 指定目标
      - "evaluate_js":    执行 JS 获取数据，script + save_as
      - "scroll":         滚动页面（无限滚动加载），direction + times + wait_after
      - "wait":           固定时间等待，seconds
    """
    action: str = "navigate"
    # navigate 参数
    url_template: str = ""         # URL 模板，含 {cat}/{id} 等变量槽
    url_from: str = ""             # 从上一步结果取 URL（如 "js_result"）
    # smart_wait 参数
    selector: str = ""             # CSS 选择器
    timeout: int = 5000            # 超时（毫秒）
    state: str = "attached"        # 等待状态: attached / visible
    # extract_links / extract_images 参数
    link_type: str = ""            # 链接类型（对应 link_patterns 中的 key）
    source: str = "markdown"       # 数据来源: markdown / state / all_image_urls
    # network_capture 参数
    filter: str = ""               # URL 过滤器（如 ".m3u8,.mp4,.flv"）
    wait_seconds: float = 0        # 等待秒数
    # click 参数
    index: int = 0                 # 元素 index（从 parsed_state）
    # evaluate_js 参数
    script: str = ""               # JS 代码
    save_as: str = ""              # 保存为变量名，供后续步骤引用
    # scroll 参数
    direction: str = "down"        # 滚动方向: down / up
    times: int = 3                 # 滚动次数
    wait_after: float = 2          # 每次滚动后等待秒数
    # wait 参数
    seconds: float = 3             # 固定等待秒数
    # params 参数 — 用于 url_template 中的变量槽
    params: dict = field(default_factory=dict)


@dataclass
class PaginationInChain:
    """链式翻页配置（嵌入在 list_crawl 链中）。"""
    methods: list[str] = field(default_factory=list)  # 优先级: ["button_click", "url_construct"]
    url_construct: dict = field(default_factory=dict)  # {"formula": "maccms", "url_template": "..."}
    max_pages: int = 100


@dataclass
class CrawlChain:
    """链式操作路径中的一条链（如 list_crawl、stream_capture）。"""
    name: str = ""
    steps: list[CrawlAction] = field(default_factory=list)
    pagination: Optional[PaginationInChain] = None  # 仅 list_crawl 链需要


@dataclass
class CrawlPattern:
    """一个分组的完整链式操作路径。

    链按定义顺序执行，链之间数据流自动串联:
      list_crawl 输出 → extract_links 的链接列表
      后续链输入 → 上条链的链接 URLs
      最后一条链输出 → 最终结果
    """
    chains: dict[str, CrawlChain] = field(default_factory=dict)  # OrderedDict 模拟
    chain_order: list[str] = field(default_factory=list)         # 链执行顺序


# ── 链接分类规则 ──────────────────────────────────────────


@dataclass
class LinkPatterns:
    """列表页链接分类规则 — 支持任意 link_type key（如 video_detail, play_page 等）。

    patterns: dict[str, list[str]]  — key 是 link_type 名，value 是正则列表
    exclude: list[str]              — 排除规则（独立字段）

    编译后的正则缓存:
      _compiled: dict[str, list[re.Pattern]]  — key 对应 patterns 的 key
      _exclude_re: list[re.Pattern]
    """
    patterns: dict = field(default_factory=dict)   # {link_type: [regex_str]}
    exclude: list = field(default_factory=list)     # 排除规则

    # 编译后的正则（初始化后填充）
    _compiled: dict = field(default_factory=dict, repr=False)
    _exclude_re: list = field(default_factory=list, repr=False)

    def compile(self):
        """编译所有正则。"""
        self._compiled = {}
        for link_type, regex_list in self.patterns.items():
            self._compiled[link_type] = [re.compile(p) for p in regex_list]
        self._exclude_re = [re.compile(p) for p in self.exclude]

    def match(self, url_path: str) -> str:
        """返回 url_path 匹配到的 link_type，空字符串表示无匹配。"""
        for link_type, regexes in self._compiled.items():
            if any(r.search(url_path) for r in regexes):
                return link_type
        return ""

    def is_excluded(self, url_path: str) -> bool:
        return any(r.search(url_path) for r in self._exclude_re)


# ── 入口点 ──────────────────────────────────────────────


@dataclass
class EntryPoint:
    """爬取入口。"""
    name: str
    url: str
    type: str  # "video" | "art" | "novel"


# ── 分组配置 ──────────────────────────────────────────────


@dataclass
class GroupConfig:
    """站点的一个资源采集分组。

    每个分组定义一种资源类型的完整采集模式:
    - 视频分组: entry_points 列表页 → crawl_pattern 链式操作 → 提取流地址
    - 图片分组: entry_points 列表页 → crawl_pattern 链式操作 → 提取图片
    - 小说分组: entry_points 列表页 → crawl_pattern 链式操作 → 提取正文
    """
    name: str                                     # 分组名称，如 "电影视频"、"漫画图片"
    resource_type: str                            # "video" | "art" | "novel"
    entry_points: list[EntryPoint] = field(default_factory=list)
    link_patterns: LinkPatterns = field(default_factory=LinkPatterns)
    # 链式操作路径（引擎直接执行）
    crawl_pattern: Optional[CrawlPattern] = None


# ── 站点配置 ──────────────────────────────────────────────


@dataclass
class SiteConfig:
    """单个站点的完整配置。"""
    name: str
    base_url: str
    site_type: str = ""            # "maccms" | "wordpress" | "custom" | ""（未知时留空）
    groups: list[GroupConfig] = field(default_factory=list)


# ── 反序列化（JSON → 对象）───────────────────────────────


def _parse_crawl_action(action_data: dict) -> CrawlAction:
    """解析链式操作路径中的一个动作步骤。"""
    return CrawlAction(
        action=action_data.get("action", "navigate"),
        url_template=action_data.get("url_template", ""),
        url_from=action_data.get("url_from", ""),
        selector=action_data.get("selector", ""),
        timeout=int(action_data.get("timeout", 5000)),
        state=action_data.get("state", "attached"),
        link_type=action_data.get("link_type", ""),
        source=action_data.get("source", "markdown"),
        filter=action_data.get("filter", ""),
        wait_seconds=float(action_data.get("wait_seconds", 0)),
        index=int(action_data.get("index", 0)),
        script=action_data.get("script", ""),
        save_as=action_data.get("save_as", ""),
        direction=action_data.get("direction", "down"),
        times=int(action_data.get("times", 3)),
        wait_after=float(action_data.get("wait_after", 2)),
        seconds=float(action_data.get("seconds", 3)),
        params=action_data.get("params", {}),
    )


def _parse_pagination_in_chain(pag_data: dict) -> PaginationInChain:
    """解析链式翻页配置。"""
    return PaginationInChain(
        methods=pag_data.get("methods", []),
        url_construct=pag_data.get("url_construct", {}),
        max_pages=int(pag_data.get("max_pages", 100)),
    )


def _parse_crawl_chain(chain_data: dict, chain_name: str = "") -> CrawlChain:
    """解析一条链。"""
    steps = []
    for step_data in chain_data.get("steps", []):
        if isinstance(step_data, dict):
            steps.append(_parse_crawl_action(step_data))

    pag_data = chain_data.get("pagination")
    pag = _parse_pagination_in_chain(pag_data) if pag_data else None

    return CrawlChain(
        name=chain_name or chain_data.get("name", ""),
        steps=steps,
        pagination=pag,
    )


def _parse_crawl_pattern(pattern_data: dict) -> CrawlPattern:
    """解析完整的链式操作路径。"""
    chains = {}
    chain_order = []
    for chain_name, chain_data in pattern_data.items():
        if isinstance(chain_data, dict):
            chains[chain_name] = _parse_crawl_chain(chain_data, chain_name)
            chain_order.append(chain_name)

    return CrawlPattern(chains=chains, chain_order=chain_order)


# ── MacCMS 默认链配置（内置在 Python 里，不需要外部 JSON 文件）──────────


# MacCMS 站点通用的链式操作路径默认值
# 新增 MacCMS 站时，HAR 向导检测到 site_type=maccms 后，用此默认值填充 crawl_pattern
MACCMS_CRAWL_PATTERN = {
    "list_crawl": {
        "steps": [
            {"action": "navigate", "url_template": "/vodshow/{cat}-----------.html"},
            {"action": "smart_wait", "selector": "a[href*='/voddetail/'], .vodlist-item, .stui-vodlist__box"},
            {"action": "extract_links", "source": "markdown", "link_type": "video_detail"},
        ],
        "pagination": {
            "methods": ["button_click", "url_construct"],
            "url_construct": {
                "formula": "maccms",
                "url_template": "/vodshow/{cat}--------{page}---.html",
            },
        },
    },
    "detail_crawl": {
        "steps": [
            {"action": "navigate", "url_template": "/voddetail/{id}.html"},
            {"action": "smart_wait", "selector": "a[href*='/vodplay/'], .playlist, .stui-vodlist__play"},
            {"action": "extract_links", "source": "markdown", "link_type": "play_page"},
        ],
    },
    "stream_capture": {
        "steps": [
            {"action": "navigate", "url_template": "/vodplay/{id}-{sid}-{eid}.html"},
            {"action": "smart_wait", "selector": "video, iframe[src], .player"},
            {"action": "network_capture", "filter": ".m3u8,.mp4,.flv", "wait_seconds": 5},
        ],
    },
}

MACCMS_LINK_PATTERNS = {
    "video_detail": ["/voddetail/\\d+.html", "/detail/\\d+.html"],
    "play_page": ["/vodplay/\\d+-\\d+-\\d+.html", "/play/\\d+-\\d+-\\d+.html"],
    "exclude": ["/vodshow/", "/vodtype/", "/vodsearch/", "/static/"],
}


def _parse_link_patterns(lp_data: dict) -> LinkPatterns:
    """解析链接分类规则 — 支持任意 link_type key。

    JSON 中的 patterns 字典（如 video_detail, play_page 等）会被完整解析，
    不再限制为只有 video_detail / art_detail 两种类型。
    """
    # 解析 patterns（所有非 exclude 的 key 都是 link_type）
    patterns = {}
    for key, value in lp_data.items():
        if key == "exclude":
            continue
        if isinstance(value, list):
            patterns[key] = value

    lp = LinkPatterns(
        patterns=patterns,
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

    # 链式操作路径
    crawl_pattern_data = group_data.get("crawl_pattern")
    if crawl_pattern_data and isinstance(crawl_pattern_data, dict):
        group.crawl_pattern = _parse_crawl_pattern(crawl_pattern_data)

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
        site_type=s.get("site_type", ""),
    )

    # 解析分组
    for group_data in s.get("groups", []):
        config.groups.append(_parse_group(group_data))

    return config
