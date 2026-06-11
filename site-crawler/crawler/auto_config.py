"""方案 A：一键自动配置生成器

输入: 列表页 URL
输出: sites.yaml 配置片段

流程:
  1. 打开列表页 → 等 CF
  2. markdown 提取链接 → 按路径模式聚类 → 自动识别详情页链接组
  3. 进入第一个详情页 → 找播放器 → 点击 → 抓 m3u8
  4. 分析翻页结构
  5. 输出完整配置
"""

import re
import time
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse
from typing import Optional

from crawler.browser_act import BrowserActClient


class _CallbackList:
    """支持回调的列表，替代 monkey-patch list.append。"""
    def __init__(self, items=None, callback=None):
        self._items = list(items) if items else []
        self._callback = callback

    def append(self, item):
        self._items.append(item)
        if self._callback:
            try:
                self._callback(item)
            except Exception:
                pass  # 回调失败不影响主流程

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __repr__(self):
        return repr(self._items)


@dataclass
class AutoConfigResult:
    """自动配置结果。"""
    success: bool = False
    config: dict = field(default_factory=dict)
    log: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _path_pattern(url: str) -> str:
    """将 URL 路径转为模式：数字段替换为 {id}。"""
    parsed = urlparse(url)
    path = parsed.path
    parts = list(path.split("/"))
    new_parts = []
    for p in parts:
        if not p:
            new_parts.append(p)
            continue
        # 处理 "123.html" 这种格式：拆成 "123" + ".html"
        base_name = p
        ext = ""
        if "." in p:
            base_name, ext = p.rsplit(".", 1)
            ext = "." + ext
        # 检查 base_name 是否是纯数字或十六进制
        if re.match(r"^\d+$", base_name):
            new_parts.append("{id}" + ext)
        elif re.match(r"^[a-f0-9]{8,}$", base_name, re.IGNORECASE):
            new_parts.append("{id}" + ext)
        else:
            new_parts.append(p)
    return "/".join(new_parts)


def _cluster_links(links: list[dict], base_url: str) -> list[dict]:
    """将链接按路径模式聚类，返回 [{pattern, count, links}]。"""
    base_netloc = urlparse(base_url).netloc
    internal = [
        l for l in links
        if (urlparse(l["url"]).netloc == base_netloc or not urlparse(l["url"]).netloc)
        and urlparse(l["url"]).path not in ("", "/")
    ]

    # 聚类
    groups = {}  # pattern -> [links]
    for l in internal:
        pat = _path_pattern(l["url"])
        if pat not in groups:
            groups[pat] = []
        groups[pat].append(l)

    # 排序：含 {id} 的优先，数量多的优先
    results = []
    for pat, lnks in groups.items():
        if "{id}" not in pat:
            continue  # 跳过没有 ID 占位符的（列表页自身等）
        results.append({
            "pattern": pat,
            "count": len(lnks),
            "links": lnks,
        })

    results.sort(key=lambda x: x["count"], reverse=True)
    return results


def _discover_category_links(client: BrowserActClient, base_url: str) -> list[dict]:
    """从页面中提取分类/导航链接。

    通过 markdown 提取链接（CDP snapshot 的 href 在 JS 渲染站可能为空）。

    策略:
    1. 优先找路径含 'type'、'class'、'category'、'tag' 等关键词的链接
    2. 排除首页、搜索、帮助等通用链接
    """
    from urllib.parse import urlparse
    from crawler.fast_crawler import extract_links_from_markdown
    nav_keywords = ["type", "class", "categor", "tag", "genre", "sort", "list", "show"]
    exclude_keywords = ["login", "register", "help", "about", "contact", "search", "user", "account"]
    exclude_path_patterns = [r"/voddetail/", r"/vodplay/", r"/artdetail/", r"/article/", r"/static/", r"/rss/", r"/map\.", r"\.xml", r"\.png", r"\.jpg", r"\.svg"]
    base_netloc = urlparse(base_url).netloc

    categories = []
    seen_urls = set()

    md = client.get_markdown()
    links = extract_links_from_markdown(md, base_url=base_url)

    for lk in links:
        href = lk["url"]
        text = lk.get("text", "")
        if not href or href == "/" or href.startswith("#") or href.startswith("javascript"):
            continue
        # 只取站内链接
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != base_netloc:
            continue
        if href in seen_urls:
            continue
        # 排除首页本身
        path = parsed.path
        if path in ("", "/"):
            continue
        # 排除通用链接
        text_lower = text.lower()
        path_lower = path.lower()
        if any(kw in text_lower or kw in path_lower for kw in exclude_keywords):
            continue
        # 排除图片链接（markdown 图片的 text 以 ![ 开头）
        if text.startswith("!["):
            continue
        # 排除详情页/播放页链接（只保留分类入口）
        if any(re.search(p, path_lower) for p in exclude_path_patterns):
            continue
        # 优先匹配分类链接
        has_nav = any(kw in path_lower for kw in nav_keywords)
        seen_urls.add(href)
        categories.append({
            "url": href,
            "text": text.strip(),
            "path": path,
            "is_nav": has_nav,
        })

    # 排序：导航关键词匹配的排前面
    categories.sort(key=lambda x: (0 if x["is_nav"] else 1, x["path"]))
    return categories


def _quick_check_pagination(client: BrowserActClient, url: str, on_log=None) -> Optional[dict]:
    """快速检查一个 URL 是否为列表页（有翻页/有详情链接模式）。

    Returns:
        {"pagination": str, "detail_pattern": str, "content_type": str} or None
    """
    try:
        snap = client.ensure_session(url=url, max_wait_cf=30)
    except Exception:
        return None

    # 方法1: 检查 URL 是否有页码模式
    url_inc = _detect_url_increment(url)
    if url_inc:
        return {"pagination": "url_increment", "template": url_inc["template"], "detail_pattern": None, "content_type": None}

    # 方法2: 检查 markdown 里的链接是否有详情模式
    try:
        md = client.get_markdown()
        from crawler.fast_crawler import extract_links_from_markdown
        raw_links = extract_links_from_markdown(md, base_url=url)
        clusters = _cluster_links(raw_links, url)
        if clusters:
            best = clusters[0]
            pat_lower = best["pattern"].lower()
            content_type = "video"
            if any(kw in pat_lower for kw in ["pic", "photo", "image", "art", "gallery", "album"]):
                content_type = "art"
            return {
                "pagination": "needs_check",
                "detail_pattern": best["pattern"],
                "detail_count": best["count"],
                "content_type": content_type,
            }
    except Exception:
        pass

    return None


def auto_config_multi(
    url: str,
    client: BrowserActClient,
    max_wait_cf: int = 60,
    max_categories: int = 20,
    on_log: Optional[callable] = None,
    is_homepage: bool = True,
) -> AutoConfigResult:
    """多分类自动分析：输入网站主页或分类页，自动发现所有分类并逐个分析。

    is_homepage=True（默认）：输入 URL 为首页/根页，自动发现分类导航并逐个分析
    is_homepage=False：输入 URL 为列表页，直接按列表页分析（不走分类发现）

    流程:
    1. 打开 URL，检查是否为列表页（有翻页/详情链接模式）
    2. 如果不是 → 提取导航分类链接 → 逐个检查是否为列表页
    3. 对所有发现的列表页调用 auto_config()
    4. 合并结果为多 entry_points 的单站点配置

    Returns:
        AutoConfigResult (config 中有多个 entry_points)
    """
    result = AutoConfigResult()
    if on_log:
        result.log = _CallbackList(callback=on_log)

    log = result.log.append

    # ── Phase 1: 判断输入 URL ──────────────────────
    log(f"[Phase 1] 分析输入 URL: {url}")
    snap = None
    try:
        snap = client.ensure_session(url=url, max_wait_cf=max_wait_cf)
    except RuntimeError as e:
        result.errors.append(str(e))
        log(f"  ❌ 页面加载失败: {e}")
        return result

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    site_name = parsed.netloc.replace(".", "_")

    # is_homepage=True → 直接走分类发现（跳过列表页判断，避免首页误判）
    # is_homepage=False → 调用 _quick_check_pagination 判断是否为列表页
    if is_homepage:
        log("  用户指定为首页（is_homepage=True），直接发现分类导航...")
        quick = None
    else:
        log("  快速检查是否为列表页...")
        quick = _quick_check_pagination(client, url, on_log)

    category_urls = []  # 需要逐个分析的分类页列表

    # 记录未被分析的其他分类，供用户后续选择
    extra_categories = []

    if quick and quick["detail_pattern"]:
        # 输入 URL 本身就是列表页
        log(f"  ✅ 当前页已是列表页: 详情模式={quick['detail_pattern']}, 类型={quick.get('content_type', '?')}")
        category_urls.append({"url": url, "text": "当前页", "type_hint": quick.get("content_type")})
    else:
        # 不是列表页 → 发现分类
        log("  当前页不是列表页，开始发现分类导航...")
        cats = _discover_category_links(client, base_url)
        log(f"  发现 {len(cats)} 个候选链接")

        # 不去重，全部检查（后续会按URL模式聚类，每模式只分析1个）
        valid_cats = []
        for cat in cats[:max_categories]:
            if on_log:
                log(f"  检查: {cat['text'][:30]} → {cat['url'][:60]}")
            quick = _quick_check_pagination(client, cat["url"], on_log)
            if quick and quick["detail_pattern"]:
                ct = quick.get("content_type", "video")
                if on_log:
                    log(f"    ✅ 列表页: {quick['detail_pattern']} ({ct})")
                valid_cats.append({"url": cat["url"], "text": cat["text"], "type_hint": ct})
            else:
                if on_log:
                    log(f"    - 非列表页")

        if not valid_cats:
            # 兜底：把第一个 URL 当列表页分析
            log("  ⚠️ 未发现任何列表页分类，将尝试分析当前页")
            category_urls.append({"url": url, "text": "默认", "type_hint": None})
        else:
            category_urls = valid_cats
            # 所有未分析的链接记录到 extra_categories
            for cat in cats[max_categories:]:
                extra_categories.append(cat)

    log(f"\n[Phase 2] 共 {len(category_urls)} 个分类页待分析")

    # ── Phase 2: 逐个分析分类页 ──────────────────────
    all_entry_points = []
    all_link_patterns = {"video_detail": [], "art_detail": []}
    all_extract_chains = {}
    all_pagination = None

    for i, cat in enumerate(category_urls):
        log(f"\n{'='*50}")
        log(f"  [{i+1}/{len(category_urls)}] 分析: {cat['text'][:40]}")
        log(f"  URL: {cat['url'][:80]}")
        log(f"{'='*50}")

        # 对每个分类调用 auto_config
        cat_result = auto_config(
            list_url=cat["url"],
            client=client,
            max_wait_cf=max_wait_cf,
            on_log=on_log,
        )

        if cat_result.success and cat_result.config:
            cfg = cat_result.config
            # 合并 entry_points
            for ep in cfg.get("entry_points", []):
                ep["name"] = cat["text"] if cat["text"] != "当前页" else ep.get("name", cat["text"])
                if cat.get("type_hint"):
                    ep["type"] = cat["type_hint"]
                all_entry_points.append(ep)

            # 合并 link_patterns
            lp = cfg.get("link_patterns", {})
            for k in ("video_detail", "art_detail"):
                for p in lp.get(k, []):
                    if p not in all_link_patterns[k]:
                        all_link_patterns[k].append(p)

            # 合并 extract_chains
            for chain_name, chain_data in cfg.get("extract_chains", {}).items():
                if isinstance(chain_data, dict):
                    all_extract_chains[chain_name] = chain_data

            # 取第一个有效的翻页配置
            if not all_pagination:
                pag = cfg.get("pagination", {})
                if pag and pag.get("type") not in ("none", "unknown"):
                    all_pagination = pag

            log(f"  ✅ 分类分析完成")
        else:
            log(f"  ⚠️ 分类分析失败: {cat_result.errors}")

    # ── Phase 3: 合并生成最终配置 ──────────────────
    if not all_entry_points:
        result.errors.append("所有分类分析均失败")
        log("\n❌ 所有分类分析均失败")
        return result

    log(f"\n{'='*50}")
    log(f"[Phase 3] 生成最终配置")
    log(f"  入口数: {len(all_entry_points)}")
    log(f"  提取链: {list(all_extract_chains.keys())}")
    log(f"{'='*50}")

    final_config = {
        "name": site_name,
        "base_url": base_url,
        "entry_points": all_entry_points,
        "link_patterns": all_link_patterns,
    }
    if all_pagination:
        final_config["pagination"] = all_pagination
    if all_extract_chains:
        final_config["extract_chains"] = all_extract_chains
    # 额外发现的分类，供用户后续选择分析
    if extra_categories:
        final_config["_extra_categories"] = [
            {"url": c["url"], "text": c["text"], "path": c["path"]}
            for c in extra_categories[:50]  # 最多存50个
        ]

    result.config = final_config
    result.success = True
    log("\n  ✅ 多分类配置生成完成")

    return result


def _try_capture_stream(
    client: BrowserActClient,
    snap: "StateSnapshot",
    result: AutoConfigResult,
    max_attempts: int = 8,
    poll_interval: float = 1.5,
) -> Optional[str]:
    """网络优先：以"捕获到流地址"为唯一成功标准，交互只是触发手段。

    交互策略优先级：
    1. 直接查 network（页面可能自动播放了）
    2. 点播放按钮（"立即播放"/"在线播放"等）
    3. 点 video/iframe 元素（触发播放）
    4. 选第一个集数标签
    5. 选第一个线路标签
    6. JS 提取兜底
    """
    from crawler.fast_crawler import _extract_stream_from_network, _extract_stream_from_js

    client.network_clear()

    # ── 策略 1: 直接查 network（自动播放页面）
    stream = _extract_stream_from_network(client)
    if stream:
        result.log.append("  策略1: 页面自动播放，直接捕获")
        return stream

    # ── 策略 2: 点播放按钮
    play_keywords = {"立即播放", "在线播放", "播放", "Play", "play", "播放视频"}
    play_btn = None
    for el in snap.elements:
        if el.text.strip() in play_keywords and el.tag in ("a", "button"):
            play_btn = el
            break
    if not play_btn:
        for el in snap.elements:
            cls = (el.class_name or "").lower()
            if "play" in cls and el.tag in ("a", "button"):
                play_btn = el
                break

    if play_btn:
        result.log.append(f"  策略2: 点击播放按钮 [{play_btn.index}] '{play_btn.text.strip()}'")
        client.click(play_btn.index)
        # 轮询等待流出现
        for _ in range(max_attempts):
            time.sleep(poll_interval)
            stream = _extract_stream_from_network(client)
            if stream:
                return stream

    # ── 策略 3: 点 video/iframe 元素
    for el in snap.elements:
        if el.tag in ("video", "iframe"):
            result.log.append(f"  策略3: 点击 {el.tag} 元素 [{el.index}]")
            client.click(el.index)
            for _ in range(max_attempts):
                time.sleep(poll_interval)
                stream = _extract_stream_from_network(client)
                if stream:
                    return stream
            break  # 只点第一个 video/iframe

    # ── 策略 4: 选第一个集数标签
    episode_keywords = {"集", "ep", "episode", "第"}
    for el in snap.elements:
        t = el.text.strip()
        if any(kw in t.lower() for kw in episode_keywords) and el.tag == "a" and len(t) < 20:
            result.log.append(f"  策略4: 点击集数 [{el.index}] '{t}'")
            client.click(el.index)
            for _ in range(max_attempts):
                time.sleep(poll_interval)
                stream = _extract_stream_from_network(client)
                if stream:
                    return stream
            break

    # ── 策略 5: 选第一个线路标签
    route_keywords = {"线路", "播放源", "源", "source", "line"}
    for el in snap.elements:
        t = el.text.strip()
        if any(kw in t.lower() for kw in route_keywords) and el.tag == "a" and len(t) < 20:
            result.log.append(f"  策略5: 点击线路 [{el.index}] '{t}'")
            client.click(el.index)
            for _ in range(max_attempts):
                time.sleep(poll_interval)
                stream = _extract_stream_from_network(client)
                if stream:
                    return stream
            break

    # ── 策略 6: JS 提取兜底
    result.log.append("  策略6: JS 提取兜底")
    stream = _extract_stream_from_js(client)
    if stream:
        return stream

    return None


def _detect_url_increment(url: str) -> Optional[dict]:
    """检测 URL 是否为数字递增翻页模式。

    匹配规则：页码数字被非数字字符包围（如 -2-、_3_、~4~、.5. 等），
    即 path 中「非数字 + 数字 + 非数字」模式中的数字段。
    优先取最后一个满足条件的候选作为页码。
    后缀不限定，可以是 .html/.php/.asp 或无后缀。

    例: /vodtype/3-6.html      → template: /vodtype/3-{page}.html, current_val=6
        /vodshow/12--------2---.html → template: /vodshow/12--------{page}---.html, current_val=2
        /list/page~3~          → template: /list/page~{page}~, current_val=3
        /topic/5_2             → template: /topic/5_{page}, current_val=2
    """
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    path = parsed.path

    # 找所有「非数字 + 数字 + 非数字」的数字段（页码候选）
    # 前后各至少一个非数字、非斜杠字符，数字本身不含 /
    candidates = []
    for m in re.finditer(r'(?<=[^/\d])\d+(?=[^/\d])', path):
        num_val = int(m.group())
        if num_val <= 500:  # 排除大数字（分类 ID 等）
            candidates.append(m)

    if not candidates:
        return None

    # 取最后一个候选作为页码
    last = candidates[-1]
    num_val = int(last.group())

    start, end = last.start(), last.end()
    template = path[:start] + "{page}" + path[end:]
    next_val = num_val + 1
    next_path = path[:start] + str(next_val) + path[end:]
    next_url = urlunparse((parsed.scheme, parsed.netloc, next_path, parsed.params, parsed.query, ""))

    return {
        "template": template,
        "current_val": num_val,
        "next_url": next_url,
    }


def _find_page_number_buttons(client: BrowserActClient, on_log=None) -> list[tuple[int, int]]:
    """从翻页区域找数字页码按钮。返回 [(index, page_num), ...]。
    
    优化策略（3级）：
    1. 预检：先快照 DOM，看页码按钮是否已存在
    2. JS 跳到底部：scroll_to_bottom() 一次跳转
    3. 兜底：遍历全 DOM（最慢）
    """
    try:
        # --- 策略1: 预检 ---
        snap = client.parsed_state()
        if snap and snap.elements:
            quick_buttons = []
            for el in snap.elements:
                if el.tag not in ("a", "button"):
                    continue
                text = (el.text or "").strip()
                if text.isdigit() and 2 <= int(text) <= 999:
                    quick_buttons.append((el.index, int(text)))
            if len(quick_buttons) >= 2:
                # 已经有足够按钮，无需滚动
                seen = set()
                unique = []
                for idx, num in quick_buttons:
                    if num not in seen:
                        seen.add(num)
                        unique.append((idx, num))
                return sorted(unique, key=lambda x: x[1])[:5]

        # --- 策略2: JS 跳到底部 ---
        if on_log:
            on_log("    滚动到页面底部...")
        client.scroll_to_bottom()
        time.sleep(1.5)  # JS 渲染需要一点时间

        snap = client.parsed_state()
        if not snap or not snap.elements:
            if on_log:
                on_log("    _find_page_number_buttons: snap 为空")
            return []

        buttons = []
        for el in snap.elements:
            if el.tag not in ("a", "button"):
                continue
            text = (el.text or "").strip()
            if text.isdigit() and 2 <= int(text) <= 999:
                buttons.append((el.index, int(text)))

        if on_log and not buttons:
            # 调试：看看有哪些 a/button 元素
            debug_els = [(el.index, el.tag, (el.text or "").strip()[:20]) for el in snap.elements if el.tag in ("a", "button")]
            on_log(f"    数字按钮为0, a/button元素: {debug_els[:10]}")

        # 去重（同页码取第一个）
        seen = set()
        unique = []
        for idx, num in buttons:
            if num not in seen:
                seen.add(num)
                unique.append((idx, num))
        return sorted(unique, key=lambda x: x[1])[:5]
    except Exception as e:
        if on_log:
            on_log(f"    _find_page_number_buttons 异常: {e}")
        return []


def auto_config(
    list_url: str,
    client: BrowserActClient,
    max_wait_cf: int = 60,
    on_log: Optional[callable] = None,
) -> AutoConfigResult:
    """一键自动配置。

    Args:
        list_url: 列表页 URL
        client: BrowserActClient 实例（会自动复用已有会话或重建）
        max_wait_cf: CF 验证最长等待秒数
        on_log: 可选日志回调，每条日志实时调用 on_log(line)

    Returns:
        AutoConfigResult
    """
    result = AutoConfigResult()

    # 替换 log 为带回调的列表
    if on_log:
        result.log = _CallbackList(callback=on_log)

    # ── Step 1: 打开列表页 ──────────────────────────────
    result.log.append(f"[1] 打开列表页: {list_url}")
    try:
        snap = client.ensure_session(url=list_url, max_wait_cf=max_wait_cf)
    except RuntimeError as e:
        result.errors.append(str(e))
        result.log.append(f"  ❌ {e}")
        return result

    result.log.append(f"  ✅ 页面加载: {snap.title[:60]}")
    list_snap = snap

    # ── Step 1.5: 分析翻页 ───────────────────────────
    result.log.append("[1.5] 分析翻页...")
    ptype = "none"
    current = 0
    total = 1
    pagination = None
    url_increment_pattern = None  # (template, current_val)

    # 策略1: 先尝试从当前 URL 检测递增模式（适用于页码已出现在第一页的情况）
    url_inc = _detect_url_increment(list_url)
    if url_inc:
        result.log.append(f"  [策略1] URL 数字递增模式: {url_inc['template']} (当前={url_inc['current_val']})")
        next_url = url_inc['next_url']
        result.log.append(f"  验证下一页: {next_url}")
        try:
            import urllib.request
            req = urllib.request.Request(next_url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status == 200:
                ptype = "url_increment"
                current = url_inc['current_val']
                total = 0
                url_increment_pattern = url_inc
                result.log.append(f"  ✅ URL递增翻页确认: page {current} → {current+1}")
        except Exception as e:
            result.log.append(f"  下一页验证失败: {e}")

    # 策略2: 点击数字页码按钮 → 比对 URL
    if ptype == "none":
        result.log.append("  [策略2] 点击数字页码按钮，比对 URL...")
        page_buttons = _find_page_number_buttons(client, on_log=on_log)

        if page_buttons:
            # 记录当前 URL（第1页）
            snap_before = client.parsed_state()
            before_url = snap_before.url if snap_before else ""
            result.log.append(f"  当前URL: {before_url}")

            # 点击第2页
            idx2, num2 = page_buttons[0]
            result.log.append(f"  点击第{num2}页 (index={idx2})")
            client.click(idx2)
            time.sleep(2)

            snap_after = client.parsed_state()
            after_url = snap_after.url if snap_after else ""
            result.log.append(f"  点击后URL: {after_url}")

            if after_url and after_url != before_url:
                url_inc2 = _detect_url_increment(after_url)
                if url_inc2:
                    # 再点击第3页确认
                    if len(page_buttons) >= 2:
                        # 回到第1页再点第3页
                        client.navigate(before_url)
                        time.sleep(1)
                        # 重新滚动找按钮
                        for _ in range(8):
                            client.scroll_down()
                        time.sleep(0.5)
                        snap_p3 = client.parsed_state()
                        # 找第3页按钮
                        idx3 = None
                        if snap_p3:
                            for el in snap_p3.elements:
                                t = (el.text or "").strip()
                                if t.isdigit() and int(t) == 3 and el.tag in ("a", "button"):
                                    idx3 = el.index
                                    break
                        if idx3 is not None:
                            client.click(idx3)
                            time.sleep(2)
                            snap_p3_after = client.parsed_state()
                            url3 = snap_p3_after.url if snap_p3_after else ""
                            url_inc3 = _detect_url_increment(url3) if url3 else None

                            if url_inc3 and url_inc3['template'] == url_inc2['template']:
                                result.log.append(f"  第3页URL确认: {url3}")

                    ptype = "url_increment"
                    current = 1  # 我们从第1页开始
                    total = 0
                    url_increment_pattern = url_inc2
                    result.log.append(f"  ✅ 页码点击比对成功: template={url_inc2['template']}")
                else:
                    result.log.append("  ⚠ URL变化但未识别到页码模式")

            # 回到第1页
            if after_url != before_url:
                client.navigate(before_url)
                time.sleep(2)
        else:
            result.log.append("  ⚠ 未找到数字页码按钮")

    # 策略3: 找不到页码链接时，用 find_next_page() 点击"下一页"
    if ptype == "none":
        result.log.append("  [策略3] 用 find_next_page() 点击翻页...")
        snap = client.parsed_state()
        next_el = snap.find_next_page() if snap else None

        if next_el and hasattr(next_el, 'index'):
            result.log.append(f"  找到下一页按钮: {next_el.text or next_el.href or 'index=' + str(next_el.index)}")
            # 记录当前 URL
            before_url = snap.url or list_url
            result.log.append(f"  翻页前 URL: {before_url}")

            # 点击
            client.click(next_el.index)
            time.sleep(2)

            # 检查 URL 变化
            after_snap = client.parsed_state()
            after_url = after_snap.url if after_snap else ""
            result.log.append(f"  翻页后 URL: {after_url}")

            if after_url and after_url != before_url:
                url_inc = _detect_url_increment(after_url)
                if url_inc:
                    ptype = "url_increment"
                    current = url_inc.get('current_val', 2)
                    total = 0
                    url_increment_pattern = url_inc
                    result.log.append(f"  ✅ 点击翻页成功: template={url_inc['template']}, current={current}")
                else:
                    result.log.append("  URL 变化但未识别到页码模式")
            else:
                result.log.append("  URL 未变化，SPA/JS 翻页")

            # 回到第一页
            client.navigate(before_url)
            time.sleep(2)

        # 纯 DOM 翻页检测（最终回退）
        if ptype == "none":
            result.log.append("  [策略4] 纯 DOM 翻页检测...")
            snap = client.parsed_state()
            pagination = snap.find_pagination_info() if snap else None

            if pagination:
                ptype = pagination.get('type', 'unknown') if isinstance(pagination, dict) else getattr(pagination, 'type', 'unknown')
                current = pagination.get('current_page', 0) if isinstance(pagination, dict) else getattr(pagination, 'current_page', 0)
                total = pagination.get('total_pages', 0) if isinstance(pagination, dict) else getattr(pagination, 'total_pages', 0)
                result.log.append(f"  DOM 翻页: type={ptype}, current={current}, total={total}")
            else:
                result.log.append("  未检测到翻页结构")

        # 回到顶部
        client.scroll_top()
        time.sleep(1)

    # ── Step 2: 提取链接 & 聚类 ─────────────────────────
    result.log.append("[2] 提取链接 & 聚类...")
    md = client.get_markdown()
    from crawler.fast_crawler import extract_links_from_markdown

    raw_links = extract_links_from_markdown(md, base_url=list_url)
    result.log.append(f"  原始链接: {len(raw_links)}")

    clusters = _cluster_links(raw_links, list_url)

    if not clusters:
        result.errors.append("无法识别详情页链接模式")
        result.log.append("  ❌ 没有找到含 ID 的链接模式")
        return result

    # 展示 top 3
    for i, c in enumerate(clusters[:3]):
        result.log.append(f"  模式 {i+1}: {c['pattern']} ({c['count']} 个)")
        if c['links']:
            result.log.append(f"    示例: {c['links'][0]['text'][:40]} → {c['links'][0]['url'][:60]}")

    # 选择最佳聚类：启发式优先级
    # 1. 路径含 detail/play/video/episode 的是详情页
    # 2. 数量在 3-500 范围内（排除过少或导航链接）
    # 3. 数量越多越好
    DETAIL_KEYWORDS = ["detail", "play", "episode", "movie", "view", "show"]
    EXCLUDE_KEYWORDS = ["type", "class", "categor", "tag", "search", "sort"]

    scored = []
    for c in clusters:
        score = 0
        # 关键词加分
        pat_lower = c["pattern"].lower()
        excluded = any(kw in pat_lower for kw in EXCLUDE_KEYWORDS)
        if excluded:
            score -= 200  # 排除分类/导航页
        for kw in DETAIL_KEYWORDS:
            if kw in pat_lower:
                score += 100
                break
        # 路径深度加分（详情页通常更深）
        depth = c["pattern"].count("/")
        score += depth * 10
        # 数量分
        if 3 <= c["count"] <= 500:
            score += 50
        elif c["count"] > 500:
            score += 20  # 太多可能是导航
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]
    detail_links = best["links"]
    detail_pattern = best["pattern"]

    # 判断内容类型：如果 URL 包含 video/play 等关键词，是视频；包含 pic/photo/image，是图集；否则默认视频
    content_type = "video"
    if any(kw in detail_pattern.lower() for kw in ["pic", "photo", "image", "art", "gallery", "album"]):
        content_type = "art"

    result.log.append(f"  选择: {detail_pattern} ({len(detail_links)} 个链接), 类型: {content_type}")

    # ── Step 3: 进入详情页提取流地址 ─────────────────────
    first_detail = detail_links[0]
    detail_url = first_detail["url"]
    result.log.append(f"[3] 进入详情页: {detail_url[:80]}")

    client.navigate(detail_url)
    # 轮询等页面就绪：非 CF + 有主要内容（播放按钮/视频/iframe/多个链接）
    snap = None
    for attempt in range(15):
        time.sleep(1)
        try:
            snap = client.parsed_state()
            t = snap.title.lower()
            if "moment" in t or "稍候" in t or "verify" in t or "checking" in t:
                continue
            # 页面非 CF，检查是否有实质性内容
            has_content = (
                any(el.tag in ("video", "iframe") for el in snap.elements)
                or any(el.text.strip() in {"立即播放", "在线播放", "播放", "Play", "play"} and el.tag in ("a", "button") for el in snap.elements)
                or sum(1 for el in snap.elements if el.tag == "a") >= 5
            )
            if has_content:
                break
        except RuntimeError:
            continue

    stream_url = None
    stream_format = ""

    if content_type == "video" and snap:
        stream_url = _try_capture_stream(client, snap, result)

        if stream_url:
            from crawler.fast_crawler import _detect_format
            stream_format = _detect_format(stream_url)
            result.log.append(f"  ✅ 流地址: {stream_url[:80]}")
            result.log.append(f"  格式: {stream_format}")
        else:
            result.log.append("  ⚠️ 未抓到流地址（可能需要手动配置）")
    elif content_type == "art":
        # 图集：提取图片
        from crawler.fast_crawler import _extract_images_combined
        images = _extract_images_combined(client)
        result.log.append(f"  图片: {len(images)} 张")

    # ── Step 4: 生成配置 ────────────────────────────────
    result.log.append("[4] 生成配置...")

    parsed = urlparse(list_url)
    site_name = parsed.netloc.replace(".", "_")
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # 推断 link_pattern 正则
    link_pattern_re = detail_pattern.replace("{id}", r"\d+")

    config = {
        "name": site_name,
        "base_url": base_url,
        "entry_points": [{
            "name": f"{list_url.split('/')[2]}/{list_url.split('/')[-1].split('-')[0]}",
            "url": list_url,
            "type": content_type,
        }],
        "link_patterns": {
            "video_detail": [link_pattern_re] if content_type == "video" else [],
            "art_detail": [link_pattern_re] if content_type == "art" else [],
        },
        "pagination": {
            "type": ptype if pagination else ("url_increment" if url_increment_pattern else "unknown"),
            "total_pages": total if pagination else 1,
        },
        "extract_chains": [],
    }

    # 如果是 URL 递增翻页，加模板信息
    if url_increment_pattern:
        config["pagination"]["url_template"] = url_increment_pattern["template"]
        config["pagination"]["start_page"] = url_increment_pattern["current_val"]

    # 添加提取链（dict 格式，与 site_config.load() 期望一致）
    if stream_url:
        if ".m3u8" in stream_url:
            config["extract_chains"] = {
                "video": {
                    "steps": [{"name": "network_capture", "filter": ".m3u8", "method": "network_capture", "extract_js": ""}]
                }
            }
        elif ".mp4" in stream_url:
            config["extract_chains"] = {
                "video": {
                    "steps": [{"name": "network_capture", "filter": ".mp4", "method": "network_capture", "extract_js": ""}]
                }
            }
    elif content_type == "art":
        config["extract_chains"] = {
            "art": {
                "steps": [{"name": "images", "method": "css_selector", "selector": "img", "extract_js": ""}]
            }
        }

    result.config = config
    result.success = True
    result.log.append("  ✅ 配置生成完成")

    return result


def format_config_yaml(config: dict) -> str:
    """将配置格式化为可读 YAML。"""
    import yaml
    return yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
