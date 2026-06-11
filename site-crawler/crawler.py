"""Site Crawler - 配置驱动的通用网站资源爬虫

用法:
    python crawler.py --site mimimi
    python crawler.py --site mimimi --deep --deep-limit 3
    python crawler.py --site mimimi --entry "电影"
    python crawler.py --url "https://www.mimimi.top/vodshow/12-----------.html" --site mimimi
"""

import argparse
import sys
import io
import json
import os


def _emit(event_type: str, **kwargs):
    """输出结构化事件，SSE 端可解析为实时进度数据。"""
    payload = json.dumps({"event": event_type, **kwargs}, ensure_ascii=False)
    print(f"[EVENT] {payload}", flush=True)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient
from crawler.parser import PageParser
from crawler.exporter import JSONExporter
from crawler.site_config import load_site_config, list_available_sites


def crawl_list_pages(
    client: BrowserActClient,
    start_url: str,
    site_config=None,
    wait_seconds: int = 8,
    max_pages: int = 100,
) -> list:
    """从起始 URL 逐页爬取列表，提取链接。"""
    pages = []
    current_url = start_url

    try:
        for page_num in range(1, max_pages + 1):
            print(f"\n[Page {page_num}] {current_url}")
            _emit("page_start", page=page_num, url=current_url)
            client.navigate(current_url)
            client.wait(wait_seconds)

            markdown = client.get_markdown()
            extra_imgs = client.get_all_image_urls()

            parser = PageParser(base_url=current_url, site_config=site_config)
            page_result = parser.parse(markdown, extra_image_urls=extra_imgs)
            pages.append(page_result)

            print(f"  images={len(page_result.image_links)}, videos={len(page_result.video_links)}, arts={len(page_result.art_links)}")
            _emit("page_result", page=page_num,
                  images=len(page_result.image_links),
                  videos=len(page_result.video_links),
                  arts=len(page_result.art_links))

            next_url = parser.find_next_page_url(markdown, current_url)
            if not next_url or next_url == current_url:
                print("  No more pages.")
                break
            current_url = next_url
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except Exception as e:
        print(f"\n  Error: {e}")

    return pages


def crawl_deep(
    client: BrowserActClient,
    pages: list,
    site_config,
    wait_seconds: int = 6,
    deep_limit: int = 0,
) -> dict:
    """按 extract_chains 配置深度爬取详情页。

    Args:
        deep_limit: 每种类型最多深入几个，0=全部
    Returns:
        {"video": [...], "art": [...]}
    """
    results = {}

    # 收集去重的详情链接
    for chain_name, chain in site_config.extract_chains.items():
        # 从列表页结果中收集该类型的链接
        detail_links = []
        seen = set()

        for page in pages:
            # 根据链名匹配链接列表
            if chain_name == "video":
                source_links = page.video_links
            elif chain_name == "art":
                source_links = page.art_links
            else:
                continue

            for link in source_links:
                if link["url"] not in seen:
                    detail_links.append(link)
                    seen.add(link["url"])

        if not detail_links:
            print(f"\n  [{chain_name}] No detail links found.")
            results[chain_name] = []
            continue

        # 限制数量
        if deep_limit > 0:
            detail_links = detail_links[:deep_limit]

        total = len(detail_links)
        print(f"\n{'='*50}")
        print(f"  [{chain_name}] Deep crawling {total} items ({len(chain.steps)} steps each)")
        print(f"{'='*50}")
        _emit("deep_start", chain=chain_name, total=total, steps=len(chain.steps))

        chain_results = []
        for i, link in enumerate(detail_links, 1):
            title = link.get("text", "")[:50]
            url = link["url"]
            print(f"\n  [{i}/{total}] {title}")
            _emit("detail_start", chain=chain_name, index=i, total=total, title=title, url=url)

            item = {"title": title, "list_url": url, "steps": {}}

            # 逐步执行提取链
            current_url = url
            for step in chain.steps:
                try:
                    client.navigate(current_url)
                    client.wait(wait_seconds)
                    step_result = client.execute_step(step)
                    item["steps"][step.name] = step_result

                    # 如果结果是链接列表，第一个链接作为下一步的 URL
                    if isinstance(step_result, list) and step_result:
                        first = step_result[0]
                        if isinstance(first, dict) and "href" in first:
                            current_url = first["href"]

                    # 简要输出
                    if isinstance(step_result, dict):
                        stream = step_result.get("stream_url") or step_result.get("url")
                        if stream:
                            print(f"    {step.name}: stream={stream[:80]}")
                            _emit("resource_found", type="stream", url=stream[:120],
                                  chain=chain_name, index=i, title=title)
                        else:
                            print(f"    {step.name}: {str(step_result)[:100]}")
                    elif isinstance(step_result, list):
                        print(f"    {step.name}: {len(step_result)} items")
                        if step_result:
                            _emit("step_result", chain=chain_name, step=step.name,
                                  result_type="items", count=len(step_result),
                                  index=i, title=title)
                    else:
                        print(f"    {step.name}: {str(step_result)[:80]}")

                except Exception as e:
                    print(f"    {step.name}: FAILED - {e}")
                    item["steps"][step.name] = {"error": str(e)}

            # 提取关键信息到顶层
            _flatten_result(item, chain)
            chain_results.append(item)

        results[chain_name] = chain_results

    return results


def _flatten_result(item: dict, chain):
    """将 steps 中的关键信息提升到 item 顶层，方便查看。"""
    for step_name, step_data in item.get("steps", {}).items():
        if isinstance(step_data, dict):
            # video 链：提取 stream_url
            if "stream_url" in step_data:
                item["stream_url"] = step_data["stream_url"]
            if "player_iframe" in step_data:
                item["player_iframe"] = step_data["player_iframe"]
        elif isinstance(step_data, list) and step_data:
            # 提取播放链接数量
            item[f"{step_name}_count"] = len(step_data)
            # 图片链：直接存储图片列表
            if all(isinstance(x, str) for x in step_data):
                item["images"] = step_data
                item["image_count"] = len(step_data)


def main():
    ap = argparse.ArgumentParser(description="配置驱动的通用网站爬虫")
    ap.add_argument("--site", "-s", required=True, help="站点配置名（对应 sites.yaml 中的 key）")
    ap.add_argument("--url", help="起始 URL（覆盖 entry_points）")
    ap.add_argument("--entry", help="入口名称（如 '电影'，匹配 entry_points 中的 name）")
    ap.add_argument("--deep", action="store_true", help="深度爬取详情页")
    ap.add_argument("--deep-limit", type=int, default=0, help="每种类型最多深入几个（0=全部）")
    ap.add_argument("--wait", "-w", type=int, default=8, help="每页等待秒数")
    ap.add_argument("--detail-wait", type=int, default=6, help="详情页等待秒数")
    ap.add_argument("--max-pages", type=int, default=100, help="最大列表页数")
    ap.add_argument("--session", default="crawl", help="browser-act 会话名")
    ap.add_argument("--output-dir", "-d", default=".", help="输出目录")
    ap.add_argument("--no-close", action="store_true", help="不关闭浏览器")

    args = ap.parse_args()

    # 加载站点配置
    site_config = load_site_config(args.site)
    print(f"[*] Site: {site_config.name} ({site_config.base_url})")

    # 确定起始 URL
    start_url = args.url
    if not start_url and args.entry:
        for ep in site_config.entry_points:
            if ep.name == args.entry:
                start_url = ep.url
                break
        if not start_url:
            available = [ep.name for ep in site_config.entry_points]
            print(f"Entry '{args.entry}' not found. Available: {available}")
            return
    if not start_url:
        # 使用第一个入口
        if site_config.entry_points:
            ep = site_config.entry_points[0]
            start_url = ep.url
            print(f"[*] Using first entry: {ep.name} -> {start_url}")
        else:
            print("No URL specified and no entry_points defined.")
            return

    print(f"[*] Start: {start_url}")
    print(f"[*] Max pages: {args.max_pages}")
    _emit("crawl_start", site=args.site, base_url=site_config.base_url, start_url=start_url, deep=args.deep)

    client = BrowserActClient(session=args.session, browser_id=None)

    try:
        # 列表页爬取
        pages = crawl_list_pages(
            client, start_url, site_config,
            wait_seconds=args.wait,
            max_pages=args.max_pages,
        )

        # 深度爬取
        deep_results = {}
        if args.deep and pages:
            deep_results = crawl_deep(
                client, pages, site_config,
                wait_seconds=args.detail_wait,
                deep_limit=args.deep_limit,
            )

        # 导出
        if pages:
            exporter = JSONExporter()
            output_path = exporter.save(
                pages, start_url, args.output_dir,
                deep_results=deep_results,
            )
            JSONExporter.print_summary(pages, output_path)

            # 深度结果摘要
            for chain_name, items in deep_results.items():
                if chain_name == "video":
                    streams = [i for i in items if i.get("stream_url")]
                    print(f"\n  [{chain_name}] {len(items)} crawled, {len(streams)} got stream URL")
                    _emit("chain_done", chain=chain_name, crawled=len(items), streams=len(streams))
                elif chain_name == "art":
                    total_imgs = sum(len(i.get("images", [])) for i in items)
                    print(f"\n  [{chain_name}] {len(items)} crawled, {total_imgs} images")
                    _emit("chain_done", chain=chain_name, crawled=len(items), images=total_imgs)
                else:
                    print(f"\n  [{chain_name}] {len(items)} crawled")
                    _emit("chain_done", chain=chain_name, crawled=len(items))

            print(f"\n  Results saved to {output_path}")
            _emit("crawl_done", output=output_path)
    finally:
        if not args.no_close:
            try:
                client.close_session()
            except Exception:
                pass


if __name__ == "__main__":
    main()
