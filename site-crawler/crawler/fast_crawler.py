"""网络优先爬虫 v2 — state 分类 + markdown 提链接 + network requests 提流

策略调整：
- state: 获取元素 index → 点击（翻页、播放按钮等交互操作）
- get_markdown: 提取链接 URL（state 输出没有 href，markdown 有完整链接）
- network requests: 提取流地址（替代 eval JS）
"""

import sys
import io
import os
import time
import re
import argparse
import glob as glob_mod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, urljoin

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient, StateSnapshot, StateElement
from crawler.site_config import SiteConfig, load_site_config
from crawler.exporter import JSONExporter
from crawler.parser import PageLinks


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


# ── Markdown 链接提取 ──────────────────────────────────────


def _smart_sleep(client: BrowserActClient, selector: str, seconds: float):
    """智能等待：wait_selector 成功后立即继续，超时则已等待 seconds。"""
    try:
        client.wait_selector(selector, timeout=int(seconds * 1000))
    except Exception:
        pass  # wait_selector 已等待了 seconds


# ── 调试截图 ──────────────────────────────────────────────

# 截图水位线配置
_SCREENSHOT_MAX = 100   # 截图总数上限
_SCREENSHOT_KEEP = 50   # 超出后保留最近数量


def _debug_screenshot(client: BrowserActClient, name: str, output_dir: str = "tmp/screenshots"):
    """调试截图：保存到 tmp/screenshots/，文件名含时间戳和场景名。

    水位线策略：
    - 截图总数超过 _SCREENSHOT_MAX 时，删除最旧的文件，保留最近 _SCREENSHOT_KEEP 张
    - 截图失败不影响主流程
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"{name}_{ts}.png")
        client.screenshot(filepath)
        print(f"  📸 screenshot: {filepath}")
        _cleanup_screenshots(output_dir)
    except Exception as e:
        print(f"  ⚠️ screenshot failed: {e}")


def _cleanup_screenshots(output_dir: str):
    """水位线清理：截图超过上限时删除最旧的，保留最近一半。"""
    try:
        files = sorted(
            glob_mod.glob(os.path.join(output_dir, "*.png")),
            key=os.path.getmtime,
        )
        if len(files) > _SCREENSHOT_MAX:
            to_delete = files[:len(files) - _SCREENSHOT_KEEP]
            for f in to_delete:
                try:
                    os.remove(f)
                except OSError:
                    pass
            print(f"  🗑️ screenshots cleanup: deleted {len(to_delete)} old files, kept {len(files) - len(to_delete)}")
    except Exception:
        pass


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
        # 忽略锚点和 JS 链接
        if url.startswith('#') or url.startswith('javascript:'):
            continue
        # 补全相对 URL
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        links.append({"text": text, "url": url})
    return links


def classify_links(
    links: list[dict],
    site_config: Optional[SiteConfig] = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """按 site_config 的 link_patterns 分类链接。

    Returns: (video_links, art_links, image_urls)
    """
    video_patterns = []
    art_patterns = []
    exclude_patterns = []
    if site_config:
        video_patterns = [re.compile(p) for p in site_config.link_patterns.video_detail]
        art_patterns = [re.compile(p) for p in site_config.link_patterns.art_detail]
        exclude_patterns = [re.compile(p) for p in site_config.link_patterns.exclude]

    video_links = []
    art_links = []
    image_urls = []

    for link in links:
        url = link["url"]
        path = urlparse(url).path

        # 排除
        if any(r.search(path) for r in exclude_patterns):
            continue

        # 图片
        if any(path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            image_urls.append(url)
            continue

        # 视频详情
        if any(r.search(path) for r in video_patterns):
            video_links.append(link)
            continue

        # 图片详情
        if any(r.search(path) for r in art_patterns):
            art_links.append(link)
            continue

    return video_links, art_links, image_urls


# ── 列表页爬取 ──────────────────────────────────────────


def crawl_list_pages(
    client: BrowserActClient,
    start_url: str,
    site_config: Optional[SiteConfig] = None,
    max_pages: int = 100,
    wait_seconds: int = 3,
) -> tuple[list[ListPageResult], list[dict]]:
    """爬取列表页：markdown 提链接 + state 找翻页按钮。

    支持翻页模式:
    - button_next: "下一页"/Next 按钮
    - number_group: 数字页码组 (1 2 3 4 5)
    - load_more: "加载更多" 按钮
    - infinite_scroll: 无限滚动

    Returns: (pages, all_video_links)
    """
    pages = []
    all_video_links = []
    seen_urls = set()

    client.navigate(start_url)
    _smart_sleep(client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)

    for page_num in range(1, max_pages + 1):
        # 1. markdown 提取链接
        md = client.get_markdown()
        snap = client.parsed_state()
        cur_url = snap.url
        raw_links = extract_links_from_markdown(md, cur_url)

        # 2. 分类
        video_links, art_links, image_urls = classify_links(raw_links, site_config)

        page = ListPageResult(
            page_url=cur_url,
            page_title=snap.title,
            video_links=video_links,
            art_links=art_links,
            image_urls=image_urls,
        )
        print(f"\n[Page {page_num}] {cur_url}")
        print(f"  links={len(raw_links)}, video={len(video_links)}, art={len(art_links)}, images={len(image_urls)}")

        # 去重
        for vl in video_links:
            if vl["url"] not in seen_urls:
                all_video_links.append(vl)
                seen_urls.add(vl["url"])

        pages.append(page)

        # 3. 获取分页信息
        pag = snap.find_pagination_info()
        pag_type = pag["type"]
        print(f"  Pagination: type={pag_type} cur={pag['current_page']} total={pag['total_pages']}")

        # 4. 翻页
        next_el = pag["next_element"]

        if pag_type == "button_next" and next_el:
            print(f"  → click [{next_el.index}] {next_el.text!r}")
            try:
                client.click(next_el.index)
                _smart_sleep(client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)
                _debug_screenshot(client, f"list_p{page_num}_after_click")
            except Exception as e:
                _debug_screenshot(client, f"list_p{page_num}_click_error")
                print(f"  Click next failed: {e}")
                break

        elif pag_type == "number_group" and next_el:
            print(f"  → click page# [{next_el.index}] {next_el.text!r}")
            try:
                client.click(next_el.index)
                _smart_sleep(client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)
                _debug_screenshot(client, f"list_p{page_num}_after_pagenum")
            except Exception as e:
                _debug_screenshot(client, f"list_p{page_num}_pagenum_error")
                print(f"  Click page# failed: {e}")
                break

        elif pag_type == "load_more" and next_el:
            print(f"  → click load-more [{next_el.index}] {next_el.text!r}")
            try:
                client.click(next_el.index)
                _smart_sleep(client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)
                # load_more 不换页，同页追加内容，继续循环
                # 检查是否有新链接
                md2 = client.get_markdown()
                snap3 = client.parsed_state()
                new_links = extract_links_from_markdown(md2, snap3.url)
                new_video, _, _ = classify_links(new_links, site_config)
                added = sum(1 for vl in new_video if vl["url"] not in seen_urls)
                if added == 0:
                    print("  No new links after load-more, stopping.")
                    break
            except Exception as e:
                print(f"  Click load-more failed: {e}")
                break

        elif pag_type == "infinite_scroll":
            # 无限滚动: 往下滚，看新内容
            print("  → infinite scroll down")
            client.scroll_down(1500)
            time.sleep(wait_seconds)
            md2 = client.get_markdown()
            snap3 = client.parsed_state()
            new_links = extract_links_from_markdown(md2, snap3.url)
            new_video, _, _ = classify_links(new_links, site_config)
            added = sum(1 for vl in new_video if vl["url"] not in seen_urls)
            if added == 0:
                print("  No new links after scroll, stopping.")
                break

        else:
            # 尝试 URL 构造翻页
            next_url = _construct_next_page_url(cur_url, page_num)
            if next_url:
                print(f"  → construct URL: {next_url[:60]}")
                try:
                    client.navigate(next_url)
                    _smart_sleep(client, "a[href*='/vodplay/'], a[href*='/arttype/'], .vodlist-item, .item, article, main", wait_seconds)
                    snap4 = client.parsed_state()
                    if snap4.url == cur_url:
                        print("  URL didn't change, stopping.")
                        break
                except Exception as e:
                    print(f"  Navigate failed: {e}")
                    break
            else:
                print("  No more pages.")
                break

    return pages, all_video_links


def _construct_next_page_url(cur_url: str, current_page: int) -> str:
    """基于当前 URL 模式构造下一页 URL。

    支持模式:
    - /vodshow/12-----------.html → /vodshow/12----------2-.html
    - /arttype/8.html → /arttype/8-2.html
    - ?page=1 → ?page=2
    - /page/1 → /page/2
    """
    next_page = current_page + 1

    # 模式 1: ----N---.html (mimimi 风格)
    m = re.match(r'^(.*---)' + str(current_page) + r'(-+\.html)$', cur_url)
    if not m and current_page == 1:
        # 第一页可能没有页码: -----.html → ------2-.html
        m2 = re.match(r'^(.*---)(-+\.html)$', cur_url)
        if m2:
            dashes = m2.group(2).replace('.html', '')
            return f"{m2.group(1)}2{dashes[1:]}.html"

    if m:
        return f"{m.group(1)}{next_page}{m.group(2)}"

    # 模式 2: /category/X.html → /category/X-2.html
    m = re.match(r'^(.*?/\w+/\d+)\.html$', cur_url)
    if m and current_page == 1:
        return f"{m.group(1)}-{next_page}.html"
    m = re.match(r'^(.*?/\w+/\d+)-\d+\.html$', cur_url)
    if m:
        return f"{m.group(1)}-{next_page}.html"

    # 模式 3: ?page=N
    m = re.search(r'[?&]page=(\d+)', cur_url)
    if m:
        return cur_url.replace(f"page={m.group(1)}", f"page={next_page}")
    if 'page=' not in cur_url and '?' in cur_url:
        return f"{cur_url}&page={next_page}"
    if '?' not in cur_url:
        return f"{cur_url}?page={next_page}"

    # 模式 4: /page/N
    m = re.search(r'/page/(\d+)', cur_url)
    if m:
        return cur_url.replace(f"/page/{m.group(1)}", f"/page/{next_page}")

    return ""


# ── 深度爬取：视频流地址 ──────────────────────────────────


def crawl_video_streams(
    client: BrowserActClient,
    video_links: list[dict],
    site_config: Optional[SiteConfig] = None,
    deep_limit: int = 0,
    wait_seconds: int = 3,
) -> list[CrawlItem]:
    """提取视频流地址：network requests 优先，eval JS 降级。"""
    if deep_limit > 0:
        video_links = video_links[:deep_limit]

    total = len(video_links)
    results = []

    for i, link in enumerate(video_links, 1):
        title = link.get("text", "")[:50]
        url = link["url"]
        print(f"\n  [{i}/{total}] {title[:40]}")

        item = CrawlItem(title=title, list_url=url)
        client.network_clear()

        try:
            # 导航到详情页
            client.navigate(url)
            _smart_sleep(client, ".content, .detail, main, article", wait_seconds)
            snap = client.parsed_state()
            item.detail_url = snap.url

            # 查找播放链接（从 state 找播放按钮 index）
            play_el = _find_play_button(snap)

            if play_el:
                snap2 = client.parsed_state()
                client.click(play_el.index)
                _smart_sleep(client, "iframe, video, .dplayer, .player", wait_seconds)
                item.steps_log.append(f"click play [{play_el.index}]")

            # 检查当前页面
            snap = client.parsed_state()
            is_play_page = any(kw in urlparse(snap.url).path for kw in ["/vodplay/", "/play/", "/video/play"])

            if is_play_page or play_el:
                # 方法 1: network requests
                stream_url = _extract_stream_from_network(client)
                if stream_url:
                    item.stream_url = stream_url
                    item.stream_format = _detect_format(stream_url)
                    item.steps_log.append(f"network: {stream_url[:80]}")
                    print(f"    ✅ stream: {stream_url[:80]}")
                else:
                    # 方法 2: eval JS
                    stream_url = _extract_stream_from_js(client)
                    if stream_url:
                        item.stream_url = stream_url
                        item.stream_format = _detect_format(stream_url)
                        item.steps_log.append(f"eval_js: {stream_url[:80]}")
                        print(f"    ✅ stream (js): {stream_url[:80]}")
                    else:
                        item.steps_log.append("no stream found")
                        print(f"    ❌ no stream found")
            else:
                item.steps_log.append(f"not play page: {snap.url}")
                print(f"    ⚠️ not play page: {snap.url[:60]}")

        except Exception as e:
            _debug_screenshot(client, f"video_{i}_error")
            item.steps_log.append(f"error: {e}")
            print(f"    ❌ error: {e}")

        results.append(item)

    return results


def _find_play_button(snap: StateSnapshot) -> Optional[StateElement]:
    play_keywords = {"立即播放", "在线播放", "播放", "Play", "play"}
    for el in snap.elements:
        if el.text.strip() in play_keywords and el.tag in ("a", "button"):
            return el
    for el in snap.elements:
        cls = el.class_name.lower()
        if "btn-warm" in cls and el.tag == "a" and "播放" in el.text:
            return el
        if "play" in cls and el.tag in ("a", "button"):
            return el
    return None


def _extract_stream_from_network(client: BrowserActClient) -> Optional[str]:
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


def _extract_stream_from_js(client: BrowserActClient) -> Optional[str]:
    js = """
JSON.stringify((() => {
    const iframes = [...document.querySelectorAll('iframe')];
    for (const f of iframes) {
        const src = f.src || '';
        if (!src) continue;
        try {
            const url = new URL(src);
            const videoUrl = url.searchParams.get('url');
            if (videoUrl && (videoUrl.includes('.m3u8') || videoUrl.includes('.mp4') || videoUrl.includes('.flv'))) {
                return videoUrl;
            }
        } catch(e) {}
        if (src.includes('.m3u8') || src.includes('.mp4')) {
            return src;
        }
    }
    return null;
})())
"""
    result = client.evaluate_json(js.strip())
    return result if isinstance(result, str) else None


def _detect_format(url: str) -> str:
    url_lower = url.lower()
    if ".m3u8" in url_lower: return "m3u8"
    if ".mp4" in url_lower: return "mp4"
    if ".flv" in url_lower: return "flv"
    return "unknown"


# ── 深度爬取：图片 ───────────────────────────────────────


def _extract_images_combined(client: BrowserActClient) -> list[str]:
    """合并 eval_js 和 network requests 两种图片提取方法，去重取并集。"""
    # 方法 1: evaluate_js — 从 DOM 提取
    eval_images = client.get_all_image_urls()

    # 方法 2: network requests — 从网络请求提取
    net_images = []
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        try:
            reqs = client.network_requests(filter_str=ext)
            for r in reqs:
                url = r.get("url", "")
                if url and ext in url.lower():
                    net_images.append(url)
        except Exception:
            pass

    # 合并去重
    all_images = list(dict.fromkeys(eval_images + net_images))

    # 过滤非内容图片
    content_images = [
        u for u in all_images
        if not any(kw in u for kw in ["/static/", "/template/", "/icon/", "logo", "favicon", ".svg"])
    ]
    return content_images


def crawl_art_images(
    client: BrowserActClient,
    art_links: list[dict],
    deep_limit: int = 0,
    wait_seconds: int = 3,
    scroll_times: int = 5,
) -> list[CrawlItem]:
    if deep_limit > 0:
        art_links = art_links[:deep_limit]

    total = len(art_links)
    results = []

    for i, link in enumerate(art_links, 1):
        title = link.get("text", "")[:50]
        url = link["url"]
        print(f"\n  [{i}/{total}] {title[:40]}")

        item = CrawlItem(title=title, detail_url=url)

        try:
            client.navigate(url)
            _smart_sleep(client, "img[src], .content, article, .detail", wait_seconds)
            # 清除旧请求，只记录本页的
            client.network_clear()
            for _ in range(scroll_times):
                client.scroll_down(800)
                time.sleep(1)
            images = _extract_images_combined(client)
            item.images = images
            item.steps_log.append(f"found {len(images)} images")
            print(f"    ✅ {len(images)} images")
        except Exception as e:
            _debug_screenshot(client, f"art_{i}_error")
            item.steps_log.append(f"error: {e}")
            print(f"    ❌ error: {e}")

        results.append(item)

    return results


# ── 主流程 ───────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description="网络优先爬虫 v2")
    ap.add_argument("--site", "-s", required=True, help="站点配置名")
    ap.add_argument("--url", help="起始 URL")
    ap.add_argument("--entry", help="入口名称")
    ap.add_argument("--deep", action="store_true", help="深度爬取")
    ap.add_argument("--deep-limit", type=int, default=0, help="每种类型最多深入几个")
    ap.add_argument("--wait", "-w", type=int, default=3, help="每页等待秒数")
    ap.add_argument("--max-pages", type=int, default=100, help="最大列表页数")
    ap.add_argument("--session", default="fast_crawl", help="browser-act 会话名")
    ap.add_argument("--browser-id", help="浏览器 ID（复用已有浏览器）")
    ap.add_argument("--output-dir", "-d", default=".", help="输出目录")
    ap.add_argument("--no-close", action="store_true", help="不关闭浏览器")

    args = ap.parse_args()

    site_config = load_site_config(args.site)
    print(f"[*] Site: {site_config.name} ({site_config.base_url})")

    start_url = args.url
    if not start_url and args.entry:
        for ep in site_config.entry_points:
            if ep.name == args.entry:
                start_url = ep.url
                break
    if not start_url and site_config.entry_points:
        ep = site_config.entry_points[0]
        start_url = ep.url
        print(f"[*] Using first entry: {ep.name}")

    print(f"[*] Start: {start_url}")
    print(f"[*] Max pages: {args.max_pages}, Wait: {args.wait}s")

    client = BrowserActClient(session=args.session, browser_id=args.browser_id)

    try:
        t0 = time.time()

        # Phase 1: 列表页
        pages, video_links = crawl_list_pages(
            client, start_url, site_config,
            max_pages=args.max_pages,
            wait_seconds=args.wait,
        )
        t1 = time.time()
        print(f"\n{'='*50}")
        print(f"  列表页: {len(pages)} 页, {len(video_links)} 个视频链接, {t1-t0:.1f}s")

        # 兼容旧导出
        compat_pages = []
        for p in pages:
            pl = PageLinks(page_url=p.page_url, page_title=p.page_title)
            pl.video_links = p.video_links
            pl.art_links = p.art_links
            pl.image_links = [{"text": "(img)", "url": u} for u in p.image_urls]
            pl.total_links = len(p.video_links) + len(p.art_links) + len(p.image_urls)
            compat_pages.append(pl)

        # Phase 2: 深度爬取
        video_results = []
        art_results = []
        deep_data = {}

        if args.deep and pages:
            if video_links:
                print(f"\n{'='*50}")
                print(f"  深度爬取视频: {len(video_links[:args.deep_limit or len(video_links)])} 个")
                video_results = crawl_video_streams(
                    client, video_links, site_config,
                    deep_limit=args.deep_limit,
                    wait_seconds=args.wait,
                )
                deep_data["video"] = [
                    {
                        "title": r.title,
                        "list_url": r.list_url,
                        "detail_url": r.detail_url,
                        "stream_url": r.stream_url,
                        "stream_format": r.stream_format,
                        "player_iframe": r.player_iframe,
                    }
                    for r in video_results
                ]

            all_art_links = []
            seen = set()
            for p in pages:
                for l in p.art_links:
                    if l["url"] not in seen:
                        all_art_links.append(l)
                        seen.add(l["url"])
            if all_art_links:
                art_results = crawl_art_images(
                    client, all_art_links,
                    deep_limit=args.deep_limit,
                    wait_seconds=args.wait,
                )
                deep_data["art"] = [
                    {
                        "title": r.title,
                        "detail_url": r.detail_url,
                        "images": r.images,
                        "image_count": len(r.images),
                    }
                    for r in art_results
                ]

        # 导出
        if compat_pages:
            exporter = JSONExporter()
            output_path = exporter.save(
                compat_pages, start_url, args.output_dir,
                deep_results=deep_data if deep_data else None,
            )
            JSONExporter.print_summary(compat_pages, output_path)

            if video_results:
                got = sum(1 for r in video_results if r.stream_url)
                print(f"\n  🎬 视频: {len(video_results)} 爬取, {got} 获取到流地址")
            if art_results:
                total_imgs = sum(len(r.images) for r in art_results)
                print(f"  🖼️ 图片: {len(art_results)} 详情页, {total_imgs} 张图片")

            print(f"\n  总耗时: {time.time()-t0:.1f}s")
            print(f"  结果: {output_path}")

    finally:
        if not args.no_close:
            try:
                client.close_session()
            except Exception:
                pass


if __name__ == "__main__":
    main()
