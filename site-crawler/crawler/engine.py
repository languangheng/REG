"""通用爬取引擎 — 链式操作路径驱动，支持 BFS/DFS 双模式

核心设计：
  - 读取 sites.json 中的 crawl_pattern，按链式步骤执行
  - 链按定义顺序执行，链之间数据流自动串联
  - BFS 模式：每条链处理所有链接（完整爬取）
  - DFS 模式：每条链只取 1 个链接直到底（快速验证，3-4 页面出结果）

用法:
    from crawler.engine import CrawlEngine
    from crawler.browser_act import BrowserActClient
    from crawler.site_config import load_site_config

    client = BrowserActClient(session="crawl", browser_id="...")
    config = load_site_config("www_mimimi_top")
    engine = CrawlEngine(client, config)
    results = engine.crawl_site(mode="dfs")
"""

import sys
import os
import re
import time
import json
from dataclasses import dataclass, field
from typing import Optional, Any
from urllib.parse import urlparse, urljoin

# 确保 crawler 包可被导入
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from crawler.browser_act import BrowserActClient, StateSnapshot, StateElement
from crawler.site_config import (
    SiteConfig, GroupConfig, CrawlPattern, CrawlChain, CrawlAction,
    LinkPatterns, EntryPoint, PaginationInChain,
)
from crawler.logger import get_logger

# ── Windows 控制台 GBK 编码兜底 ─────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (OSError, AttributeError):
        pass

_log = get_logger("engine")


# ── 数据结构 ─────────────────────────────────────────────

@dataclass
class CrawlResult:
    """单条爬取结果。"""
    title: str = ""
    detail_url: str = ""
    stream_url: str = ""
    stream_format: str = ""
    images: list[str] = field(default_factory=list)
    steps_log: list[str] = field(default_factory=list)


@dataclass
class ChainResult:
    """一条链的执行结果。"""
    chain_name: str = ""
    links: list[dict] = field(default_factory=list)   # extract_links 的输出
    streams: list[str] = field(default_factory=list)   # network_capture 的输出
    images: list[str] = field(default_factory=list)    # extract_images 的输出
    js_results: dict = field(default_factory=dict)     # evaluate_js 的输出


# ── 工具函数 ─────────────────────────────────────────────

def _log_msg(msg: str, ltype: str = "") -> None:
    """打印日志到 SSE 管道（stdout）+ 日志文件。"""
    prefix = ""
    if ltype == "ok":
        prefix = "✅ "
        _log.info("%s", msg)
    elif ltype == "err":
        prefix = "❌ "
        _log.error("%s", msg)
    elif ltype == "warn":
        prefix = "⚠️ "
        _log.warning("%s", msg)
    else:
        _log.info("%s", msg)
    _safe_print(f"{prefix}{msg}")


def _emit(event_type: str, **kwargs) -> None:
    """输出结构化 SSE 事件。"""
    payload = json.dumps({"event": event_type, **kwargs}, ensure_ascii=False)
    _log.info("[EVENT] %s %s", event_type, json.dumps(kwargs, ensure_ascii=False)[:200])
    _safe_print(f"[EVENT] {payload}")


def _safe_print(text: str) -> None:
    """编码安全的打印。"""
    try:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        try:
            print(text, flush=True)
        except UnicodeEncodeError:
            print(text.encode("gbk", errors="replace").decode("gbk"), flush=True)


def _smart_wait(client: BrowserActClient, selector: str, timeout: int = 5000, state: str = "attached"):
    """智能等待：先 wait_selector，超时则 time.sleep 兜底。"""
    try:
        client.wait_selector(selector, state=state, timeout=timeout)
        time.sleep(1)  # 等元素渲染完
    except Exception:
        time.sleep(timeout // 1000)


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


def classify_links_by_patterns(
    links: list[dict],
    link_patterns: LinkPatterns,
) -> dict[str, list[dict]]:
    """按 link_patterns 分类链接，返回 {link_type: [links]}。

    支持任意 link_type（video_detail, play_page 等），
    遍历 patterns 中所有 link_type 的正则进行匹配。
    """
    classified = {}

    for link in links:
        url = link["url"]
        path = urlparse(url).path

        # 排除
        if link_patterns.is_excluded(path):
            continue

        # 图片后缀特殊处理
        if any(path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            classified.setdefault("image", []).append(link)
            continue

        # 按 link_patterns 中定义的 link_type 逐个匹配
        matched_type = link_patterns.match(path)
        if matched_type:
            classified.setdefault(matched_type, []).append(link)
            continue

    return classified


# ── URL 构造 ─────────────────────────────────────────────

def _construct_next_page_url(cur_url: str, current_page: int) -> str:
    """基于当前 URL 模式构造下一页 URL（MacCMS + 通用格式）。"""
    next_page = current_page + 1

    # MacCMS 格式 A：已含页码
    m = re.match(r'^(https?://[^/]+/[^/]+/\d+)(-+)(\d+)(---)(\.html)$', cur_url)
    if m:
        prefix, dashes_before, page_str, tail, suffix = m.groups()
        new_dash_len = len(dashes_before) + len(page_str) - len(str(next_page))
        if new_dash_len >= 0:
            return f"{prefix}{'-' * new_dash_len}{next_page}{tail}{suffix}"
        return ""

    # MacCMS 格式 B：第1页纯 dash
    m = re.match(r'^(https?://[^/]+/[^/]+/\d+)(-+)(\.html)$', cur_url)
    if m:
        prefix, dashes, suffix = m.groups()
        dash_count = len(dashes)
        tail = "---"
        body_len = dash_count + 1 - len(tail) - len(str(next_page))
        if body_len >= 0:
            return f"{prefix}{'-' * body_len}{next_page}{tail}{suffix}"
        return ""

    # 通用格式 C: /category/X.html → /category/X-2.html
    m = re.match(r'^(.*?/\w+/\d+)\.html$', cur_url)
    if m and current_page == 1:
        return f"{m.group(1)}-{next_page}.html"
    m = re.match(r'^(.*?/\w+/\d+)-\d+\.html$', cur_url)
    if m:
        return f"{m.group(1)}-{next_page}.html"

    # 通用格式 D: ?page=N
    m = re.search(r'[?&]page=(\d+)', cur_url)
    if m:
        return cur_url.replace(f"page={m.group(1)}", f"page={next_page}")
    if 'page=' not in cur_url and '?' in cur_url:
        return f"{cur_url}&page={next_page}"
    if '?' not in cur_url:
        return f"{cur_url}?page={next_page}"

    # 通用格式 E: /page/N
    m = re.search(r'/page/(\d+)', cur_url)
    if m:
        return cur_url.replace(f"/page/{m.group(1)}", f"/page/{next_page}")

    return ""


# ── 通用引擎 ─────────────────────────────────────────────

class CrawlEngine:
    """通用爬取引擎 — 链式操作路径驱动。

    读取 sites.json 中的 crawl_pattern，按链式步骤执行。
    支持 BFS（完整爬取）和 DFS（快速验证）两种模式。
    """

    def __init__(self, client: BrowserActClient, site_config: SiteConfig):
        self.client = client
        self.config = site_config
        self.base_url = site_config.base_url
        self._js_vars: dict = {}  # evaluate_js 的 save_as 变量

    def crawl_site(
        self,
        mode: str = "bfs",
        deep_limit: int = 0,
        wait_seconds: int = 4,
        max_pages: int = 50,
        group_name: str = "",
    ) -> list[CrawlResult]:
        """爬取站点，返回结果列表。

        Args:
            mode: "bfs"（完整爬取）或 "dfs"（快速验证）
            deep_limit: 每条链取几个链接，0=不限
            wait_seconds: 默认等待秒数
            max_pages: 最大翻页数
            group_name: 指定分组名，空=所有分组
        """
        # 筛选分组
        if group_name:
            groups = [g for g in self.config.groups if g.name == group_name]
        else:
            groups = self.config.groups

        if not groups:
            _log_msg("站点无分组配置", "err")
            return []

        _emit("crawl_start",
              site=self.config.name,
              base_url=self.base_url,
              site_type=self.config.site_type,
              mode=mode,
              groups=len(groups))

        all_results = []

        for group in groups:
            results = self.crawl_group(
                group,
                mode=mode,
                deep_limit=deep_limit,
                wait_seconds=wait_seconds,
                max_pages=max_pages,
            )
            all_results.extend(results)

        _emit("crawl_done",
              site=self.config.name,
              mode=mode,
              total=len(all_results),
              streams=sum(1 for r in all_results if r.stream_url),
              success=any(r.stream_url for r in all_results))

        return all_results

    def crawl_group(
        self,
        group: GroupConfig,
        mode: str = "bfs",
        deep_limit: int = 0,
        wait_seconds: int = 4,
        max_pages: int = 50,
    ) -> list[CrawlResult]:
        """爬取一个分组。"""
        # 获取或推断 crawl_pattern
        pattern = self._get_crawl_pattern(group)
        if not pattern or not pattern.chain_order:
            _log_msg(f"分组 '{group.name}' 无链式操作路径", "err")
            return []

        # DFS 模式参数
        if mode == "dfs":
            per_chain_limit = 1
            effective_max_pages = 1
        elif deep_limit > 0:
            per_chain_limit = deep_limit
            effective_max_pages = min(max_pages, deep_limit)
        else:
            per_chain_limit = 0  # 不限
            effective_max_pages = max_pages

        _emit("group_start",
              group=group.name,
              resource_type=group.resource_type,
              mode=mode,
              chains=len(pattern.chain_order))

        _log_msg(f"\n{'=' * 50}")
        _log_msg(f"分组: {group.name} ({group.resource_type}) [{mode.upper()}]")

        # ── 执行链序列 ──
        accumulated_links: list[dict] = []

        for chain_idx, chain_name in enumerate(pattern.chain_order):
            chain = pattern.chains.get(chain_name)
            if not chain:
                continue

            is_first_chain = (chain_idx == 0)
            is_last_chain = (chain_idx == len(pattern.chain_order) - 1)

            _log_msg(f"\n── 链 [{chain_idx + 1}/{len(pattern.chain_order)}]: {chain_name}")

            if is_first_chain:
                # 第一条链：用 entry_points 作为起始 URL
                chain_results = self._execute_first_chain(
                    chain, group, pattern,
                    max_pages=effective_max_pages,
                    wait_seconds=wait_seconds,
                    per_chain_limit=per_chain_limit,
                )
                accumulated_links = chain_results.links

            else:
                # 后续链：用上一条链的输出作为输入
                chain_results = self._execute_deep_chain(
                    chain, group, pattern,
                    input_links=accumulated_links,
                    wait_seconds=wait_seconds,
                    per_chain_limit=per_chain_limit,
                )
                accumulated_links = chain_results.links

            # 如果是最后一条链（通常是 stream_capture），提取最终结果
            if is_last_chain or chain_results.streams or chain_results.images:
                return self._convert_to_crawl_results(
                    accumulated_links, chain_results, group,
                )

        # 如果链全部走完但没有最终结果，返回链接列表
        return self._links_to_crawl_results(accumulated_links, group)

    def _get_crawl_pattern(self, group: GroupConfig) -> Optional[CrawlPattern]:
        """获取分组的 crawl_pattern。"""
        return group.crawl_pattern

    def _execute_first_chain(
        self,
        chain: CrawlChain,
        group: GroupConfig,
        pattern: CrawlPattern,
        max_pages: int = 50,
        wait_seconds: int = 4,
        per_chain_limit: int = 0,
    ) -> ChainResult:
        """执行第一条链（通常是 list_crawl），遍历 entry_points + 翻页。"""
        all_links = []
        seen_urls = set()

        for ep in group.entry_points:
            url = ep.url
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)

            _log_msg(f"  入口: {ep.name} → {url[:80]}")
            _emit("entry_start", group=group.name, entry_name=ep.name, url=url)

            # 执行链步骤
            page_num = 1
            while page_num <= max_pages:
                # 执行当前页的步骤
                result = self._execute_chain_steps(chain, url=url, group=group, pattern=pattern)

                # 提取链接
                new_links = result.links
                new_count = 0
                for link in new_links:
                    if link["url"] not in seen_urls:
                        all_links.append(link)
                        seen_urls.add(link["url"])
                        new_count += 1

                _log_msg(f"  [Page {page_num}] {url[:60]} → {new_count} 新链接")

                # DFS 模式：只爬 1 页
                if max_pages <= 1:
                    break

                # 翻页
                next_url = self._try_pagination(chain, group, page_num, result)
                if not next_url or not next_url.startswith("http"):
                    break

                url = next_url
                page_num += 1

                # per_chain_limit 限制
                if per_chain_limit > 0 and len(all_links) >= per_chain_limit:
                    break

        # 应用 per_chain_limit
        if per_chain_limit > 0:
            all_links = all_links[:per_chain_limit]

        _emit("chain_done", group=group.name, chain=chain.name, links=len(all_links))
        return ChainResult(chain_name=chain.name, links=all_links)

    def _execute_deep_chain(
        self,
        chain: CrawlChain,
        group: GroupConfig,
        pattern: CrawlPattern,
        input_links: list[dict],
        wait_seconds: int = 4,
        per_chain_limit: int = 0,
    ) -> ChainResult:
        """执行后续链（detail_crawl / stream_capture 等），用上一条链的输出作为输入。"""
        all_links = []
        all_streams = []
        all_images = []
        total = len(input_links)

        for i, link in enumerate(input_links, 1):
            url = link.get("url", "")
            title = link.get("text", "")[:50]
            _log_msg(f"  [{i}/{total}] {title[:40]}")

            # 执行链步骤
            result = self._execute_chain_steps(chain, url=url, group=group, pattern=pattern)

            # 收集结果
            all_links.extend(result.links)
            all_streams.extend(result.streams)
            all_images.extend(result.images)

            # 如果抓到流地址，输出
            for stream_url in result.streams:
                fmt = "m3u8" if ".m3u8" in stream_url.lower() else "mp4"
                _log_msg(f"    ✅ stream: {stream_url[:80]}", "ok")
                _emit("resource_found", type="stream", url=stream_url, title=title, format=fmt)

            for img_url in result.images[:3]:
                _emit("resource_found", type="image", url=img_url, title=title)

        # 应用 per_chain_limit
        if per_chain_limit > 0:
            all_links = all_links[:per_chain_limit]

        _emit("chain_done",
              group=group.name,
              chain=chain.name,
              links=len(all_links),
              streams=len(all_streams),
              images=len(all_images))

        return ChainResult(
            chain_name=chain.name,
            links=all_links,
            streams=all_streams,
            images=all_images,
        )

    def _execute_chain_steps(
        self,
        chain: CrawlChain,
        url: str = "",
        group: GroupConfig = None,
        pattern: CrawlPattern = None,
    ) -> ChainResult:
        """执行一条链的所有步骤。

        任何步骤导致浏览器 session 丢失时，立即终止当前链并返回已有结果，
        避免后续步骤继续在无效 session 上操作产生连锁错误。
        """
        result = ChainResult(chain_name=chain.name)

        # 如果本链包含 network_capture 步骤，在导航前提前清空网络请求记录，
        # 确保 navigate 过程中产生的流请求（m3u8/mp4/flv）能被捕获到。
        chain_has_network_capture = any(s.action == "network_capture" for s in chain.steps)
        if chain_has_network_capture:
            try:
                self.client.network_clear()
                _log_msg("  network_clear (pre-navigate, chain contains network_capture)")
            except Exception:
                pass

        for step in chain.steps:
            action = step.action

            try:
                if action == "navigate":
                    target_url = self._resolve_url(step, url)
                    if target_url:
                        _log_msg(f"  navigate → {target_url[:80]}")
                        self.client.navigate(target_url)

                elif action == "smart_wait":
                    _smart_wait(
                        self.client,
                        step.selector,
                        timeout=step.timeout,
                        state=step.state,
                    )

                elif action == "extract_links":
                    md = self.client.get_markdown()
                    raw_links = extract_links_from_markdown(md, self.base_url)
                    # 用 link_patterns 分类
                    lp = group.link_patterns if group else LinkPatterns()
                    if not lp._compiled:
                        lp.compile()
                    classified = classify_links_by_patterns(raw_links, lp)

                    # 按指定的 link_type 提取
                    if step.link_type:
                        result.links = classified.get(step.link_type, [])
                    else:
                        # 没指定 link_type，取所有非排除链接
                        for lt, links in classified.items():
                            result.links.extend(links)

                elif action == "extract_images":
                    result.images = self.client.get_all_image_urls()

                elif action == "network_capture":
                    # network_clear 已在链开始前（navigate 之前）执行，
                    # 此处只需等待播放器加载并读取捕获结果
                    wait = step.wait_seconds or 5
                    _log_msg(f"  network_capture: 等待 {wait}s 后读取网络请求...")
                    time.sleep(wait)
                    result.streams = self._extract_stream_from_network(step.filter)
                    _log_msg(f"  network_capture: 捕获到 {len(result.streams)} 个流地址")

                elif action == "click":
                    self.client.click(step.index)

                elif action == "evaluate_js":
                    js_result = self.client.evaluate_json(step.script)
                    if step.save_as:
                        self._js_vars[step.save_as] = js_result
                        result.js_results[step.save_as] = js_result

                elif action == "scroll":
                    for _ in range(step.times):
                        if step.direction == "down":
                            self.client.scroll_down(500)
                        else:
                            self.client.scroll_top()
                        time.sleep(step.wait_after or 2)

                elif action == "wait":
                    time.sleep(step.seconds or 3)

            except Exception as e:
                err_msg = str(e)
                # 判断是否是 session 丢失级别的致命错误
                is_session_lost = any(keyword in err_msg.lower() for keyword in [
                    "no active session", "no active browser", "session not found",
                    "session不存在", "browser closed", "target closed",
                ])
                if is_session_lost:
                    _log_msg(f"  浏览器 session 丢失，终止链 '{chain.name}': {e}", "err")
                    # 立即终止当前链，不再执行后续步骤
                    break
                else:
                    # 非致命错误：记录但继续执行
                    _log_msg(f"  步骤 {action} 失败（非致命）: {e}", "warn")

        return result

    def _resolve_url(self, step: CrawlAction, fallback_url: str = "") -> str:
        """解析步骤的 URL 来源。

        优先级:
          1. url_from → 从 JS 变量取
          2. url_template → 填充 params 变量槽
             - 如果模板填充后仍有未替换的 {xxx} 占位符，说明变量来自上一条链的链接，
               此时应 fallback 到 fallback_url（上一条链传入的实际链接 URL）
          3. fallback_url → 直接使用上一条链的链接 URL
        """
        # 1. url_from: 从 JS 变量取
        if step.url_from and step.url_from in self._js_vars:
            return str(self._js_vars[step.url_from])

        # 2. url_template: 填充变量槽
        if step.url_template:
            url = step.url_template
            # 用 params 填充变量
            params = step.params or {}
            for key, val in params.items():
                url = url.replace(f"{{{key}}}", str(val))

            # 检查是否仍有未替换的占位符（如 {id}, {sid}, {eid}）
            remaining_placeholders = re.findall(r'\{(\w+)\}', url)
            if remaining_placeholders:
                # 模板中的占位符来自上一条链的链接数据，无法从 params 填充
                # 直接使用 fallback_url（上一条链传入的实际链接 URL）
                _log.debug("url_template 仍有未填充占位符 %s，fallback 到实际链接 URL: %s",
                           remaining_placeholders, fallback_url[:80] if fallback_url else "(空)")
                if fallback_url:
                    return fallback_url
                # fallback_url 也为空 → 补全 base_url 后返回模板（可能导航到无效 URL）
                if not url.startswith(('http://', 'https://')):
                    url = urljoin(self.base_url, url)
                return url

            # 全部占位符已填充 → 补全 base_url
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)
            return url

        # 3. fallback
        return fallback_url

    def _try_pagination(
        self,
        chain: CrawlChain,
        group: GroupConfig,
        current_page: int,
        chain_result: ChainResult,
    ) -> str:
        """翻页 — 三级回退（性能优先）。

        Tier 1: url_construct  → 纯字符串拼接，零 DOM 交互（~0ms）
        Tier 2: click + URL 检测 → 点击后立即读地址栏（~300ms）
        Tier 3: click + 内容等待 → 点击后 smart_wait 确认页面就绪（~2s）

        返回下一页 URL，空字符串表示无更多页面。
        不再返回魔法字符串（如 "clicked"），调用方直接用返回值做 URL。
        """
        if not chain.pagination:
            return ""

        methods = chain.pagination.methods or []

        # ── Tier 1: URL 构造（最快，零 DOM） ──
        if "url_construct" in methods:
            try:
                snap = self.client.parsed_state()
                cur_url = snap.url
            except Exception:
                cur_url = ""
            if cur_url:
                next_url = _construct_next_page_url(cur_url, current_page)
                if next_url:
                    _log_msg(f"  → 翻页URL(构造): {next_url[:80]} [Tier 1]")
                    return next_url

        # ── Tier 2 & 3: 点击翻页 ──
        if "button_click" in methods:
            try:
                snap = self.client.parsed_state()
                old_url = snap.url
                next_el = snap.find_next_page(current_page)
                if not next_el:
                    return ""

                self.client.click(next_el.index)
                _log_msg(f"  → 翻页(点击): [{next_el.index}] {next_el.text!r}")

                # ── Tier 2: URL 变化检测（快速路径，传统翻页） ──
                time.sleep(0.5)
                try:
                    new_snap = self.client.parsed_state()
                    if new_snap.url and new_snap.url != old_url:
                        _log_msg(f"  → URL已变化: {new_snap.url[:80]} [Tier 2]")
                        return new_snap.url
                except Exception:
                    pass

                # ── Tier 3: 内容等待（稳健路径，AJAX 翻页） ──
                # 从链步骤中提取 smart_wait selector，复用站点配置的准确选择器
                wait_selector = ""
                for step in chain.steps:
                    if step.action == "smart_wait" and step.selector:
                        wait_selector = step.selector
                        break
                if wait_selector:
                    _smart_wait(self.client, wait_selector)
                    _log_msg(f"  → 内容等待完成 [Tier 3]")
                else:
                    time.sleep(2)

                try:
                    new_snap = self.client.parsed_state()
                    return new_snap.url or ""
                except Exception:
                    return ""

            except Exception as e:
                _log_msg(f"  翻页点击失败: {e}", "warn")

        return ""

    def _extract_stream_from_network(self, filter_str: str = "") -> list[str]:
        """从 network_requests 中提取流地址。

        策略：
          1. 一次性获取所有网络请求（不传 filter，避免遗漏）
          2. 按 XHR/Fetch 优先顺序筛选包含流扩展名的 URL
          3. filter_str 用于额外过滤（如只要 .m3u8），为空则接受所有流格式
        """
        stream_exts = [".m3u8", ".mp4", ".flv"]
        # 已知跳转代理域名 / 非真实流地址模式
        _redirect_denylist = ["aojiexi.com", "jx.618g.com", "jx.m3u8.tv"]
        streams = []

        # 一次性拉取所有请求，不在 browser_act 层过滤（避免多轮调用）
        all_reqs = self.client.network_requests()

        def _is_redirect_proxy(url: str) -> bool:
            """检测是否为跳转代理/解析接口（非真实流地址）。"""
            u = url.lower()
            for domain in _redirect_denylist:
                if domain in u:
                    return True
            # ?url= 参数模式（常见跳转代理格式）
            if "?url=" in u and not any(u.endswith(ext) or f"{ext}?" in u for ext in stream_exts):
                return True
            return False

        def _is_stream_url(url: str) -> bool:
            u = url.lower()
            if _is_redirect_proxy(url):
                return False
            if filter_str:
                # filter_str 形如 ".m3u8,.mp4,.flv"
                return any(f.strip() in u for f in filter_str.split(","))
            return any(ext in u for ext in stream_exts)

        # 优先：XHR/Fetch
        for r in all_reqs:
            if r.get("resource_type") in ("XHR", "Fetch"):
                url = r.get("url", "")
                if _is_stream_url(url) and url not in streams:
                    streams.append(url)

        # 次优先：其他类型（媒体资源、脚本内嵌请求等）
        for r in all_reqs:
            url = r.get("url", "")
            if _is_stream_url(url) and url not in streams and "player.js" not in url.lower():
                streams.append(url)

        return streams

    def _convert_to_crawl_results(
        self,
        links: list[dict],
        chain_result: ChainResult,
        group: GroupConfig,
    ) -> list[CrawlResult]:
        """将链执行结果转换为 CrawlResult 列表。"""
        results = []

        if chain_result.streams:
            # 有流地址 → 每个流地址一条结果
            for i, stream_url in enumerate(chain_result.streams):
                title = links[i].get("text", "")[:50] if i < len(links) else f"stream_{i}"
                detail_url = links[i].get("url", "") if i < len(links) else ""
                results.append(CrawlResult(
                    title=title,
                    detail_url=detail_url,
                    stream_url=stream_url,
                    stream_format="m3u8" if ".m3u8" in stream_url.lower() else "mp4",
                ))
        elif chain_result.images:
            # 有图片 → 合并为一条结果
            results.append(CrawlResult(
                images=chain_result.images,
            ))
        else:
            # 无流/图 → 返回链接列表
            for link in links:
                results.append(CrawlResult(
                    title=link.get("text", "")[:50],
                    detail_url=link.get("url", ""),
                ))

        return results

    def _links_to_crawl_results(
        self,
        links: list[dict],
        group: GroupConfig,
    ) -> list[CrawlResult]:
        """将链接列表转换为 CrawlResult 列表。"""
        return [
            CrawlResult(title=link.get("text", "")[:50], detail_url=link.get("url", ""))
            for link in links
        ]
