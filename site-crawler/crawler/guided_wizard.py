"""引导式向导 — 用户主动触发的分步网站配置采集。

核心理念:
  - 只录 URL 模式，不录按钮操作
  - 用户主动触发每一步，系统负责分析和反馈
  - 引导式分步: 翻页检测 → 添加路径 → 检测资源 → 完成

用法:
  from crawler.guided_wizard import GuidedWizard
  wizard = GuidedWizard(client)
  session = wizard.start("我的网站", "https://example.com")
  wizard.start_pagination_detect(session.session_id)
  # ... 用户翻页 ...
  result = wizard.end_pagination_detect(session.session_id)
  # ... 用户进入下一级页面 ...
  level = wizard.add_path(session.session_id)
  # ... 用户播放视频 ...
  resources = wizard.detect_resource(session.session_id)
  config = wizard.complete(session.session_id, site_name, start_url)
"""

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, parse_qs

from crawler.logger import get_logger

_log = get_logger("guided_wizard")


# ── 数据模型 ──────────────────────────────────────────────


@dataclass
class GuidedLevel:
    """引导过程中记录的一个页面层级。"""
    level: int                                    # 层级编号 0=列表页, 1/2/3...
    name: str = ""                                # 层级名称（如"详情页"）
    original_url: str = ""                        # 用户录入时的原始 URL
    path_pattern: str = ""                        # 泛化后的 URL 正则模式
    is_resource: bool = False                     # 是否为资源页（检测到视频流）
    resources: list[dict] = field(default_factory=list)  # 检测到的资源 [{type, url}]

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "name": self.name,
            "original_url": self.original_url,
            "path_pattern": self.path_pattern,
            "is_resource": self.is_resource,
            "resources": self.resources,
        }


@dataclass
class PaginationInfo:
    """翻页检测结果。"""
    method: str = ""         # "url_construct" | "button_click" | ""（未检测）
    format: str = ""         # "maccms" | "query_param" | "path_page" | "suffix_page" | "query_other"
    url_before: str = ""
    url_after: str = ""
    generalized: str = ""    # 泛化后的翻页 URL 模式

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "format": self.format,
            "url_before": self.url_before,
            "url_after": self.url_after,
            "generalized": self.generalized,
        }


@dataclass
class GuidedSession:
    """一次引导会话的完整状态。"""
    session_id: str
    site_name: str = ""
    start_url: str = ""
    current_url: str = ""
    levels: list[GuidedLevel] = field(default_factory=list)
    pagination: Optional[PaginationInfo] = None
    pagination_detecting: bool = False
    pagination_url_before: str = ""
    resource_detected: bool = False


# ── URL 泛化 ──────────────────────────────────────────────


def generalize_path(path: str) -> str:
    """将 URL 路径泛化为正则模式。

    例:
      /voddetail/456.html       → /voddetail/\\d+\\.html
      /vodplay/456-1-1.html     → /vodplay/\\d+-\\d+-\\d+\\.html
      /vodshow/1--------2---.html → /vodshow/\\d+--------\\d+---\\.html
      /category/electronics     → /category/electronics  (非数字段不变)
    """
    # 去掉 query string
    clean = path.split("?")[0]

    # 通用策略: 将所有数字序列替换为 \d+
    result = re.sub(r"\d+", r"\\d+", clean)

    # 转义文件扩展名中的点号（.html → \.html）
    result = re.sub(r"\.(html|htm|php|asp|aspx|jsp|do|shtml)$",
                    lambda m: r"\." + m.group(1), result)

    return result


def detect_pagination(url_before: str, url_after: str) -> Optional[dict]:
    """对比两个 URL，识别翻页模式。

    检测策略（按优先级）:
      1. query 参数翻页 (?page=2, ?p=2 等)
      2. /page/N 路径翻页
      3. MacCMS 风格翻页 (数字+短横线组合)
      4. 后缀页码 (/1-2.html)
      5. 其他 query 参数变化

    Returns:
        {"method": "url_construct", "format": "...", "generalized": "..."} 或 None
    """
    if not url_before or not url_after or url_before == url_after:
        return None

    pu_before = urlparse(url_before)
    pu_after = urlparse(url_after)

    path_before = pu_before.path
    path_after = pu_after.path

    # ── 策略 1: query 参数翻页 ──────────────────────
    params_before = parse_qs(pu_before.query)
    params_after = parse_qs(pu_after.query)

    # 常见翻页参数名优先
    page_keys = ["page", "p", "pg", "pageno", "pagenum", "currentPage", "pageNo"]
    for key in page_keys:
        v_after = params_after.get(key, [None])[0]
        if v_after and v_after.isdigit():
            _log.info("翻页检测: query_param key=%s val=%s", key, v_after)
            generalized = f"{pu_after.path}?{key}={{page}}"
            return {
                "method": "url_construct",
                "format": "query_param",
                "generalized": generalized,
            }

    # 其他 query 参数变化（路径相同时）
    if path_before == path_after and url_before != url_after:
        all_keys = set(params_before.keys()) | set(params_after.keys())
        for key in sorted(all_keys):
            v_before = params_before.get(key, [None])[0]
            v_after = params_after.get(key, [None])[0]
            if v_before != v_after and v_after and v_after.isdigit():
                _log.info("翻页检测: query_other key=%s", key)
                generalized = f"{path_after}?{key}={{page}}"
                return {
                    "method": "url_construct",
                    "format": "query_other",
                    "generalized": generalized,
                }

    # ── 策略 2: /page/N 路径翻页 ─────────────────────
    if re.search(r"/page/\d+", path_after) and not re.search(r"/page/\d+", path_before):
        _log.info("翻页检测: path_page")
        generalized = re.sub(r"/page/\d+", "/page/{page}", path_after)
        return {
            "method": "url_construct",
            "format": "path_page",
            "generalized": generalized,
        }

    # ── 策略 3: MacCMS 风格翻页 ─────────────────────
    # MacCMS URL: /vodshow/1-----------.html (无页码)
    #          →  /vodshow/1--------2---.html (有页码)
    # 特征: 路径最后一段由 数字和短横线 组成，且 before/after 都含短横线
    maccms_re = r"^(/[^/]+/)(\d[-\d]*)(\.[\w]+)$"
    m_before = re.match(maccms_re, path_before)
    m_after = re.match(maccms_re, path_after)

    if (m_before and m_after
            and m_before.group(1) == m_after.group(1)
            and m_before.group(3) == m_after.group(3)
            and "-" in m_before.group(2) and "-" in m_after.group(2)):
        code_before = m_before.group(2)  # 如 "1" 或 "1-----------"
        code_after = m_after.group(2)    # 如 "1--------2---"
        prefix = m_after.group(1)
        ext = m_after.group(3)

        nums_before = re.findall(r"\d+", code_before)
        nums_after = re.findall(r"\d+", code_after)

        if len(nums_after) > len(nums_before):
            # 新数字出现 → MacCMS 翻页
            # 将最后一个数字替换为 {page}
            template = re.sub(r"\d+(?=[^\d]*$)", "{page}", code_after)
            generalized = f"{prefix}{template}{ext}"
            _log.info("翻页检测: MacCMS (新数字) before=%s after=%s generalized=%s",
                      code_before, code_after, generalized)
            return {
                "method": "url_construct",
                "format": "maccms",
                "generalized": generalized,
            }

        elif len(nums_after) == len(nums_before) and nums_after != nums_before:
            # 数字变化 → 找到变化的位置替换为 {page}
            for i, (nb, na) in enumerate(zip(nums_before, nums_after)):
                if nb != na:
                    # 替换第 i 个数字组为 {page}
                    matches = list(re.finditer(r"\d+", code_after))
                    if i < len(matches):
                        m_obj = matches[i]
                        template = code_after[:m_obj.start()] + "{page}" + code_after[m_obj.end():]
                        generalized = f"{prefix}{template}{ext}"
                        _log.info("翻页检测: MacCMS (数字变化) generalized=%s", generalized)
                        return {
                            "method": "url_construct",
                            "format": "maccms",
                            "generalized": generalized,
                        }

    # ── 策略 4: 后缀页码 /category/1-2.html ──────────
    suffix_re = r"^(.+?/)(\d+)(?:-(\d+))?(\.[\w]+)?$"
    m_before_s = re.match(suffix_re, path_before)
    m_after_s = re.match(suffix_re, path_after)
    if m_after_s and m_before_s and m_after_s.group(1) == m_before_s.group(1):
        page_after = m_after_s.group(3)
        page_before = m_before_s.group(3)
        base_before = m_before_s.group(2)
        base_after = m_after_s.group(2)
        ext_s = m_after_s.group(4) or ""

        if page_after and page_after.isdigit():
            if not page_before or (base_before == base_after and page_before != page_after):
                _log.info("翻页检测: suffix_page base=%s page=%s", base_after, page_after)
                generalized = f"{m_after_s.group(1)}{{base}}-{{page}}{ext_s}"
                return {
                    "method": "url_construct",
                    "format": "suffix_page",
                    "generalized": generalized,
                }

    _log.warning("翻页检测失败: 无法识别 pattern. before=%s after=%s", path_before, path_after)
    return None


def guess_level_name(path: str, level: int) -> str:
    """根据 URL 路径和层级推断名称。"""
    keywords = {
        "detail": "详情页",
        "voddetail": "详情页",
        "play": "播放页",
        "vodplay": "播放页",
        "video": "视频页",
        "episode": "剧集页",
        "download": "下载页",
        "list": "列表页",
        "category": "分类页",
        "search": "搜索页",
        "tag": "标签页",
        "topic": "专题页",
        "album": "专辑页",
        "chapter": "章节页",
        "read": "阅读页",
        "article": "文章页",
    }
    path_lower = path.lower()
    for kw, name in keywords.items():
        if kw in path_lower:
            return name
    if level == 0:
        return "列表页"
    return f"第{level}级页面"


def match_current_level(current_url: str, levels: list[GuidedLevel]) -> Optional[int]:
    """当前 URL 匹配哪个已记录的 Level？返回 level 编号或 None。"""
    path = urlparse(current_url).path
    for lv in levels:
        try:
            if re.search(lv.path_pattern, path):
                return lv.level
        except re.error:
            continue
    return None


# ── 配置生成 ──────────────────────────────────────────────


def _infer_selector(path_pattern: str) -> str:
    """从 path_pattern 推断 smart_wait 选择器。"""
    parts = path_pattern.strip("/").split("/")
    for part in parts:
        clean = re.sub(r"\\d\+", "", part)
        clean = clean.replace("\\.", ".").replace(".html", "").replace(".htm", "")
        clean = clean.replace("*", "").strip("-.")
        if clean and clean not in ("", "-"):
            return f"a[href*='/{clean}/']"
    return "body"


def _guess_link_type(path_pattern: str) -> str:
    """从 path_pattern 推断 link_type 名称。"""
    keywords = {
        "detail": "video_detail",
        "voddetail": "video_detail",
        "play": "play_page",
        "vodplay": "play_page",
        "download": "download_page",
        "episode": "episode_page",
        "chapter": "chapter_page",
        "article": "article_page",
        "read": "read_page",
    }
    path_lower = path_pattern.lower()
    for kw, lt in keywords.items():
        if kw in path_lower:
            return lt
    # 通用: 用路径第一段非数字部分
    parts = path_pattern.strip("/").split("/")
    for part in parts:
        clean = re.sub(r"\\d\+", "", part)
        clean = clean.replace("\\.", "").replace(".html", "").replace("*", "")
        clean = clean.strip("-.")
        if clean and clean not in ("", "-"):
            return f"{clean}_page"
    return "next_page"


def generate_site_config(
    site_name: str,
    start_url: str,
    levels: list[GuidedLevel],
    pagination: Optional[PaginationInfo],
) -> dict:
    """从引导数据生成完整的 sites.json 配置。"""
    chains = {}
    chain_order = []
    link_patterns = {}

    for i, level in enumerate(levels):
        if i == 0:
            # Level 0 = list_crawl
            chain_name = "list_crawl"
            next_is_resource = (len(levels) > 1 and levels[1].is_resource)
            link_type = "resource" if next_is_resource else "level_1"

            chain = {
                "name": chain_name,
                "steps": [
                    {"action": "navigate"},
                    {"action": "smart_wait", "selector": _infer_selector(level.path_pattern)},
                    {"action": "extract_links", "source": "markdown", "link_type": link_type},
                ],
            }
            if pagination and pagination.method:
                chain["pagination"] = {
                    "methods": [pagination.method],
                    "url_construct": {
                        "format": pagination.format,
                        "url_template": pagination.generalized,
                    },
                    "max_pages": 100,
                }

            chains[chain_name] = chain
            chain_order.append(chain_name)

        elif level.is_resource:
            # 资源页 = stream_capture
            chain_name = "stream_capture"
            chains[chain_name] = {
                "name": chain_name,
                "steps": [
                    {"action": "navigate"},
                    {"action": "smart_wait", "selector": "video, iframe[src], .player, #player, .video-box"},
                    {"action": "network_capture", "filter": ".m3u8,.mp4,.flv,.ts", "wait_seconds": 5},
                ],
            }
            chain_order.append(chain_name)

        else:
            # 中间层级 = level_N
            chain_name = f"level_{i}"
            next_level = levels[i + 1] if i + 1 < len(levels) else None
            next_is_resource = next_level and next_level.is_resource if next_level else False
            link_type = "resource" if next_is_resource else f"level_{i + 1}"

            chain = {
                "name": chain_name,
                "steps": [
                    {"action": "navigate"},
                    {"action": "smart_wait", "selector": _infer_selector(level.path_pattern)},
                    {"action": "extract_links", "source": "markdown", "link_type": link_type},
                ],
            }
            chains[chain_name] = chain
            chain_order.append(chain_name)

    # 构建 link_patterns: 每个非资源 Level 的下一级 path_pattern
    for i, level in enumerate(levels):
        if level.is_resource:
            continue
        if i + 1 < len(levels):
            next_level = levels[i + 1]
            lt = _guess_link_type(next_level.path_pattern)
            if lt not in link_patterns:
                link_patterns[lt] = []
            # 去掉正则转义，生成可存储的正则字符串
            pattern_str = next_level.path_pattern
            link_patterns[lt].append(pattern_str)

    # 从 start_url 提取基 URL
    parsed_start = urlparse(start_url)
    base_url = f"{parsed_start.scheme}://{parsed_start.netloc}"

    # 生成 site_key
    site_key = re.sub(r"[^a-z0-9_]", "_", site_name.lower())[:30]

    return {
        "name": site_name,
        "base_url": base_url,
        "entry_points": [start_url],
        "link_patterns": link_patterns,
        "crawl_pattern": {
            "chain_order": chain_order,
            **chains,
        },
    }


# ── 引导向导核心类 ────────────────────────────────────────


class GuidedWizard:
    """引导式网站配置采集向导。

    管理引导会话的生命周期: 创建 → 翻页检测 → 添加路径 → 检测资源 → 完成。

    每个会话独立维护状态，会话之间互不干扰。
    通过 BrowserActClient 与浏览器交互（命令式），用户控制浏览器操作。
    """

    def __init__(self, client):
        """初始化向导。

        Args:
            client: BrowserActClient 实例（应使用持久化 session）
        """
        self._client = client
        self._sessions: dict[str, GuidedSession] = {}

    def _get_session(self, session_id: str) -> GuidedSession:
        """获取会话，不存在则抛异常。"""
        if session_id not in self._sessions:
            raise ValueError(f"会话不存在: {session_id}")
        return self._sessions[session_id]

    # ── 会话生命周期 ──────────────────────────────────

    def start(self, site_name: str, start_url: str) -> GuidedSession:
        """开始引导：创建 session + 打开浏览器 + 导航到起始 URL。

        Args:
            site_name: 网站名称
            start_url: 起始 URL（通常是列表页）

        Returns:
            GuidedSession 对象
        """
        session_id = f"guided_{uuid.uuid4().hex[:8]}"
        _log.info("开始引导: session_id=%s site_name=%s start_url=%s", session_id, site_name, start_url)

        # 导航到起始 URL
        self._client.navigate(start_url)
        current_url = start_url

        # 尝试获取实际 URL（页面可能重定向）
        try:
            snap = self._client.parsed_state()
            if snap and snap.url:
                current_url = snap.url
                _log.info("页面加载完成: actual_url=%s title=%s", current_url, snap.title[:50])
        except Exception as e:
            _log.warning("获取页面状态失败，使用原始URL: %s", e)

        # 创建 session
        session = GuidedSession(
            session_id=session_id,
            site_name=site_name,
            start_url=start_url,
            current_url=current_url,
            levels=[
                GuidedLevel(
                    level=0,
                    name="列表页",
                    original_url=current_url,
                    path_pattern=generalize_path(urlparse(current_url).path),
                )
            ],
        )
        self._sessions[session_id] = session
        return session

    def get_status(self, session_id: str) -> dict:
        """获取当前引导状态。"""
        session = self._get_session(session_id)

        # 刷新当前 URL
        try:
            snap = self._client.parsed_state()
            if snap and snap.url:
                session.current_url = snap.url
        except Exception:
            pass

        return {
            "ok": True,
            "session_id": session.session_id,
            "site_name": session.site_name,
            "start_url": session.start_url,
            "current_url": session.current_url,
            "levels": [lv.to_dict() for lv in session.levels],
            "pagination": session.pagination.to_dict() if session.pagination else None,
            "pagination_detecting": session.pagination_detecting,
            "resource_detected": session.resource_detected,
        }

    def cancel(self, session_id: str) -> dict:
        """取消引导：清理 session。"""
        session = self._get_session(session_id)
        _log.info("取消引导: session_id=%s", session_id)
        del self._sessions[session_id]
        return {"ok": True, "message": "引导已取消"}

    # ── 翻页检测 ──────────────────────────────────────

    def start_pagination_detect(self, session_id: str) -> dict:
        """开始翻页检测：记录当前 URL。

        用户需要在浏览器中翻页，然后调用 end_pagination_detect()。
        """
        session = self._get_session(session_id)

        # 获取当前 URL
        try:
            snap = self._client.parsed_state()
            session.current_url = snap.url if snap and snap.url else session.current_url
        except Exception:
            pass

        session.pagination_detecting = True
        session.pagination_url_before = session.current_url
        _log.info("开始翻页检测: session_id=%s url_before=%s", session_id, session.current_url)

        return {
            "ok": True,
            "url_before": session.current_url,
        }

    def end_pagination_detect(self, session_id: str) -> dict:
        """结束翻页检测：获取当前 URL + 对比识别翻页模式。

        用户已在浏览器中翻页，点击此按钮后对比 URL 变化。
        """
        session = self._get_session(session_id)

        if not session.pagination_detecting:
            return {"ok": False, "error": "翻页检测未开始，请先点击[开始翻页检测]"}

        url_before = session.pagination_url_before

        # 获取翻页后的 URL
        try:
            snap = self._client.parsed_state()
            url_after = snap.url if snap and snap.url else ""
            session.current_url = url_after
        except Exception as e:
            _log.error("获取翻页后状态失败: %s", e)
            return {"ok": False, "error": f"获取页面状态失败: {e}"}

        session.pagination_detecting = False

        if not url_after or url_after == url_before:
            _log.warning("翻页检测: URL未变化")
            return {
                "ok": False,
                "error": "URL 未发生变化，请确认已在浏览器中翻页后重试",
                "url_before": url_before,
                "url_after": url_after,
            }

        # 检测翻页模式
        result = detect_pagination(url_before, url_after)
        if result is None:
            _log.warning("翻页检测失败: 无法识别模式 before=%s after=%s", url_before[:80], url_after[:80])
            return {
                "ok": False,
                "error": "未能识别翻页模式，URL 变化不足以推断翻页方式。"
                         "请尝试翻到不同页码后重试",
                "url_before": url_before,
                "url_after": url_after,
            }

        pagination = PaginationInfo(
            method=result["method"],
            format=result["format"],
            url_before=url_before,
            url_after=url_after,
            generalized=result["generalized"],
        )
        session.pagination = pagination
        _log.info("翻页检测成功: method=%s format=%s generalized=%s",
                  pagination.method, pagination.format, pagination.generalized)

        return {
            "ok": True,
            "pagination": pagination.to_dict(),
        }

    # ── 添加路径 ──────────────────────────────────────

    def add_path(self, session_id: str) -> dict:
        """添加路径：获取当前 URL → 泛化 → 添加新 Level。"""
        session = self._get_session(session_id)

        # 获取当前 URL
        try:
            snap = self._client.parsed_state()
            current_url = snap.url if snap and snap.url else ""
            session.current_url = current_url
        except Exception as e:
            _log.error("获取当前页面状态失败: %s", e)
            return {"ok": False, "error": f"获取页面状态失败: {e}"}

        if not current_url:
            return {"ok": False, "error": "无法获取当前页面 URL"}

        # 检查是否与已有 Level 重复
        current_path = urlparse(current_url).path
        for lv in session.levels:
            try:
                if re.search(lv.path_pattern, current_path):
                    _log.info("URL 已匹配已有 Level %d: pattern=%s path=%s",
                              lv.level, lv.path_pattern, current_path)
                    return {
                        "ok": True,
                        "level": lv.level,
                        "name": lv.name,
                        "original_url": current_url,
                        "path_pattern": lv.path_pattern,
                        "already_exists": True,
                    }
            except re.error:
                continue

        # 新 Level
        new_level_num = len(session.levels)
        pattern = generalize_path(current_path)
        level_name = guess_level_name(current_path, new_level_num)

        level = GuidedLevel(
            level=new_level_num,
            name=level_name,
            original_url=current_url,
            path_pattern=pattern,
        )
        session.levels.append(level)
        _log.info("添加路径: level=%d name=%s original=%s pattern=%s",
                  level.level, level.name, level.original_url[:80], level.path_pattern)

        return {
            "ok": True,
            "level": level.level,
            "name": level.name,
            "original_url": level.original_url,
            "path_pattern": level.path_pattern,
        }

    def update_path_pattern(self, session_id: str, level: int, new_pattern: str) -> dict:
        """编辑某个 Level 的 path_pattern。"""
        session = self._get_session(session_id)
        for lv in session.levels:
            if lv.level == level:
                old = lv.path_pattern
                lv.path_pattern = new_pattern
                _log.info("更新路径模式: level=%d old=%s new=%s", level, old, new_pattern)
                return {"ok": True, "level": level, "path_pattern": new_pattern}
        return {"ok": False, "error": f"未找到 Level {level}"}

    # ── 检测资源 ──────────────────────────────────────

    def detect_resource(self, session_id: str) -> dict:
        """检测资源：获取网络请求中的 m3u8/mp4/flv/ts。"""
        session = self._get_session(session_id)

        # 确保在正确的页面（刷新当前 URL）
        try:
            snap = self._client.parsed_state()
            current_url = snap.url if snap and snap.url else session.current_url
            session.current_url = current_url
        except Exception:
            pass

        # 检测网络请求中的流媒体
        resources = []
        targets = [".m3u8", ".mp4", ".flv", ".ts"]
        for target in targets:
            try:
                reqs = self._client.network_requests(filter_str=target)
                for req in reqs:
                    url = req.get("url", "")
                    if url:
                        resources.append({
                            "type": target.lstrip("."),
                            "url": url,
                        })
            except Exception as e:
                _log.warning("网络请求检测失败 (filter=%s): %s", target, e)

        if not resources:
            _log.info("未检测到资源: url=%s", session.current_url)
            return {
                "ok": False,
                "error": "未检测到 m3u8/mp4/flv/ts 资源，请确认视频已开始播放后重试",
                "current_url": session.current_url,
            }

        # 匹配当前 URL 到 Level
        matched_level = match_current_level(session.current_url, session.levels)
        if matched_level is not None:
            for lv in session.levels:
                if lv.level == matched_level:
                    lv.is_resource = True
                    lv.resources = resources
                    session.resource_detected = True
                    _log.info("资源检测成功: level=%d type_count=%d", matched_level, len(resources))
        else:
            # 当前 URL 不匹配任何已知 Level → 标记最后一个 Level 为资源页
            if session.levels:
                last = session.levels[-1]
                last.is_resource = True
                last.resources = resources
                session.resource_detected = True
                matched_level = last.level
                _log.info("资源检测成功(末级): level=%d type_count=%d", last.level, len(resources))

        return {
            "ok": True,
            "matched_level": matched_level,
            "resources": resources,
            "current_url": session.current_url,
        }

    # ── 完成 ──────────────────────────────────────────

    def complete(self, session_id: str, site_name: str = "", start_url: str = "") -> dict:
        """完成引导：生成配置 + 写入 sites.json。"""
        session = self._get_session(session_id)

        if not session.levels or len(session.levels) < 2:
            return {
                "ok": False,
                "error": "至少需要添加一个路径才能生成配置",
            }

        site_name = site_name or session.site_name
        start_url = start_url or session.start_url

        # 生成配置
        config = generate_site_config(
            site_name=site_name,
            start_url=start_url,
            levels=session.levels,
            pagination=session.pagination,
        )

        # 写入 sites.json
        site_key = self._save_to_sites_json(site_name, start_url, config)

        _log.info("引导完成: site_key=%s site_name=%s levels=%d",
                  site_key, site_name, len(session.levels))

        # 清理 session
        del self._sessions[session_id]

        return {
            "ok": True,
            "site_key": site_key,
            "config": config,
        }

    @staticmethod
    def _save_to_sites_json(site_name: str, start_url: str, config: dict) -> str:
        """将生成的配置写入 sites.json。

        Returns:
            site_key: 写入的 site key
        """
        sites_path = os.path.join(os.path.dirname(__file__), "..", "sites.json")

        # 读取现有配置
        existing = {}
        if os.path.exists(sites_path):
            with open(sites_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                existing = raw.get("sites", {})

        # 生成 site_key
        site_key = re.sub(r"[^a-z0-9_]", "_", site_name.lower())[:30]
        if site_key in existing:
            # 去重：追加序号
            i = 2
            while f"{site_key}_{i}" in existing:
                i += 1
            site_key = f"{site_key}_{i}"

        # 构建站点条目
        parsed_start = urlparse(start_url)
        base_url = config.get("base_url", f"{parsed_start.scheme}://{parsed_start.netloc}")

        entry_points = []
        for ep_url in config.get("entry_points", [start_url]):
            entry_points.append({
                "name": site_name,
                "url": ep_url,
                "type": config.get("resource_type", "video"),
            })

        group = {
            "name": site_name,
            "resource_type": config.get("resource_type", "video"),
            "entry_points": entry_points,
            "link_patterns": config.get("link_patterns", {}),
            "crawl_pattern": config["crawl_pattern"],
        }

        existing[site_key] = {
            "name": site_name,
            "base_url": base_url,
            "groups": [group],
        }

        # 写回
        output = {"sites": existing}
        with open(sites_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        _log.info("配置已写入 sites.json: site_key=%s", site_key)
        return site_key


# ── 模块级便捷函数 ────────────────────────────────────────

# 已注册的 Wizard 实例（供 Flask 路由使用）
_registered_wizards: dict[str, "GuidedWizard"] = {}


def create_wizard(client) -> GuidedWizard:
    """创建并注册一个新的 GuidedWizard 实例。"""
    wizard = GuidedWizard(client)
    return wizard
