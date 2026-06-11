"""browser-act CLI 封装层（通用，无网站特定逻辑）"""

import subprocess
import shutil
import os
import time
import re
import json
import tempfile
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


class BrowserActClient:
    """封装 browser-act CLI，提供通用浏览器自动化操作。"""

    def __init__(self, session: str = "default", browser_id: Optional[str] = None):
        self.session = session
        self.browser_id = browser_id
        self._cmd = self._find_cli()

    @staticmethod
    def _find_cli() -> str:
        path = shutil.which("browser-act")
        if path:
            return path
        default = os.path.expanduser("~/.local/bin/browser-act")
        if os.path.isfile(default):
            return default
        raise FileNotFoundError(
            "browser-act CLI 未找到，请先安装: uv tool install browser-act-cli --python 3.12"
        )

    def _run(self, *args: str, timeout: int = 60) -> str:
        env = os.environ.copy()
        local_bin = os.path.expanduser("~/.local/bin")
        env["PATH"] = local_bin + os.pathsep + env.get("PATH", "")
        cmd = [self._cmd]
        _NO_SESSION_CMDS = {"session", "proxy", "stealth-extract", "get-skills"}
        needs_session = not (
            args[0] in _NO_SESSION_CMDS
            or (args[0] == "browser" and len(args) > 1 and args[1] == "list")
        )
        if self.session and needs_session:
            cmd += [f"--session={self.session}"]
        cmd += list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            env=env,
        )
        output = result.stdout + result.stderr
        output = re.sub(r"^browser-act\s*:\s*", "", output, flags=re.MULTILINE)
        if result.returncode != 0 and "Error" in output:
            raise RuntimeError(f"browser-act 命令失败: {output.strip()}")
        return output.strip()

    def list_browsers(self) -> list:
        raw = self._run("browser", "list")
        browsers = []
        for line in raw.splitlines():
            m = re.match(
                r'id=(\S+)\s+name="([^"]+)"\s+type=(\S+)\s+state=(\S+)', line
            )
            if m:
                browsers.append(
                    {
                        "id": m.group(1),
                        "name": m.group(2),
                        "type": m.group(3),
                        "state": m.group(4),
                    }
                )
        return browsers

    def get_first_browser_id(self) -> Optional[str]:
        browsers = self.list_browsers()
        return browsers[0]["id"] if browsers else None

    def open(self, url: str) -> str:
        bid = self.browser_id or self.get_first_browser_id()
        if not bid:
            raise RuntimeError("没有可用的浏览器，请先创建。调用 browser create 创建。")
        return self._run("browser", "open", bid, url, timeout=60)

    def _session_exists(self) -> bool:
        """通过 session list 检查当前 session name 是否还存活（比 parsed_state 更可靠）。"""
        try:
            raw = self._run("session", "list")
            # 输出格式: session_name=xxx browser_type=xxx ...
            for line in raw.splitlines():
                if f"session_name: {self.session}" in line:
                    return True
            return False
        except RuntimeError:
            return False

    def ensure_session(self, url: str = "", max_wait_cf: int = 60) -> "StateSnapshot":
        """确保会话可用。优先复用已有 session，避免不必要的 browser open（减少 CF 触发）。

        检测优先级：
        1. session list 检查 session name 是否存活（最可靠）
        2. parsed_state() 验证页面可用（次要）
        3. 都失败才 browser open 重建

        Returns:
            StateSnapshot of the target page.
        """
        # 第一层：session list 检查（不依赖页面状态，不会因临时超时误判）
        session_alive = self._session_exists()

        if session_alive:
            # Session 还在，直接导航（同站导航不触发 CF）
            if url:
                try:
                    self._run("navigate", url, timeout=30)
                except RuntimeError:
                    # navigate 失败可能只是临时问题，再试一次
                    time.sleep(2)
                    self._run("navigate", url, timeout=30)
        else:
            # Session 真的丢了，重建
            bid = self.browser_id or self.get_first_browser_id()
            if not bid:
                raise RuntimeError("没有可用的浏览器")
            if url:
                self._run("browser", "open", bid, url, timeout=60)
            else:
                raise RuntimeError("需要提供 url 来重建会话")

        # 等 CF 通过
        for i in range(max_wait_cf // 3):
            time.sleep(3)
            try:
                snap = self.parsed_state()
                t = snap.title.lower()
                if "moment" not in t and "稍候" not in t and "verify" not in t and "checking" not in t:
                    return snap
            except RuntimeError:
                continue
        raise RuntimeError(f"CF 验证超时 ({max_wait_cf}s)")

    def navigate(self, url: str) -> str:
        """导航到 URL。若 session 不存在则先打开浏览器。"""
        try:
            return self._run("navigate", url, timeout=30)
        except RuntimeError:
            # Fallback: open browser first
            bid = self.browser_id or self.get_first_browser_id()
            if not bid:
                # Create new browser
                import subprocess
                env = os.environ.copy()
                env["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + env.get("PATH", "")
                result = subprocess.run(
                    [self._cmd, "browser", "create", "--type=chrome-direct"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                output = result.stdout + result.stderr
                # Parse browser id from output like "id=xxx"
                m = re.search(r'id=(\S+)', output)
                if m:
                    self.browser_id = m.group(1)
                    bid = self.browser_id
                else:
                    raise RuntimeError(f"Failed to create browser: {output}")
            return self._run("browser", "open", bid, url, timeout=30)

    def wait(self, seconds: int = 10) -> str:
        import time
        time.sleep(seconds)
        try:
            return self._run("wait", "stable", "--timeout", str(seconds * 1000), timeout=seconds + 10)
        except RuntimeError:
            return "wait_timeout"

    def get_markdown(self) -> str:
        return self._run("get", "markdown", timeout=30)

    def get_html(self) -> str:
        return self._run("get", "html", timeout=60)

    def get_title(self) -> str:
        return self._run("get", "title", timeout=10)

    def solve_captcha(self) -> str:
        return self._run("solve-captcha", timeout=30)

    def click(self, index: int) -> str:
        return self._run("click", str(index), timeout=15)

    def state(self) -> str:
        return self._run("state", timeout=15)

    def scroll_down(self, amount: int = 500) -> str:
        return self._run("scroll", "down", "--amount", str(amount), timeout=10)

    def scroll_top(self) -> str:
        """滚动到页面顶部。"""
        return self._run("eval", "window.scrollTo(0, 0)", timeout=10)

    def scroll_to_bottom(self) -> str:
        """滚动到页面底部（JS 一次跳到底，比多次 scroll_down 快）。"""
        return self._run("eval", "window.scrollTo(0, document.body.scrollHeight)", timeout=10)

    def screenshot(self, path: str = "", full_page: bool = False) -> str:
        """页面截图。

        Args:
            path: 保存路径，空则保存到临时文件
            full_page: 是否截取整个页面（含滚动区域）

        Returns:
            截图文件路径
        """
        args = ["screenshot"]
        if path:
            args.append(path)
        if full_page:
            args.append("--full")
        return self._run(*args, timeout=30)

    def back(self) -> str:
        """浏览器后退。"""
        return self._run("back", timeout=15)

    def forward(self) -> str:
        """浏览器前进。"""
        return self._run("forward", timeout=15)

    def reload(self) -> str:
        """刷新当前页面。"""
        return self._run("reload", timeout=30)

    def input_text(self, index: int, text: str) -> str:
        """点击元素后输入文字（用于搜索框、输入框等）。"""
        return self._run("input", str(index), text, timeout=15)

    def press_key(self, key_combo: str) -> str:
        """发送键盘按键（如 Enter, Tab, Escape 等）。"""
        return self._run("keys", key_combo, timeout=10)

    def wait_selector(self, selector: str, state: str = "visible", timeout: int = 30000) -> str:
        """等待指定元素达到目标状态，比 time.sleep 更可靠。

        Args:
            selector: CSS 选择器
            state: 等待状态 - visible/hidden/attached/detached
            timeout: 超时时间（毫秒）
        """
        return self._run(
            "wait", "selector",
            "--selector", selector,
            "--state", state,
            "--timeout", str(timeout),
            timeout=timeout // 1000 + 10,
        )

    def cookies_get(self, url: str = "") -> str:
        """获取当前页面的 Cookie 列表。可选指定 URL 过滤。"""
        args = ["cookies", "get"]
        if url:
            args.extend(["--url", url])
        return self._run(*args, timeout=10)

    def cookies_set(self, name: str, value: str, url: str = "") -> str:
        """设置 Cookie。"""
        args = ["cookies", "set", name, value]
        if url:
            args.extend(["--url", url])
        return self._run(*args, timeout=10)

    def cookies_export(self, filepath: str) -> str:
        """导出 Cookie 到文件。"""
        return self._run("cookies", "export", filepath, timeout=10)

    def cookies_import(self, filepath: str) -> str:
        """从文件导入 Cookie。"""
        return self._run("cookies", "import", filepath, timeout=10)

    def evaluate_js(self, js_code: str) -> str:
        """执行 JavaScript。超长 JS 写入临时文件后通过 stdin 传入。"""
        if len(js_code) > 500:
            return self._eval_via_stdin(js_code)
        else:
            return self._run("eval", js_code, timeout=30)

    def _eval_via_stdin(self, js_code: str) -> str:
        """通过临时文件 + PowerShell pipe 将超长 JS 传给 browser-act eval --stdin"""
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
        try:
            tmp.write(js_code)
            tmp.close()
            # 用 PowerShell pipe 传递文件内容，避免 Python subprocess 的 stdin 编码问题
            env = os.environ.copy()
            env["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + env.get("PATH", "")
            session_arg = f"--session={self.session}" if self.session else ""
            ps_cmd = f'Get-Content -Path "{tmp.name}" -Raw -Encoding UTF8 | browser-act {session_arg} eval --stdin'
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                timeout=30,
                env=env,
            )
            output = result.stdout.decode("utf-8", errors="replace") + result.stderr.decode("utf-8", errors="replace")
            output = re.sub(r"^browser-act\s*:\s*", "", output, flags=re.MULTILINE)
            if result.returncode != 0 and "Error" in output:
                raise RuntimeError(f"browser-act eval 失败: {output.strip()}")
            return output.strip()
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def evaluate_json(self, js_code: str):
        result = self.evaluate_js(js_code)
        try:
            return json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return None

    def get_all_image_urls(self) -> list:
        js = """
JSON.stringify(Array.from(new Set([
    ...[...document.querySelectorAll('img')].flatMap(img =>
        [img.src, img.dataset.src, img.dataset.original, img.dataset.lazySrc]
        .filter(s => s && !s.startsWith('data:'))
    ),
    ...[...document.querySelectorAll('[style*="background"]')].map(el => {
        const style = getComputedStyle(el);
        const bg = style.backgroundImage;
        const match = bg.match(/url\\(["']?([^"')]+)["']?\\)/);
        return match ? match[1] : null;
    }).filter(Boolean)
])).filter(Boolean))
"""
        return self.evaluate_json(js.strip()) or []

    def execute_step(self, step):
        return self.evaluate_json(step.extract_js)

    # ── Network ──────────────────────────────────────────

    def network_requests(
        self,
        filter_str: str = "",
        req_type: str = "",
        method: str = "",
        status: str = "",
        clear: bool = False,
    ) -> list[dict]:
        """获取已捕获的网络请求列表。

        Args:
            filter_str: URL 子串过滤（如 ".m3u8"）
            req_type: 资源类型过滤，逗号分隔（如 "xhr,fetch"）
            method: HTTP 方法过滤（如 "get"）
            status: 状态码过滤（如 "200", "2xx"）
            clear: 是否同时清除已跟踪的请求

        Returns:
            [{"request_id", "method", "status", "resource_type", "mime_type", "timestamp", "url"}]
        """
        args = ["network", "requests"]
        if filter_str:
            args += ["--filter", filter_str]
        if req_type:
            args += ["--type", req_type]
        if method:
            args += ["--method", method]
        if status:
            args += ["--status", status]
        if clear:
            args.append("--clear")

        raw = self._run(*args, timeout=15)
        lines = raw.strip().splitlines()
        # 跳过标题行 "# format: csv"
        data_lines = [l for l in lines if l and not l.startswith("#")]
        if len(data_lines) < 2:
            return []

        headers = data_lines[0].split(",")
        results = []
        for line in data_lines[1:]:
            # CSV split — url 可能含逗号，取前 6 列 + 剩余为 url
            parts = line.split(",")
            if len(parts) < 7:
                continue
            row = {}
            for i, h in enumerate(headers[:-1]):
                row[h.strip()] = parts[i].strip()
            row["url"] = ",".join(parts[6:])
            results.append(row)
        return results

    def network_request_detail(self, request_id: str) -> dict:
        """获取单个网络请求的详情（含响应体）。"""
        raw = self._run("network", "request", request_id, timeout=15)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {"raw": raw}

    def network_clear(self) -> str:
        """清除已跟踪的网络请求。"""
        return self._run("network", "clear", timeout=10)

    def har_start(self) -> str:
        """开始 HAR 录制。"""
        return self._run("network", "har", "start", timeout=10)

    def har_stop(self, path: str = "") -> str:
        """停止 HAR 录制，可选保存到文件。"""
        args = ["network", "har", "stop"]
        if path:
            args.append(path)
        return self._run(*args, timeout=30)

    # ── State 解析 ────────────────────────────────────────

    def parsed_state(self) -> "StateSnapshot":
        """获取并解析 state 输出为结构化对象。"""
        raw = self.state()
        return StateSnapshot.parse(raw)

    def close_session(self) -> str:
        return self._run("session", "close", self.session, timeout=10)


# ── State 输出解析 ────────────────────────────────────────


@dataclass
class StateElement:
    """state 输出中的一个交互元素。"""
    index: int
    tag: str = ""
    class_name: str = ""
    title: str = ""
    role: str = ""
    aria_label: str = ""
    text: str = ""
    href: str = ""
    input_type: str = ""
    level: int = 0
    compound_components: str = ""

    # 从 text 中推测链接类型
    @property
    def is_link(self) -> bool:
        return self.tag == "a" or bool(self.href)

    @property
    def url_path(self) -> str:
        if not self.href:
            return ""
        try:
            return urlparse(self.href).path
        except Exception:
            return ""


@dataclass
class StateSnapshot:
    """browser-act state 命令的结构化输出。"""
    url: str = ""
    title: str = ""
    elements: list[StateElement] = field(default_factory=list)

    @staticmethod
    def parse(raw: str) -> "StateSnapshot":
        """解析 browser-act state 的文本输出。

        state 输出格式:
            url=...
            title=...
            |SCROLL|<html />
                [1]<tag attrs />same-line-text
                [2]<tag attrs>
                    text-on-next-line
                [3]<tag attrs />
        """
        snapshot = StateSnapshot()
        lines = raw.splitlines()

        # 第 1-5 行: url=... title=...
        for line in lines[:5]:
            m = re.match(r'url=(.+)', line.strip())
            if m:
                snapshot.url = m.group(1).strip()
            m = re.match(r'title=(.+)', line.strip())
            if m:
                snapshot.title = m.group(1).strip()

        # 解析元素行 + 紧跟的文本行
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # 匹配 [N]<tag .../>text 或 [N]<tag ...>text
            m = re.match(r'^\s*\[(\d+)\]<(\w+)([^/>]*?)/>\s*(.*?)\s*$', line)
            if not m:
                m = re.match(r'^\s*\[(\d+)\]<(\w+)([^>]*?)>\s*(.*?)\s*$', line)
            if not m:
                i += 1
                continue

            idx = int(m.group(1))
            tag = m.group(2)
            attrs_str = m.group(3).strip()
            inline_text = m.group(4).strip()

            el = StateElement(index=idx, tag=tag)

            # 解析属性
            el.class_name = _extract_attr(attrs_str, "class")
            el.title = _extract_attr(attrs_str, "title")
            el.role = _extract_attr(attrs_str, "role")
            el.aria_label = _extract_attr(attrs_str, "aria-label")
            el.input_type = _extract_attr(attrs_str, "type")
            el.level = int(_extract_attr(attrs_str, "level") or "0")
            el.compound_components = _extract_attr(attrs_str, "compound_components")

            # href
            href = _extract_attr(attrs_str, "href")
            el.href = href

            # 文本: 同行 > 下一行
            if inline_text:
                el.text = inline_text
            else:
                # 检查下一行是否为纯文本（非元素行、非 |SCROLL|）
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (next_line
                        and not re.match(r'^\s*\[\d+\]', next_line)
                        and not next_line.startswith('|SCROLL|')
                        and not next_line.startswith('▼')
                        and not next_line.startswith('▲')):
                        el.text = next_line
                        i += 1  # 跳过已消费的文本行

            snapshot.elements.append(el)
            i += 1

        return snapshot

    def find_elements(self, **kwargs) -> list[StateElement]:
        """按属性查找元素。例: find_elements(tag="a", class_name="btn")"""
        results = []
        for el in self.elements:
            match = True
            for key, val in kwargs.items():
                el_val = getattr(el, key, None)
                if el_val is None or val not in str(el_val):
                    match = False
                    break
            if match:
                results.append(el)
        return results

    def links(self) -> list[StateElement]:
        """所有链接元素。"""
        return [e for e in self.elements if e.is_link]

    def video_detail_links(self, patterns: list[str] | None = None) -> list[StateElement]:
        """匹配视频详情页的链接。"""
        links = self.links()
        if not patterns:
            return links
        import re as _re
        compiled = [_re.compile(p) for p in patterns]
        return [l for l in links if any(r.search(l.url_path) for r in compiled)]

    def find_next_page(self, current_page: int = 0) -> StateElement | None:
        """查找下一页按钮，支持多种翻页模式。

        模式优先级:
        1. 文本/aria-label 匹配（下一页/Next/›/»等）
        2. class 含 next/page-next
        3. 数字页码按钮组（1 2 3 4 5 → 点 N+1）
        4. 下拉框 select（option 含页码）
        5. "加载更多" 按钮
        6. 尾页链接 → 提取总页数后构造 URL

        Args:
            current_page: 当前页码（0=未知，自动检测）
        """
        # ── 自动检测当前页码 ──
        if current_page == 0:
            current_page = self._detect_current_page()

        # ── 模式 1: 文本/aria-label ──
        next_keywords = {"下一页", "下页", "Next", "next", "›", "»", "≫", "→", ">", "next page", "次へ"}
        for el in self.elements:
            if el.aria_label.lower() in {"next", "next page", "下一页"}:
                return el
            if el.text.strip() in next_keywords:
                return el

        # ── 模式 2: class 含 next/page-next ──
        for el in self.elements:
            cls = el.class_name.lower()
            if "next" in cls and ("page" in cls or "btn" in cls or "pager" in cls or el.is_link):
                return el

        # ── 模式 3: 数字页码按钮组 ──
        page_num_el = self._find_page_number_group(current_page)
        if page_num_el:
            return page_num_el

        # ── 模式 4: 下拉框 select ──
        select_el = self._find_page_select(current_page)
        if select_el:
            return select_el

        # ── 模式 5: "加载更多" 按钮 ──
        load_more_keywords = {"加载更多", "显示更多", "Load more", "load more", "更多", "もっと見る", "Show more"}
        for el in self.elements:
            if el.text.strip() in load_more_keywords:
                return el
            if el.aria_label.strip() in load_more_keywords:
                return el
            cls = el.class_name.lower()
            if "load-more" in cls or "loadmore" in cls or "show-more" in cls:
                return el

        # ── 模式 6: 尾页链接 → 构造下一页 URL ──
        # 由调用方通过 find_last_page() 判断是否还有下一页
        return None

    def find_last_page(self) -> tuple[StateElement | None, int]:
        """查找尾页按钮，返回 (元素, 总页数)。

        尾页文本格式: 尾页(186), 末页, Last(50) 等
        """
        last_keywords = {"尾页", "末页", "Last", "last", "last page", "最後"}
        for el in self.elements:
            if el.text.strip() in last_keywords or el.aria_label.strip() in last_keywords:
                return el, 0  # 未知总页数
        # 带数字的: 尾页(186), Last(50)
        for el in self.elements:
            text = el.text.strip()
            m = re.match(r'(?:尾页|末页|Last|last)[^(]*\((\d+)\)', text)
            if m:
                return el, int(m.group(1))
            cls = el.class_name.lower()
            if "last" in cls and ("page" in cls or "btn" in cls):
                return el, 0
        return None, 0

    def _detect_current_page(self) -> int:
        """从 URL 或 active class 检测当前页码。"""
        # URL: ?page=2, /page/2, -2.html, -----------2--.html
        url = self.url
        m = re.search(r'[?&]page=(\d+)', url)
        if m:
            return int(m.group(1))
        m = re.search(r'/page/(\d+)', url)
        if m:
            return int(m.group(1))
        m = re.search(r'--(\d+)--.*\.html', url)
        if m:
            return int(m.group(1))

        # active class: btn-warm, active, current
        for el in self.elements:
            cls = el.class_name.lower()
            if ("active" in cls or "warm" in cls or "current" in cls) and el.text.strip().isdigit():
                return int(el.text.strip())
        return 0

    def _find_page_number_group(self, current_page: int) -> StateElement | None:
        """查找连续数字页码按钮组，返回 current_page+1 的元素。

        典型模式:
        - [25] 首页  [26] 上一页  [27] 1*  [28] 2  [29] 3  ...  [32] 下一页
        - [72] 1  [73] 2  [74] 3  (无文字导航)
        """
        if current_page == 0:
            return None

        # 收集所有纯数字文本的元素
        num_els: list[StateElement] = []
        for el in self.elements:
            text = el.text.strip()
            if text.isdigit() and 1 <= int(text) <= 9999:
                num_els.append(el)

        if len(num_els) < 2:
            return None

        # 检查是否构成连续数字序列（允许跳页如 1 2 3 ... 10）
        nums = [int(el.text.strip()) for el in num_els]

        # 找 current_page+1
        target = current_page + 1
        for el, num in zip(num_els, nums):
            if num == target:
                return el

        return None

    def _find_page_select(self, current_page: int) -> StateElement | None:
        """查找下拉框翻页 select 元素。"""
        for el in self.elements:
            if el.tag == "select" and el.input_type == "":
                # select 的 options 通常不出现在 state 中
                # 需要配合 click + 选择操作
                return el
        return None

    def find_pagination_info(self) -> dict:
        """获取完整分页信息，供爬虫决策。

        Returns: {
            "type": "button_next" | "number_group" | "select" | "load_more" | "infinite_scroll" | "none",
            "current_page": int,
            "total_pages": int (0=未知),
            "next_element": StateElement | None,
            "page_numbers": [(num, element), ...],
        }
        """
        current_page = self._detect_current_page()
        _, total_pages = self.find_last_page()
        next_el = self.find_next_page(current_page)

        # 数字页码组
        num_els = []
        for el in self.elements:
            text = el.text.strip()
            if text.isdigit() and 1 <= int(text) <= 9999:
                num_els.append((int(text), el))

        # 判断类型
        if next_el is None:
            pag_type = "none"
        elif next_el.text.strip() in {"加载更多", "显示更多", "Load more", "load more", "更多"} or "load" in next_el.class_name.lower():
            pag_type = "load_more"
        elif next_el.text.strip().isdigit():
            pag_type = "number_group"
        else:
            pag_type = "button_next"

        if next_el is None and len(num_els) >= 2:
            # 有数字但没有匹配到 next → 可能需要直接构造 URL
            pag_type = "number_group"

        return {
            "type": pag_type,
            "current_page": current_page,
            "total_pages": total_pages,
            "next_element": next_el,
            "page_numbers": num_els,
        }


def _extract_attr(attrs_str: str, attr_name: str) -> str:
    """从属性字符串中提取属性值。"""
    # class=foo, title="bar baz", aria-label=next
    pattern = rf'{attr_name}=["\']?([^"\'>\s]+)["\']?'
    m = re.search(pattern, attrs_str)
    return m.group(1) if m else ""
