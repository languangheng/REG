"""引擎 CLI 入口 — 支持 BFS/DFS 双模式

用法:
    python -m crawler.engine_cli --site www_mimimi_top              # BFS 完整爬取
    python -m crawler.engine_cli --site www_mimimi_top --mode dfs   # DFS 快速验证
    python -m crawler.engine_cli --site www_mimimi_top --mode bfs --deep-limit 5  # 每链5个

SSE 事件格式（与 site_manager.py 兼容）:
    [EVENT] {"event": "crawl_start", "site": "...", "mode": "dfs"}
    [EVENT] {"event": "group_start", "group": "...", "mode": "dfs"}
    [EVENT] {"event": "resource_found", "type": "stream", "url": "..."}
    [EVENT] {"event": "crawl_done", "site": "...", "mode": "dfs", "success": true}
"""

import sys
import os
import argparse

# 确保 crawler 包可被导入
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from crawler.engine import CrawlEngine, CrawlResult
from crawler.browser_act import BrowserActClient
from crawler.site_config import load_site_config
from crawler.exporter import JSONExporter

# ── Windows 控制台 GBK 编码兜底 ─────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (OSError, AttributeError):
        pass

def main():
    ap = argparse.ArgumentParser(description="引擎 CLI — 链式操作路径驱动爬取")
    ap.add_argument("--site", "-s", required=True, help="站点配置名（sites.json 中的 key）")
    ap.add_argument("--group", help="指定分组名（空=所有分组）")
    ap.add_argument("--mode", choices=["bfs", "dfs"], default="bfs",
                    help="爬取模式: bfs=完整爬取, dfs=快速验证（3-4页面出结果）")
    ap.add_argument("--deep-limit", type=int, default=0,
                    help="每条链取几个链接，0=不限（bfs默认0, dfs默认1）")
    ap.add_argument("--wait", "-w", type=int, default=4, help="每页等待秒数")
    ap.add_argument("--max-pages", type=int, default=50, help="每个入口最多翻页数")
    ap.add_argument("--session", default="engine_crawl", help="browser-act 会话名")
    ap.add_argument("--browser-id", help="复用已有浏览器 ID")
    ap.add_argument("--output-dir", "-d", default="output", help="输出目录")

    args = ap.parse_args()

    site_config = load_site_config(args.site)

    # 初始化浏览器会话
    first_url = ""
    for g in site_config.groups:
        if g.entry_points:
            first_url = g.entry_points[0].url
            break

    client = BrowserActClient(session=args.session, browser_id=args.browser_id)

    # 初始化浏览器
    if first_url:
        from crawler.engine import _log_msg, _emit
        _log_msg(f"初始化浏览器会话: {first_url}")
        _emit("session_init", url=first_url)
        try:
            client.ensure_session(first_url, max_wait_cf=90)
            _log_msg(f"会话就绪: {client.parsed_state().title[:50]}", "ok")
            _emit("session_ready", title=client.parsed_state().title)
        except RuntimeError as e:
            _log_msg(f"会话初始化失败: {e}", "err")
            _emit("session_error", error=str(e))
            return

    # 创建引擎
    engine = CrawlEngine(client, site_config)

    # 执行爬取
    mode = args.mode
    deep_limit = args.deep_limit if args.deep_limit > 0 else (1 if mode == "dfs" else 0)
    max_pages = 1 if mode == "dfs" else args.max_pages

    results = engine.crawl_site(
        mode=mode,
        deep_limit=deep_limit,
        wait_seconds=args.wait,
        max_pages=max_pages,
        group_name=args.group or "",
    )

    # 导出结果
    if results:
        exporter = JSONExporter()
        os.makedirs(args.output_dir, exist_ok=True)

        # 构建导出数据
        deep_data = {}
        for r in results:
            group_key = "video" if r.stream_url else "art" if r.images else "links"
            deep_data.setdefault(group_key, []).append({
                "title": r.title,
                "detail_url": r.detail_url,
                "stream_url": r.stream_url,
                "stream_format": r.stream_format,
                "images": r.images,
            })

        output_path = exporter.save(
            [],  # 空的 pages（引擎不产生 ListPageResult）
            site_config.base_url,
            args.output_dir,
            deep_results=deep_data if deep_data else None,
        )

        from crawler.engine import _log_msg
        _log_msg(f"\n导出: {output_path}", "ok")

        # DFS 模式特别标记验证成功/失败
        has_streams = any(r.stream_url for r in results)
        from crawler.engine import _emit
        _emit("crawl_done",
              site=site_config.name,
              output=output_path,
              mode=mode,
              total=len(results),
              streams=sum(1 for r in results if r.stream_url),
              success=has_streams if mode == "dfs" else True,
              duration=0)
    else:
        from crawler.engine import _log_msg, _emit
        _log_msg("无数据", "err")
        _emit("crawl_done", site=site_config.name, output="", mode=mode, total=0, success=False)


if __name__ == "__main__":
    main()