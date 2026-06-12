"""分组爬虫 — CLI 入口，委托 CrawlEngine 执行链式操作路径爬取。

用法（CLI）:
    python -m crawler.group_crawler --site www_mimimi_top
    python -m crawler.group_crawler --site www_mimimi_top --group 视频 --deep-limit 3

SSE 事件格式（与 site_manager.py 兼容）:
    [EVENT] {"event": "session_init", "url": "..."}
    [EVENT] {"event": "session_ready", "title": "..."}
    [EVENT] {"event": "crawl_done", "site": "...", "output": "output/..."}
"""

import sys
import os
import json
import argparse

# 确保 crawler 包可被导入（subprocess 调用时 sys.path 可能不含项目根目录）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from crawler.browser_act import BrowserActClient
from crawler.site_config import SiteConfig, load_site_config
from crawler.exporter import JSONExporter
from crawler.logger import get_logger

# ── Windows 控制台 GBK 编码兜底 ─────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (OSError, AttributeError):
        pass

_logger = get_logger("group_crawler")


# ── 工具函数 ─────────────────────────────────────────────

def _log(msg: str, ltype: str = "") -> None:
    """打印日志并写入日志文件。同时写 SSE 管道（stdout）。"""
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
    _safe_print(f"{prefix}{msg}")


def _emit(event_type: str, **kwargs) -> None:
    """输出结构化事件，site_manager SSE 端可解析。"""
    payload = json.dumps({"event": event_type, **kwargs}, ensure_ascii=False)
    _logger.info("[EVENT] %s %s", event_type, json.dumps(kwargs, ensure_ascii=False)[:200])
    _safe_print(f"[EVENT] {payload}")


def _safe_print(text: str) -> None:
    """编码安全的打印：优先 UTF-8 字节写入，Windows GBK 控制台兜底。"""
    try:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        try:
            print(text, flush=True)
        except UnicodeEncodeError:
            print(text.encode("gbk", errors="replace").decode("gbk"), flush=True)


# ── 引擎模式 ────────────────────────────────────────────

def _crawl_with_engine(
    site_config: SiteConfig,
    group_name: str = "",
    deep_limit: int = 0,
    wait_seconds: int = 4,
    max_pages: int = 50,
    output_dir: str = ".",
    session: str = "group_crawl",
    browser_id: str = "",
) -> str:
    """使用 CrawlEngine 爬取站点。"""
    from crawler.engine import CrawlEngine

    client = BrowserActClient(session=session, browser_id=browser_id)

    # 初始化浏览器会话
    first_url = ""
    for g in site_config.groups:
        if g.entry_points:
            first_url = g.entry_points[0].url
            break

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

    engine = CrawlEngine(client, site_config)
    results = engine.crawl_site(
        mode="bfs",
        deep_limit=deep_limit,
        wait_seconds=wait_seconds,
        max_pages=max_pages,
        group_name=group_name or "",
    )

    # 导出结果
    if results:
        exporter = JSONExporter()
        os.makedirs(output_dir, exist_ok=True)

        deep_data = {}
        for r in results:
            if r.stream_url:
                deep_data.setdefault("video", []).append({
                    "title": r.title,
                    "detail_url": r.detail_url,
                    "stream_url": r.stream_url,
                    "stream_format": r.stream_format,
                })
            elif r.images:
                deep_data.setdefault("art", []).append({
                    "title": r.title,
                    "detail_url": r.detail_url,
                    "images": r.images,
                    "image_count": len(r.images),
                })

        output_path = exporter.save(
            [],
            site_config.base_url,
            output_dir,
            deep_results=deep_data if deep_data else None,
        )
        _log(f"\n导出: {output_path}", "ok")
        _emit("crawl_done", site=site_config.name, output=output_path, total=len(results))
        return output_path
    else:
        _log("无数据", "err")
        _emit("crawl_done", site=site_config.name, output="", total=0)
        return ""


# ── 分组爬取核心 ─────────────────────────────────────────

def crawl_site_by_groups(
    site_config: SiteConfig,
    group_name: str = "",
    deep_limit: int = 0,
    wait_seconds: int = 4,
    max_pages: int = 50,
    output_dir: str = ".",
    session: str = "group_crawl",
    browser_id: str = "",
) -> str:
    """按分组配置爬取站点，返回输出文件路径。

    使用 CrawlEngine（链式操作路径驱动）执行爬取。
    每个分组必须有 crawl_pattern，否则报错。
    """
    groups_to_check = [g for g in site_config.groups
                       if (not group_name) or g.name == group_name]
    missing_pattern = [g.name for g in groups_to_check if not g.crawl_pattern]
    if missing_pattern:
        _log(f"分组 {missing_pattern} 缺少 crawl_pattern，无法爬取", "err")
        _emit("error", message=f"分组 {missing_pattern} 缺少 crawl_pattern")
        return ""

    return _crawl_with_engine(
        site_config, group_name, deep_limit, wait_seconds,
        max_pages, output_dir, session, browser_id,
    )


# ── CLI 入口 ────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="分组爬虫 — 链式操作路径驱动爬取")
    ap.add_argument("--site", "-s", required=True, help="站点配置名（sites.json 中的 key）")
    ap.add_argument("--group", help="指定分组名（空=所有分组）")
    ap.add_argument("--deep-limit", type=int, default=0, help="每种类型最多深入几个，0=全部")
    ap.add_argument("--wait", "-w", type=int, default=4, help="每页等待秒数")
    ap.add_argument("--max-pages", type=int, default=50, help="每个入口最多翻页数")
    ap.add_argument("--session", default="group_crawl", help="browser-act 会话名")
    ap.add_argument("--browser-id", help="复用已有浏览器 ID")
    ap.add_argument("--output-dir", "-d", default="output", help="输出目录")

    args = ap.parse_args()

    site_config = load_site_config(args.site)
    _logger.info("CLI启动: site=%s (%s), groups=%s, wait=%ds, max_pages=%d",
                 site_config.name, site_config.base_url,
                 [g.name for g in site_config.groups], args.wait, args.max_pages)

    output = crawl_site_by_groups(
        site_config,
        group_name=args.group or "",
        deep_limit=args.deep_limit,
        wait_seconds=args.wait,
        max_pages=args.max_pages,
        output_dir=args.output_dir,
        session=args.session,
        browser_id=args.browser_id,
    )

    if output:
        _logger.info("爬取完成: output=%s", output)


if __name__ == "__main__":
    main()
