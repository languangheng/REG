"""页面解析器 — 数据结构定义

PageLinks 是单页爬取结果的数据容器，被 exporter 和 group_crawler 消费。
链接提取和分类逻辑已迁移到 CrawlEngine（engine.py）。
"""

from dataclasses import dataclass, field


@dataclass
class PageLinks:
    """单页爬取结果。"""
    page_url: str = ""
    page_title: str = ""
    image_links: list[dict] = field(default_factory=list)
    video_links: list[dict] = field(default_factory=list)
    art_links: list[dict] = field(default_factory=list)
    total_links: int = 0
