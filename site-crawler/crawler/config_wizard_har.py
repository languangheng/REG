"""HAR 配置向导 — 用户操作浏览器，自动生成 sites.yaml

流程:
1. 打开浏览器 → network har start
2. Python 轮询 state 记录 URL 变化序列
3. 用户自由浏览: 入口页 → 列表页 → 详情页 → 播放页
4. 用户说"完成" → network har stop
5. 分析 HAR 数据:
   - URL 序列 → 生成 URL pattern → link_patterns
   - m3u8/mp4 请求 → 生成 extract_chains
   - 入口 URL → entry_points
6. 输出 sites.yaml 片段
"""

import json
import os
import re
import time
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from crawler.browser_act import BrowserActClient, StateSnapshot
from crawler.logger import get_logger

_log = get_logger("config_wizard_har")


# ── 数据收集 ─────────────────────────────────────────────


@dataclass
class NavigationStep:
    """用户浏览路径中的一步。"""
    url: str
    title: str = ""
    timestamp: float = 0
    m3u8_urls: list[str] = field(default_factory=list)
    mp4_urls: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    api_urls: list[str] = field(default_factory=list)


@dataclass
class RecordingSession:
    """录制会话。"""
    steps: list[NavigationStep] = field(default_factory=list)
    site_name: str = ""
    base_url: str = ""

    def add_step(self, url: str, title: str = "") -> NavigationStep:
        step = NavigationStep(url=url, title=title, timestamp=time.time())
        self.steps.append(step)
        # 推断 base_url
        if not self.base_url and url:
            parsed = urlparse(url)
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        return step


# ── 录制控制器 ───────────────────────────────────────────


class HarWizard:
    """HAR 配置向导控制器。"""

    def __init__(self, client: BrowserActClient):
        self.client = client
        self.recording = RecordingSession()
        self._last_url = ""
        self._running = False
        self._broadcast = None  # 外部注入的广播函数

    def start(self, start_url: str = "", reuse_session: bool = True) -> str:
        """启动录制。
        
        reuse_session=True 时，复用已有浏览器（不 navigate，避免触发 CF）。
        会自动创建会话，用户需先在浏览器中手动过了 CF。
        
        reuse_session=False 时，导航到 start_url（可能触发 CF 验证）。
        """
        _log.info("HAR录制启动: reuse_session=%s, start_url=%s", reuse_session, start_url or "(无)")

        if not reuse_session and start_url:
            self.client.navigate(start_url)
            time.sleep(3)
        else:
            # 确保有活跃会话 — navigate 到当前页即可
            try:
                snapshot = self.client.parsed_state()
                _log.info("复用已有会话: url=%s, title=%s", snapshot.url, snapshot.title)
            except Exception as e:
                _log.warning("会话不存在，需要创建: %s", e)
                # 会话不存在，用 navigate 创建（会自动选浏览器）
                if start_url:
                    self.client.navigate(start_url)
                else:
                    self.client.navigate("about:blank")
                time.sleep(2)

        # 启动 HAR 录制
        self.client.har_start()
        self.client.network_clear()
        self._running = True

        # 记录当前页
        snapshot = self.client.parsed_state()
        self._last_url = snapshot.url
        self.recording.site_name = urlparse(snapshot.url).netloc
        self.recording.add_step(snapshot.url, snapshot.title)
        _log.info("录制开始: url=%s, site_name=%s", snapshot.url, self.recording.site_name)

        return f"录制开始: {snapshot.url}\n请在浏览器中自由浏览，路径会自动记录\n完成后点击「停止录制」"

    def poll(self) -> Optional[NavigationStep]:
        """轮询检测页面变化，记录新步骤。"""
        if not self._running:
            return None
        try:
            snapshot = self.client.parsed_state()
        except Exception:
            return None

        if snapshot.url != self._last_url:
            step = self.recording.add_step(snapshot.url, snapshot.title)
            _log.info("页面变化: url=%s, title=%s", snapshot.url, snapshot.title)

            # 检测流地址
            for ext in [".m3u8", ".mp4", ".flv"]:
                reqs = self.client.network_requests(filter_str=ext)
                for r in reqs:
                    url = r.get("url", "")
                    if r.get("resource_type") in ("XHR", "Fetch"):
                        if ".m3u8" in url and url not in step.m3u8_urls:
                            step.m3u8_urls.append(url)
                        elif ".mp4" in url and url not in step.mp4_urls:
                            step.mp4_urls.append(url)

            # 检测 API 请求
            api_reqs = self.client.network_requests(req_type="xhr,fetch")
            for r in api_reqs:
                url = r.get("url", "")
                mime = r.get("mime_type", "")
                if "json" in mime and url not in step.api_urls:
                    step.api_urls.append(url)

            self._last_url = snapshot.url
            return step

        return None

    def stop(self, har_path: str = "") -> str:
        """停止录制并保存 HAR。"""
        self._running = False
        _log.info("停止录制: steps=%d", len(self.recording.steps))

        # 最后一次检查流地址
        if self.recording.steps:
            last_step = self.recording.steps[-1]
            for ext in [".m3u8", ".mp4", ".flv"]:
                reqs = self.client.network_requests(filter_str=ext)
                for r in reqs:
                    url = r.get("url", "")
                    if r.get("resource_type") in ("XHR", "Fetch"):
                        if ".m3u8" in url and url not in last_step.m3u8_urls:
                            last_step.m3u8_urls.append(url)
                        elif ".mp4" in url and url not in last_step.mp4_urls:
                            last_step.mp4_urls.append(url)

        # 保存 HAR
        if not har_path:
            har_path = str(Path.home() / ".qclaw" / "workspace-tfxjjhfnjialcuju" / "site-crawler" / f"{self.recording.site_name}_har.json")
        try:
            result = self.client.har_stop(har_path)
            _log.info("HAR保存成功: path=%s", har_path)
            return f"HAR 已保存: {har_path}\n{result}"
        except Exception as e:
            _log.error("HAR保存失败: %s", e)
            return f"HAR 保存失败: {e}"

    def run_interactive(self, start_url: str) -> dict:
        """交互式录制：Python 控制台引导用户操作。"""
        _log.info("交互式录制启动: url=%s", start_url)
        start_msg = self.start(start_url)
        print(start_msg)

        try:
            while self._running:
                step = self.poll()
                if step:
                    print(f"\n📍 页面变化: {step.url}")
                    if step.m3u8_urls:
                        print(f"  🎬 m3u8: {step.m3u8_urls[0][:80]}")
                    if step.mp4_urls:
                        print(f"  🎬 mp4: {step.mp4_urls[0][:80]}")
                    if step.api_urls:
                        print(f"  🔗 API: {len(step.api_urls)} 个")

                cmd = input("\n输入命令 (done=完成, status=状态, quit=退出): ").strip().lower()
                if cmd == "done":
                    break
                elif cmd == "status":
                    self._print_status()
                elif cmd == "quit":
                    self._running = False
                    break

                time.sleep(2)
        except KeyboardInterrupt:
            _log.warning("录制被用户中断")
            print("\n录制中断")

        har_result = self.stop()
        print(har_result)

        # 生成配置
        config = self.generate_config()
        _log.info("交互式录制完成: steps=%d", len(self.recording.steps))
        return config

    def _print_status(self):
        """打印当前录制状态。"""
        status = "进行中" if self._running else "已停止"
        _log.info("录制状态: %s, site=%s, steps=%d", status, self.recording.site_name, len(self.recording.steps))
        print(f"\n{'='*50}")
        print(f"  录制状态: {status}")
        print(f"  站点: {self.recording.site_name}")
        print(f"  步骤: {len(self.recording.steps)}")
        for i, step in enumerate(self.recording.steps, 1):
            path = urlparse(step.url).path
            extras = []
            if step.m3u8_urls:
                extras.append(f"m3u8={len(step.m3u8_urls)}")
            if step.mp4_urls:
                extras.append(f"mp4={len(step.mp4_urls)}")
            if step.api_urls:
                extras.append(f"api={len(step.api_urls)}")
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            print(f"  {i}. {path}{extra_str}")
        print(f"{'='*50}")


# ── 配置生成 ─────────────────────────────────────────────


class ConfigGenerator:
    """从录制会话生成 sites.json 分组格式配置。

    支持 site_type 检测：
    - 已知类型（如 maccms）：用内置默认链配置加速生成
    - 未知类型：从录制数据自动推断链结构
    """

    def __init__(self, recording: RecordingSession, group_name: str = "", resource_type: str = "video"):
        self.rec = recording
        self.group_name = group_name or "默认分组"
        self.resource_type = resource_type  # "video" | "art"

    def generate(self) -> dict:
        """生成站点配置字典（分组格式 + 链式操作路径）。"""
        # 检测 site_type
        site_type = self._detect_site_type()

        group = {
            "name": self.group_name,
            "resource_type": self.resource_type,
            "entry_points": self._generate_entry_points(),
            "link_patterns": self._generate_link_patterns(),
            "extract_chains": self._generate_extract_chains(),
        }

        # 已知 site_type → 用内置默认链配置
        if site_type == "maccms":
            from crawler.site_config import MACCMS_CRAWL_PATTERN, MACCMS_LINK_PATTERNS

            if self.resource_type == "art":
                # 图片分组：复制 MACCMS_CRAWL_PATTERN，修改 level_1 为图片捕获
                import copy
                art_cp = copy.deepcopy(MACCMS_CRAWL_PATTERN)
                if "level_1" in art_cp:
                    art_cp["level_1"] = {
                        "steps": [
                            {"action": "navigate", "url_template": ""},
                            {"action": "smart_wait", "selector": "img[src], .art-content, .content, .pic"},
                            {"action": "network_capture", "filter": ".jpg,.jpeg,.png,.webp,.gif",
                             "wait_seconds": 3},
                        ]
                    }
                group["crawl_pattern"] = art_cp
            else:
                group["crawl_pattern"] = MACCMS_CRAWL_PATTERN

            # 合并 link_patterns（视频默认 + 录制推断）
            inferred_lp = group.get("link_patterns", {})
            for key in ("video_detail", "play_page", "exclude"):
                if key not in inferred_lp and key in MACCMS_LINK_PATTERNS:
                    inferred_lp[key] = MACCMS_LINK_PATTERNS[key]
            group["link_patterns"] = inferred_lp
        else:
            # 未知类型 → 从录制数据推断链结构
            crawl_pattern = self._infer_crawl_pattern_from_recording()
            if crawl_pattern:
                group["crawl_pattern"] = crawl_pattern

        config = {
            "name": self.rec.site_name,
            "base_url": self.rec.base_url,
            "groups": [group],
        }
        if site_type:
            config["site_type"] = site_type

        return config

    def _generate_link_patterns(self) -> dict:
        """从 URL 路径序列推断 link_patterns。"""
        paths = [urlparse(s.url).path for s in self.rec.steps]

        video_detail = []
        art_detail = []
        exclude = []

        # 分析路径模式
        path_categories = {}  # pattern -> [paths]
        for path in paths:
            pattern = self._generalize_path(path)
            if pattern not in path_categories:
                path_categories[pattern] = []
            path_categories[pattern].append(path)

        # 有 m3u8 的步骤之前的那一步是 video_detail
        # 有图片的步骤之前的那一步是 art_detail
        video_detail_paths = set()
        art_detail_paths = set()

        # 填充 video_detail_paths（视频分组）
        for i, step in enumerate(self.rec.steps):
            if step.m3u8_urls or step.mp4_urls:
                if i > 0:
                    prev_path = urlparse(self.rec.steps[i-1].url).path
                    video_detail_paths.add(self._generalize_path(prev_path))
                cur_path = urlparse(step.url).path
                if not any(kw in cur_path for kw in ["/play/", "/vodplay/"]):
                    video_detail_paths.add(self._generalize_path(cur_path))

        # 填充 art_detail_paths（图片分组）
        if self.resource_type == "art":
            # 启发式：最后一个步骤大概率是图片详情页
            for step in reversed(self.rec.steps):
                p = urlparse(step.url).path
                # 跳过列表页
                if not any(kw in p for kw in ["/arttype/", "/list", "/category", "/artsearch/"]):
                    art_detail_paths.add(self._generalize_path(p))
                    break
            # 如果上面没找到，用倒数第二步（列表→详情的跳转）
            if not art_detail_paths and len(self.rec.steps) >= 2:
                p = urlparse(self.rec.steps[-1].url).path
                art_detail_paths.add(self._generalize_path(p))

        for pattern in video_detail_paths:
            if pattern and pattern != "/":
                video_detail.append(pattern)

        for pattern in art_detail_paths:
            if pattern and pattern != "/":
                art_detail.append(pattern)

        # 排除模式：列表页、搜索页等
        list_keywords = ["/vodshow/", "/vodtype/", "/vodsearch/", "/topic/", "/tag/", "/static/",
                         "/arttype/", "/artsearch/"]
        for path in paths:
            gen = self._generalize_path(path)
            if any(kw in path for kw in list_keywords) and gen not in exclude:
                exclude.append(gen)

        # 如果没推断出来，给个默认（仅视频分组）
        if not video_detail and self.resource_type == "video":
            for path in paths:
                if re.search(r'/\d+', path) and "/play" not in path and "/vodshow" not in path:
                    video_detail.append(self._generalize_path(path))
                    break

        result = {}
        if video_detail:
            result["video_detail"] = video_detail or ["/voddetail/\\d+"]
        if art_detail:
            result["art_detail"] = art_detail
        if exclude:
            result["exclude"] = exclude or ["/vodshow/", "/vodtype/", "/vodsearch/", "/static/"]

        return result

    def _generate_extract_chains(self) -> dict:
        """从录制数据生成 extract_chains（按 resource_type 使用对应 method）。"""
        chains = {}

        if self.resource_type == "video":
            chains["video"] = self._generate_video_chain()
        elif self.resource_type == "art":
            chains["art"] = self._generate_art_chain()

        return chains

    def _generate_video_chain(self) -> dict:
        """生成视频提取链（network_capture 方式）。"""
        steps = []

        # 检测是否需要中间步骤（详情页 → 播放页）
        has_detail = any(
            any(kw in urlparse(s.url).path for kw in ["/voddetail/", "/detail/"])
            for s in self.rec.steps
            if not s.m3u8_urls and not s.mp4_urls
        )

        # 详情页步骤：如果有详情页和播放页的区分，先导航到详情页
        if has_detail:
            steps.append({
                "name": "enter_detail",
                "method": "navigate",
            })

        # 播放步骤：点击播放按钮 + 等待流出现 + 网络捕获
        steps.append({
            "name": "capture_stream",
            "method": "network_capture",
            "filter": ".m3u8,.mp4,.flv",
            "wait_seconds": 5,
        })

        return {"steps": steps}

    def _generate_art_chain(self) -> dict:
        """生成图片提取链（network_capture 方式）。"""
        steps = []

        # 进入详情页
        steps.append({
            "name": "enter_detail",
            "method": "navigate",
        })

        # 图片网络捕获
        steps.append({
            "name": "capture_images",
            "method": "network_capture",
            "filter": ".jpg,.jpeg,.png,.webp,.gif",
            "wait_seconds": 3,
        })

        return {"steps": steps}

    def _generate_entry_points(self) -> list[dict]:
        """从第一步生成入口点。"""
        if not self.rec.steps:
            return []

        first_url = self.rec.steps[0].url
        first_title = self.rec.steps[0].title or "入口"

        return [
            {"name": first_title.split("-")[0].strip()[:20] or "入口", "url": first_url, "type": self.resource_type}
        ]

    @staticmethod
    def _generalize_path(path: str) -> str:
        """将 URL 路径泛化为正则模式。

        策略：将所有数字序列替换为 \\d+，转义点号。
        例: /voddetail/227275.html    → /voddetail/\\d+\\.html
            /artdetail-38385.html   → /artdetail-\\d+\\.html
            /vodshow/12----.html   → /vodshow/\\d+\\.html
        """
        import re
        # 1. 替换所有数字序列为 \d+
        generalized = re.sub(r'\d+', r'\\d+', path)
        # 2. 转义点号（正则中点号匹配任意字符，需转义）
        generalized = generalized.replace('.', r'\.')
        return generalized

    @staticmethod
    def _path_to_url_template(path: str) -> str:
        """将 URL 路径转换为 url_template（用 {id} 占位符）。

        替换最后一个数字序列为 {id}（详情页 ID）。
        例: /voddetail/227275.html  → /voddetail/{id}.html
            /artdetail-38385.html → /artdetail-{id}.html
        """
        import re
        # 替换最后一个数字序列为 {id}
        return re.sub(r'\d+(?=[^/]*$)', '{id}', path)

    def _detect_site_type(self) -> str:
        """从录制数据的 URL 模式检测站点类型。"""
        paths = [urlparse(s.url).path for s in self.rec.steps]

        # MacCMS 特征：/vodshow/ + /voddetail/ + /vodplay/
        has_vodshow = any("/vodshow/" in p for p in paths)
        has_voddetail = any("/voddetail/" in p for p in paths)
        has_vodplay = any("/vodplay/" in p for p in paths)
        if has_vodshow and (has_voddetail or has_vodplay):
            return "maccms"

        # WordPress 特征：/wp-content/ + /category/
        has_wp = any("/wp-content/" in p for p in paths)
        has_cat = any("/category/" in p for p in paths)
        if has_wp and has_cat:
            return "wordpress"

        return ""  # 未知类型

    def _infer_crawl_pattern_from_recording(self) -> dict:
        """从录制数据推断链式操作路径（未知类型时使用）。"""
        chains = {}
        chain_order = []
        chain_count = 0

        for i, step in enumerate(self.rec.steps):
            url_path = urlparse(step.url).path

            if step.m3u8_urls or step.mp4_urls:
                # 有流 → 最后一条链是 stream_capture
                if "/play/" in url_path or "/vodplay/" in url_path:
                    wait_sel = "video, iframe[src], .player"
                else:
                    wait_sel = ".player, video, iframe[src]"

                chains["stream_capture"] = {
                    "steps": [
                        {"action": "navigate", "url_template": self._path_to_url_template(url_path)},
                        {"action": "smart_wait", "selector": wait_sel},
                        {"action": "network_capture", "filter": ".m3u8,.mp4,.flv", "wait_seconds": 5},
                    ]
                }
                chain_order.append("stream_capture")
                break
            else:
                # 无流 → 中间链
                is_last_step = (i == len(self.rec.steps) - 1)

                # 图片分组的最后一步 → 网络图片捕获（不是 extract_links）
                if is_last_step and self.resource_type == "art" and chain_count > 0:
                    nav_template = self._path_to_url_template(url_path)
                    chains["level_1"] = {
                        "steps": [
                            {"action": "navigate", "url_template": nav_template},
                            {"action": "smart_wait", "selector": "img[src], .art-content, .content, .pic"},
                            {"action": "network_capture", "filter": ".jpg,.jpeg,.png,.webp,.gif",
                             "wait_seconds": 3},
                        ]
                    }
                    chain_order.append("level_1")
                    break

                chain_name = "list_crawl" if chain_count == 0 else f"level_{chain_count}"
                # list_crawl 不需要 url_template（用入口 URL）
                # level_N 需要 url_template 构造详情页 URL
                nav_template = "" if chain_count == 0 else self._path_to_url_template(url_path)
                wait_sel = self._infer_selector_from_path(url_path)

                # 根据 resource_type 确定 link_type
                if self.resource_type == "art":
                    link_type = "art_detail"
                elif self.resource_type == "video":
                    link_type = "video_detail"
                else:
                    link_type = "next_level"

                chains[chain_name] = {
                    "steps": [
                        {"action": "navigate", "url_template": nav_template},
                        {"action": "smart_wait", "selector": wait_sel},
                        {"action": "extract_links", "source": "markdown", "link_type": link_type},
                    ]
                }
                if chain_count == 0:
                    chains[chain_name]["pagination"] = {
                        "methods": ["button_click", "url_construct"],
                        "max_pages": 100,
                    }
                chain_order.append(chain_name)
                chain_count += 1

        if not chains:
            return {}

        result = {}
        for name in chain_order:
            result[name] = chains[name]
        return result

    def _infer_selector_from_path(self, path: str) -> str:
        """从 URL 路径推断合适的 wait selector。"""
        if "/vodshow/" in path or "/vodtype/" in path:
            return "a[href*='/voddetail/'], .vodlist-item, .stui-vodlist__box"
        if "/voddetail/" in path or "/detail/" in path:
            return "a[href*='/vodplay/'], .playlist, .stui-vodlist__play"
        if "/vodplay/" in path or "/play/" in path:
            return "video, iframe[src], .player"
        if "/category/" in path:
            return "a[href*='/detail/'], .item, .card"
        return "a[href], .item, article, main"


# ── 主入口 ───────────────────────────────────────────────


def main():
    import argparse
    ap = argparse.ArgumentParser(description="HAR 配置向导 — 自动生成 sites.yaml")
    ap.add_argument("--url", "-u", help="起始 URL")
    ap.add_argument("--site", "-s", help="站点名称（用于配置 key）")
    ap.add_argument("--session", default="har_wizard", help="browser-act 会话名")
    ap.add_argument("--output", "-o", help="输出 YAML 文件路径")

    args = ap.parse_args()

    client = BrowserActClient(session=args.session, browser_id=None)

    start_url = args.url
    if not start_url:
        start_url = input("请输入起始 URL: ").strip()
    if not start_url:
        _log.warning("未提供 URL，退出")
        print("未提供 URL，退出")
        return

    site_key = args.site or urlparse(start_url).netloc.replace(".", "_")

    wizard = HarWizard(client)
    config = wizard.run_interactive(start_url)

    # 添加 network_first 标记
    config["network_first"] = True

    # 输出 YAML
    yaml_content = {site_key: config}
    yaml_str = yaml.dump({"sites": yaml_content}, allow_unicode=True, default_flow_style=False, sort_keys=False)

    _log.info("配置生成完成: site_key=%s", site_key)
    print(f"\n{'='*60}")
    print(f"  生成的 sites.yaml 配置:")
    print(f"{'='*60}")
    print(yaml_str)

    # 保存
    output_path = args.output or str(Path(__file__).parent.parent / "sites_generated.yaml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 自动生成的站点配置 — HAR 配置向导\n")
        f.write(yaml_str)
    _log.info("配置已保存: path=%s", output_path)
    print(f"\n  已保存到: {output_path}")


if __name__ == "__main__":
    main()
