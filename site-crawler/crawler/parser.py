"""页面解析器 - 从 Markdown 内容中提取链接

通用化设计：链接分类规则由 SiteConfig.link_patterns 驱动，
不再硬编码网站特定路径模式。
"""

import re
from urllib.parse import urljoin, urlparse, parse_qs
from dataclasses import dataclass, field
from typing import Optional

from .site_config import SiteConfig, LinkPatterns


# ── 通用常量（不针对特定网站）──────────────────────────────

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".bmp", ".ico", ".tiff", ".tif", ".avif",
}

VIDEO_EXTENSIONS = {
    ".mp4", ".m3u8", ".flv", ".avi", ".mkv", ".mov",
    ".wmv", ".webm", ".ts", ".m4v", ".3gp",
}


@dataclass
class PageLinks:
    """单页爬取结果。"""
    page_url: str = ""
    page_title: str = ""
    image_links: list[dict] = field(default_factory=list)
    video_links: list[dict] = field(default_factory=list)
    art_links: list[dict] = field(default_factory=list)
    total_links: int = 0


class PageParser:
    """从 browser-act 获取的 Markdown 内容中提取链接。

    Args:
        base_url: 页面基础 URL
        site_config: 站点配置（提供链接分类规则），为 None 时仅按扩展名分类
    """

    def __init__(self, base_url: str = "", site_config: Optional[SiteConfig] = None):
        self.base_url = base_url
        self.site_config = site_config

    def parse(self, markdown: str, extra_image_urls: list[str] | None = None) -> PageLinks:
        """解析页面，分类提取图片和视频链接。"""
        result = PageLinks(page_url=self.base_url)
        result.page_title = self._extract_title(markdown)

        all_links = self._extract_all_links(markdown)
        result.total_links = len(all_links)

        # 合并 JS 提取的额外图片 URL
        if extra_image_urls:
            seen_urls = {link["url"] for link in all_links}
            for url in extra_image_urls:
                full_url = self._resolve_url(url, self.base_url)
                if full_url not in seen_urls:
                    all_links.append({"text": "(img)", "url": full_url})
                    seen_urls.add(full_url)

        patterns = self.site_config.link_patterns if self.site_config else None

        for link in all_links:
            url = link["url"]

            # 先检查排除规则
            if patterns and patterns.is_excluded(url):
                continue

            if self._is_image_url(url):
                result.image_links.append(link)
            elif patterns and patterns.is_art_detail(url):
                result.art_links.append(link)
            elif self._is_video_url(url, patterns):
                result.video_links.append(link)

        return result

    def find_next_page_url(self, markdown: str, current_url: str = "") -> str | None:
        """通用下一页检测（不依赖站点配置）。"""
        base = current_url or self.base_url

        next_url = self._find_next_by_aria(markdown)
        if next_url:
            return self._resolve_url(next_url, base)

        next_url = self._find_next_by_text(markdown)
        if next_url:
            return self._resolve_url(next_url, base)

        return self._guess_next_page_from_url(base)

    # ── 链接分类 ──────────────────────────────────────────

    def _is_image_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        for ext in IMAGE_EXTENSIONS:
            if path.endswith(ext):
                return True
        if re.search(r"/(?:image|img|pic|photo|thumb|cover|poster|avatar)s?/", path):
            return True
        return False

    def _is_video_url(self, url: str, patterns: Optional[LinkPatterns] = None) -> bool:
        path = urlparse(url).path.lower()

        # 视频格式文件
        for ext in VIDEO_EXTENSIONS:
            if path.endswith(ext):
                return True

        # 站点特定的视频详情页路径
        if patterns and patterns.is_video_detail(url):
            return True

        return False

    # ── 下一页检测（通用，不变）───────────────────────────

    def _find_next_by_aria(self, markdown: str) -> str | None:
        lines = markdown.splitlines()
        for i, line in enumerate(lines):
            low = line.lower()
            if any(kw in low for kw in ['rel="next"', "rel='next'", "aria-label=\"next\"",
                                         "aria-label='next'", "aria-label=\"下一页\"",
                                         "aria-label='下一页'"]):
                for offset in range(-1, 2):
                    idx = i + offset
                    if 0 <= idx < len(lines):
                        m = re.search(r'\[([^\]]*)\]\(([^)]+)\)', lines[idx])
                        if m:
                            return m.group(2).strip()
        return None

    def _find_next_by_text(self, markdown: str) -> str | None:
        patterns = [
            r"^下一页$", r"^下页$", r"^后一页$", r"^后页$",
            r"^下一个$", r"^翻页$",
            r"^Next$", r"^Next\s*Page$", r"^next$", r"^More$",
            r"^Show\s+More$", r"^Load\s+More$",
            r"^>$", r"^›$", r"^»$", r"^≫$", r"^→$",
            r"^⟩$", r"^►$",
            r"^>\s*$", r"^›\s*$",
            r"^第\d+[页頁]$",
        ]
        pat_compiled = [re.compile(p) for p in patterns]
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        for m in re.finditer(link_pattern, markdown):
            text = m.group(1).strip()
            href = m.group(2).strip()
            for pat in pat_compiled:
                if pat.match(text):
                    return href
        return None

    def _guess_next_page_from_url(self, current_url: str) -> str | None:
        parsed = urlparse(current_url)
        path = parsed.path
        query = parse_qs(parsed.query)

        # query 参数页码
        page_params = ["page", "p", "pg", "pn", "pageNum", "pagenum", "page_num",
                       "currentPage", "current_page", "pageNo", "page_no"]
        for param in page_params:
            if param in query:
                try:
                    current_page = int(query[param][0])
                    next_page = current_page + 1
                    new_query = []
                    for k, v_list in parse_qs(parsed.query).items():
                        for v in v_list:
                            val = str(next_page) if k == param else v
                            new_query.append(f"{k}={val}")
                    return parsed._replace(query="&".join(new_query)).geturl()
                except (ValueError, IndexError):
                    continue

        # 路径页码模式
        m = re.search(r'^(.*?/page/)(\d+)(/?.*)$', path, re.IGNORECASE)
        if m:
            return parsed._replace(path=f"{m.group(1)}{int(m.group(2))+1}{m.group(3)}").geturl()

        m = re.search(r'^(.*?[_\-])(\d+)(\.html?|/?)$', path, re.IGNORECASE)
        if m:
            return parsed._replace(path=f"{m.group(1)}{int(m.group(2))+1}{m.group(3)}").geturl()

        m = re.search(r'^(.*?/p/)(\d+)(/?.*)$', path, re.IGNORECASE)
        if m:
            return parsed._replace(path=f"{m.group(1)}{int(m.group(2))+1}{m.group(3)}").geturl()

        # URL 数字位递增
        m = re.search(r'^(.*?)(\d+)([\-_]*\.html?)$', path, re.IGNORECASE)
        if m:
            return parsed._replace(path=f"{m.group(1)}{int(m.group(2))+1}{m.group(3)}").geturl()

        return None

    # ── 内部方法 ──────────────────────────────────────────

    def _extract_title(self, markdown: str) -> str:
        for line in markdown.splitlines():
            line = line.strip()
            if not line or line.startswith("[!") or line.startswith("*"):
                continue
            clean = re.sub(r"^[#]+\s*", "", line)
            clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", clean)
            clean = clean.strip()
            if clean and len(clean) > 3:
                return clean[:200]
        return ""

    def _extract_all_links(self, markdown: str) -> list[dict]:
        links: list[dict] = []
        seen: set[str] = set()
        pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        for m in re.finditer(pattern, markdown):
            text = m.group(1).strip()
            href = m.group(2).strip()
            if href.startswith("javascript:") or href.startswith("#") or href == "":
                continue
            full_url = self._resolve_url(href, self.base_url)
            if full_url in seen:
                continue
            seen.add(full_url)
            links.append({"text": text, "url": full_url})
        return links

    def _resolve_url(self, href: str, base: str = "") -> str:
        if href.startswith("http"):
            return href
        return urljoin(base or self.base_url, href)
