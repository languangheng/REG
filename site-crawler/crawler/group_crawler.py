"""分组爬虫 — 按 GroupConfig 遍历 entry_points，内联核心爬取逻辑。

不修改任何已有类，仅新增本文件。

修复（相比上一版本）：
  - 内联 crawl_list_pages / crawl_video_streams / crawl_art_images，
    消除跨文件 session 管理问题
  - 每次 navigate() 前自动校验 session，失效则自动恢复
  - 增加详细日志，方便定位问题

用法（CLI）:
    python -m crawler.group_crawler --site www_mimimi_top
    python -m crawler.group_crawler --site www_mimimi_top --group 视频 --deep --deep-limit 3

SSE 事件格式（与 site_manager.py 兼容）:
    [EVENT] {"event": "crawl_start", "site": "...", "groups": 2}
    [EVENT] {"event": "group_start", "group": "视频", "resource_type": "video", "entries": 2}
    [EVENT] {"event": "entry_start", "group": "视频", "entry_name": "最新", "url": "..."}
    [EVENT] {"event": "page_start", "group": "视频", "entry": "最新", "page": 1, "url": "..."}
    [EVENT] {"event": "page_result", "group": "视频", "page": 1, "video": 20, "art": 0}
    [EVENT] {"event": "deep_start", "group": "视频", "chain": "video", "total": 60}
    [EVENT] {"event": "resource_found", "type": "stream", "url": "...", "title": "...", "group": "视频"}
    [EVENT] {"event": "crawl_done", "site": "...", "output": "output/..."}
"""

import sys
import os
import json
import argparse
import time
import re
import glob as glob_mod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, urljoin

# 确保 crawler 包可被导入（subprocess 调用时 sys.path 可能不含项目根目录）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from crawler.browser_act import BrowserActClient, StateSnapshot, StateElement
from crawler.site_config import SiteConfig, GroupConfig, LinkPatterns, EntryPoint, load_site_config
from crawler.exporter import JSONExporter
from crawler.parser import PageLinks
from crawler.logger import get_logger

_logger = get_logger("group_crawler")


# ── 数据结构 ─────────────────────────────────────────────

@dataclass
class CrawlItem:
    title: str = ""
    list_url: str = ""
    detail_url: str = ""
    stream_url: str = ""
    stream_format: str = ""
    player_iframe: str = ""
    images: list[str] = field(default_factory=list)
    steps_log: list[str] = field(default_factory=list)


@dataclass
class ListPageResult:
    page_url: str = ""
    page_title: str = ""
    video_links: list[dict] = field(default_factory=list)
    art_links: list[dict] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


# ── 工具函数 ─────────────────────────────────────────────

def _log(msg: str, ltype: str = ""):
    """打印日志并写入日志文件。"""
    prefix = ""
    if ltype == "ok":
        prefix = "✅ "
        _logger.info("%s", msg)
    elif ltype == "err":
        prefix = "❌ "
        _logger.error("%s", msg)
    elif ltype == "warn":
        prefix = "⚠️ "
        _logger.warning("%s", msg)
    else:
        _logger.info("%s", msg)
    # stdout 保留输出给 SSE 管道（子进程 stdout 被 site_manager 读取）
    print(f"{prefix}{msg}", flush=True)


def _emit(event_type: str, **kwargs):
    """输出结构化事件，site_manager SSE 端可解析，同时写入日志文件。"""
    payload = json.dumps({"event": event_type, **kwargs}, ensure_ascii=False)
    _logger.info("[EVENT] %s %s", event_type, json.dumps(kwargs, ensure_ascii=False)[:200])
    # stdout 保留输出给 SSE 管道
    print(f"[EVENT] {payload}", flush=True)


def _smart_sleep(client: BrowserActClient, selector: str, seconds: float):
    """智能等待：wait_selector 成功后立即继续，超时则已等待 seconds。"""
    try:
        client.wait_selector(selector, timeout=int(seconds * 1000))
    except Exception:
        pass


# ── Session 保活 ─────────────────────────────────────────────

class SessionGuard:
    """Session 保活器：每次 navigate 前自动校验，失效则恢复。"""

    def __init__(self, client: BrowserActClient, first_url: str = "", max_wait_cf: int = 90):
        self.client = client
        self.first_url = first_url
        self.max_wait_cf = max_wait_cf
        self._last_check = 0
        self._check_interval = 5  # 每 5 秒检查一次

    def ensure_alive(self):
        """检查 session 是否还活着，死了就恢复。"""
        now = time.time()
        if now - self._last_check < self._check_interval:
            return
        self._last_check = now

        if self.client._session_exists():
            return

        _log("Session 失效，自动恢复...", "warn")
        _emit("session_recover", url=self.first_url)
        try:
            self.client.ensure_session(self.first_url, max_wait_cf=self.max_wait_cf)
            _log("Session 恢复成功", "ok")
            _emit("session_ready", title=self.client.parsed_state().title)
        except Exception as e:
            _log(f"Session 恢复失败: {e}", "err")
            _emit("session_error", error=str(e))
            raise

    def navigate(self, url: str):
        """带 session 保活的 navigate。"""
        self.ensure_alive()
        return self.client.navigate(url)

    def get_markdown(self) -> str:
        """带 session 保活的 get_markdown。"""
        self.ensure_alive()
        return self.client.get_markdown()

    def parsed_state(self) -> StateSnapshot:
        """带 session 保活的 parsed_state。"""
        self.ensure_alive()
        return self.client.parsed_state()


# ── Markdown 链接提取 ──────────────────────────────────────

def extract_links_from_markdown(md: str, base_url: str = "") -> list[dict]:
    """从 markdown 文本中提取 [text](url) 链接。"""
    links = []
    pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
    seen = set()
    for m in pattern.finditer(md):
        text = m.group(1).strip()
        url = m.group(2).strip()
        if url in seen:
            continue
        seen.add(url)
        if url.startswith('#') or url.startswith('javascript:'):
            continue
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        links.append({"text": text, "url": url})
    return links


def classify_links(
    links: list[dict],
    link_patterns: LinkPatterns,
) -> tuple[list[dict], list[dict], list[str]]:
    """按 link_patterns 分类链接。"""
    video_links = []
    art_links = []
    image_urls = []

    for link in links:
        url = link["url"]
        path = urlparse(url).path

        if any(r.search(path) for r in link_patterns._exclude_re):
            continue

        if any(path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            image_urls.append(url)
            continue

        if any(r.search(path) for r in link_patterns._video_detail_re):
            video_links.append(link)
            continue

        if any(r.search(path) for r in link_patterns._art_detail_re):
            art_links.append(link)
            continue

    return video_links, art_links, image_urls


# ── 列表页爬取（内联自 fast_crawler.py）─────────────────────

def _construct_next_page_url(cur_url: str, current_page: int) -> str:
    """基于当前 URL 模式构造下一页 URL。"""
    next_page = current_page + 1
    m = re.match(r'^(.*---)' + str(current_page) + r'(-+\.html)$', cur_url)
    if not m and current_page == 1:
        m2 = re.match(r'^(.*---)(-+\.html)$', cur_url)
        if m2:
            dashes = m2.group(2).replace('.html', '')
            return f"{m2.group(1)}2{dashes[1:]}.html"
    if m:
        return f"{m.group(1)}{next_page}{m.group(2)}"
    return ""


def crawl_list_pages_inline(
    sg: SessionGuard,
    start_url: str,
    link_patterns: LinkPatterns,
    max_pages: int = 50,
    wait_seconds: int = 4,
) -> tuple[list[ListPageResult], list[dict]]:
    """内联版列表页爬取：markdown 提链接 + state 找翻页按钮。"""
    pages = []
    all_video_links = []
    seen_urls = set()

    sg.navigate(start_url)
    _smart_sleep(sg.client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)

    for page_num in range(1, max_pages + 1):
        md = sg.get_markdown()
        snap = sg.parsed_state()
        cur_url = snap.url
        raw_links = extract_links_from_markdown(md, cur_url)
        video_links, art_links, image_urls = classify_links(raw_links, link_patterns)

        page = ListPageResult(
            page_url=cur_url,
            page_title=snap.title,
            video_links=video_links,
            art_links=art_links,
            image_urls=image_urls,
        )
        _log(f"\n[Page {page_num}] {cur_url}")
        _log(f"  links={len(raw_links)}, video={len(video_links)}, art={len(art_links)}, images={len(image_urls)}")

        for vl in video_links:
            if vl["url"] not in seen_urls:
                all_video_links.append(vl)
                seen_urls.add(vl["url"])

        pages.append(page)

        # 翻页逻辑（简化版，只处理 button_next 和 url 构造）
        next_url = ""
        if page_num < max_pages:
            next_url = _construct_next_page_url(cur_url, page_num)

        if next_url:
            _log(f"  → 下一页: {next_url[:60]}")
            try:
                sg.navigate(next_url)
                _smart_sleep(sg.client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)
            except Exception as e:
                _log(f"  翻页失败: {e}", "err")
                break
        else:
            _log("  无更多页面")
            break

    return pages, all_video_links


# ── 视频流地址提取（内联）────────────────────────────

def _find_play_button(snap: StateSnapshot) -> Optional[StateElement]:
    """从 state 中找播放按钮。"""
    play_keywords = {"立即播放", "在线播放", "播放", "Play", "play"}
    for el in snap.elements:
        if el.text.strip() in play_keywords and el.tag in ("a", "button"):
            return el
    for el in snap.elements:
        cls = el.class_name.lower()
        if "play" in cls and el.tag in ("a", "button"):
            return el
    return None


def _extract_stream_from_network(client: BrowserActClient) -> Optional[str]:
    """从 network_requests 中提取流地址。"""
    for ext in [".m3u8", ".mp4", ".flv"]:
        reqs = client.network_requests(filter_str=ext)
        for r in reqs:
            if r.get("resource_type") in ("XHR", "Fetch"):
                url = r.get("url", "")
                if ext in url:
                    return url
        for r in reqs:
            url = r.get("url", "")
            if ext in url and "player" not in url.lower():
                return url
    return None


def crawl_video_streams_inline(
    sg: SessionGuard,
    video_links: list[dict],
    deep_limit: int = 0,
    wait_seconds: int = 3,
) -> list[CrawlItem]:
    """内联版视频流地址提取。"""
    if deep_limit > 0:
        video_links = video_links[:deep_limit]

    total = len(video_links)
    results = []

    for i, link in enumerate(video_links, 1):
        title = link.get("text", "")[:50]
        url = link["url"]
        _log(f"\n  [{i}/{total}] {title[:40]}")

        item = CrawlItem(title=title, list_url=url)
        sg.client.network_clear()

        try:
            sg.navigate(url)
            _smart_sleep(sg.client, ".content, .detail, main, article", wait_seconds)
            snap = sg.parsed_state()
            item.detail_url = snap.url

            play_el = _find_play_button(snap)
            if play_el:
                sg.client.click(play_el.index)
                _smart_sleep(sg.client, "iframe, video, .dplayer, .player", wait_seconds)
                item.steps_log.append(f"click play [{play_el.index}]")

            snap = sg.parsed_state()
            is_play_page = any(kw in urlparse(snap.url).path for kw in ["/vodplay/", "/play/", "/video/play"])

            if is_play_page or play_el:
                stream_url = _extract_stream_from_network(sg.client)
                if stream_url:
                    item.stream_url = stream_url
                    item.stream_format = "m3u8" if ".m3u8" in stream_url.lower() else "mp4"
                    item.steps_log.append(f"network: {stream_url[:80]}")
                    _log(f"    ✅ stream: {stream_url[:80]}")
                else:
                    item.steps_log.append("no stream found")
                    _log(f"    ❌ no stream found")
            else:
                item.steps_log.append(f"not play page: {snap.url}")
                _log(f"    ⚠️ not play page: {snap.url[:60]}")

        except Exception as e:
            item.steps_log.append(f"error: {e}")
            _log(f"    ❌ error: {e}", "err")

        results.append(item)

    return results


# ── 图片提取（内联）────────────────────────────────

def crawl_art_images_inline(
    sg: SessionGuard,
    art_links: list[dict],
    deep_limit: int = 0,
    wait_seconds: int = 3,
) -> list[CrawlItem]:
    """内联版图片提取。"""
    if deep_limit > 0:
        art_links = art_links[:deep_limit]

    total = len(art_links)
    results = []

    for i, link in enumerate(art_links, 1):
        title = link.get("text", "")[:50]
        url = link["url"]
        _log(f"\n  [{i}/{total}] {title[:40]}")

        item = CrawlItem(title=title, detail_url=url)

        try:
            sg.navigate(url)
            _smart_sleep(sg.client, "img[src], .content, article, .detail", wait_seconds)
            sg.client.network_clear()
            images = sg.client.get_all_image_urls()
            item.images = images
            item.steps_log.append(f"found {len(images)} images")
            _log(f"    ✅ {len(images)} images")
        except Exception as e:
            item.steps_log.append(f"error: {e}")
            _log(f"    ❌ error: {e}", "err")

        results.append(item)

    return results


# ── 分组爬取核心 ─────────────────────────────────────────

def crawl_site_by_groups(
    site_config: SiteConfig,
    group_name: str = "",
    deep: bool = True,
    deep_limit: int = 0,
    wait_seconds: int = 4,
    max_pages: int = 50,
    output_dir: str = ".",
    session: str = "group_crawl",
    browser_id: str = "",
    no_close: bool = False,
) -> str:
    """按分组配置爬取站点，返回输出文件路径。"""
    client = BrowserActClient(session=session, browser_id=browser_id)

    # 筛选分组
    if group_name:
        groups = [g for g in site_config.groups if g.name == group_name]
        if not groups:
            _log(f"分组 '{group_name}' 不存在", "err")
            _emit("error", message=f"分组 '{group_name}' 不存在")
            return ""
    else:
        groups = site_config.groups

    if not groups:
        _log("站点无分组配置，无法爬取", "err")
        _emit("error", message="站点无分组配置")
        return ""

    # 初始化 SessionGuard（保活器）
    first_url = ""
    for g in groups:
        if g.entry_points:
            first_url = g.entry_points[0].url
            break

    sg = SessionGuard(client, first_url=first_url, max_wait_cf=90)

    # 初始化浏览器会话
    if first_url:
        _log(f"初始化浏览器会话: {first_url}")
        _emit("session_init", url=first_url)
        try:
            client.ensure_session(first_url, max_wait_cf=90)
            _log(f"会话就绪: {client.parsed_state().title[:50]}", "ok")
            _emit("session_ready", title=client.parsed_state().title)
        except RuntimeError as e:
            _log(f"会话初始化失败: {e}", "err")
            _emit("session_error", error=str(e))
            return ""

    _emit("crawl_start",
          site=site_config.name,
          base_url=site_config.base_url,
          groups=len(groups),
          group_names=[g.name for g in groups])

    _log(f"站点: {site_config.name} ({site_config.base_url})")
    _log(f"分组: {len(groups)} 个，入口总计: {sum(len(g.entry_points) for g in groups)} 个")

    all_pages: list[ListPageResult] = []
    all_video_links: list[dict] = []
    all_art_links: list[dict] = []
    seen_video: set = set()
    seen_art: set = set()
    deep_data: dict = {}

    t0 = time.time()

    for gidx, group in enumerate(groups, 1):
        _log(f"\n{'=' * 50}")
        _log(f"分组 [{gidx}/{len(groups)}]: {group.name} ({group.resource_type})")
        _emit("group_start",
              group=group.name,
              resource_type=group.resource_type,
              entries=len(group.entry_points),
              group_idx=gidx,
              group_total=len(groups))

        if not group.entry_points:
            _log(f"  分组 '{group.name}' 无入口点，跳过", "err")
            _emit("group_skip", group=group.name, reason="无入口点")
            continue

        # Phase 1: 列表页爬取
        group_pages: list[ListPageResult] = []
        group_video_links: list[dict] = []
        group_art_links: list[dict] = []

        for ep_idx, ep in enumerate(group.entry_points, 1):
            _log(f"\n  入口 [{ep_idx}/{len(group.entry_points)}]: {ep.name} → {ep.url}")
            _emit("entry_start",
                  group=group.name,
                  entry_idx=ep_idx,
                  entry_total=len(group.entry_points),
                  entry_name=ep.name,
                  url=ep.url)

            try:
                pages, video_links = crawl_list_pages_inline(
                    sg,
                    ep.url,
                    group.link_patterns,
                    max_pages=max_pages,
                    wait_seconds=wait_seconds,
                )
            except Exception as e:
                _log(f"  入口 {ep.name} 爬取失败: {e}", "err")
                _emit("entry_error", group=group.name, entry_name=ep.name, error=str(e))
                continue

            for page in pages:
                group_pages.append(page)
                for vl in page.video_links:
                    if vl["url"] not in seen_video:
                        group_video_links.append(vl)
                        all_video_links.append(vl)
                        seen_video.add(vl["url"])
                for al in page.art_links:
                    if al["url"] not in seen_art:
                        group_art_links.append(al)
                        all_art_links.append(al)
                        seen_art.add(al["url"])

            _emit("entry_done",
                  group=group.name,
                  entry_name=ep.name,
                  pages=len(pages),
                  video_links=len(video_links))

        _log(f"\n  分组 '{group.name}' 列表完成: "
             f"{len(group_pages)} 页, "
             f"{len(group_video_links)} 视频链接, "
             f"{len(group_art_links)} 图片链接")
        _emit("group_list_done",
              group=group.name,
              pages=len(group_pages),
              video_links=len(group_video_links),
              art_links=len(group_art_links))

        all_pages.extend(group_pages)

        # Phase 2: 深度爬取
        group_deep: dict = {}

        if not deep:
            _log(f"  (跳过深度爬取)")
            deep_data[group.name] = group_deep
            continue

        resource_type = group.resource_type

        if resource_type == "video" and group_video_links:
            _log(f"\n  深度爬取视频流地址 ({len(group_video_links)} 个)...")
            _emit("deep_start",
                  group=group.name,
                  chain="video",
                  total=len(group_video_links))

            try:
                items = crawl_video_streams_inline(
                    sg,
                    group_video_links,
                    deep_limit=deep_limit,
                    wait_seconds=wait_seconds,
                )
                got_streams = sum(1 for r in items if r.stream_url)
                group_deep["video"] = [
                    {
                        "title": r.title,
                        "list_url": r.list_url,
                        "detail_url": r.detail_url,
                        "stream_url": r.stream_url,
                        "stream_format": r.stream_format,
                    }
                    for r in items
                ]
                _log(f"  ✅ 视频: {len(items)} 爬取, {got_streams} 获取到流地址", "ok")
                _emit("chain_done",
                      group=group.name,
                      chain="video",
                      crawled=len(items),
                      streams=got_streams)

                for r in items:
                    if r.stream_url:
                        _emit("resource_found",
                              type="stream",
                              url=r.stream_url,
                              title=r.title,
                              group=group.name,
                              format=r.stream_format)

            except Exception as e:
                _log(f"  视频深度爬取失败: {e}", "err")
                _emit("deep_error", group=group.name, chain="video", error=str(e))

        elif resource_type == "art" and group_art_links:
            _log(f"\n  深度爬取图片 ({len(group_art_links)} 个详情页)...")
            _emit("deep_start",
                  group=group.name,
                  chain="art",
                  total=len(group_art_links))

            try:
                items = crawl_art_images_inline(
                    sg,
                    group_art_links,
                    deep_limit=deep_limit,
                    wait_seconds=wait_seconds,
                )
                total_imgs = sum(len(r.images) for r in items)
                group_deep["art"] = [
                    {
                        "title": r.title,
                        "detail_url": r.detail_url,
                        "images": r.images,
                        "image_count": len(r.images),
                    }
                    for r in items
                ]
                _log(f"  ✅ 图片: {len(items)} 详情页, {total_imgs} 张图片", "ok")
                _emit("chain_done",
                      group=group.name,
                      chain="art",
                      crawled=len(items),
                      images=total_imgs)

                for r in items:
                    for img_url in r.images[:3]:
                        _emit("resource_found",
                              type="image",
                              url=img_url,
                              title=r.title,
                              group=group.name)

            except Exception as e:
                _log(f"  图片深度爬取失败: {e}", "err")
                _emit("deep_error", group=group.name, chain="art", error=str(e))

        deep_data[group.name] = group_deep

    # 导出结果
    t1 = time.time()

    compat_pages = []
    for p in all_pages:
        pl = PageLinks(page_url=p.page_url, page_title=p.page_title)
        pl.video_links = p.video_links
        pl.art_links = p.art_links
        pl.image_links = [{"text": "(img)", "url": u} for u in p.image_urls]
        pl.total_links = len(p.video_links) + len(p.art_links) + len(p.image_urls)
        compat_pages.append(pl)

    if compat_pages:
        exporter = JSONExporter()
        os.makedirs(output_dir, exist_ok=True)
        output_path = exporter.save(
            compat_pages,
            site_config.base_url or "crawled",
            output_dir,
            deep_results=deep_data if deep_data else None,
        )
        _log(f"\n{'=' * 50}")
        _log(f"导出: {output_path}", "ok")
        JSONExporter.print_summary(compat_pages, output_path)

        _emit("crawl_done",
              site=site_config.name,
              output=output_path,
              pages=len(compat_pages),
              video_links=len(all_video_links),
              art_links=len(all_art_links),
              duration=round(t1 - t0, 1))

        return output_path
    else:
        _log("无数据，未导出", "err")
        _emit("crawl_done", site=site_config.name, output="", pages=0)
        return ""


# ── CLI 入口 ────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="分组爬虫 — 按 GroupConfig 遍历入口点")
    ap.add_argument("--site", "-s", required=True, help="站点配置名（sites.json 中的 key）")
    ap.add_argument("--group", help="指定分组名（空=所有分组）")
    ap.add_argument("--deep", action="store_true", help="深度爬取（提取流地址/图片）")
    ap.add_argument("--deep-limit", type=int, default=0, help="每种类型最多深入几个，0=全部")
    ap.add_argument("--wait", "-w", type=int, default=4, help="每页等待秒数")
    ap.add_argument("--max-pages", type=int, default=50, help="每个入口最多翻页数")
    ap.add_argument("--session", default="group_crawl", help="browser-act 会话名")
    ap.add_argument("--browser-id", help="复用已有浏览器 ID")
    ap.add_argument("--output-dir", "-d", default="output", help="输出目录")
    ap.add_argument("--no-close", action="store_true", help="不关闭浏览器")

    args = ap.parse_args()

    site_config = load_site_config(args.site)
    _logger.info("CLI启动: site=%s (%s), groups=%s, deep=%s, wait=%ds, max_pages=%d",
                 site_config.name, site_config.base_url,
                 [g.name for g in site_config.groups], args.deep, args.wait, args.max_pages)

    output = crawl_site_by_groups(
        site_config,
        group_name=args.group or "",
        deep=args.deep,
        deep_limit=args.deep_limit,
        wait_seconds=args.wait,
        max_pages=args.max_pages,
        output_dir=args.output_dir,
        session=args.session,
        browser_id=args.browser_id,
        no_close=args.no_close,
    )

    if output:
        _logger.info("爬取完成: output=%s", output)


if __name__ == "__main__":
    main()
