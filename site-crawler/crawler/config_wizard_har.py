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
        if not reuse_session and start_url:
            self.client.navigate(start_url)
            time.sleep(3)
        else:
            # 确保有活跃会话 — navigate 到当前页即可
            try:
                snapshot = self.client.parsed_state()
            except Exception:
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
            return f"HAR 已保存: {har_path}\n{result}"
        except Exception as e:
            return f"HAR 保存失败: {e}"

    def run_interactive(self, start_url: str) -> dict:
        """交互式录制：Python 控制台引导用户操作。"""
        print(self.start(start_url))

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
            print("\n录制中断")

        har_result = self.stop()
        print(har_result)

        # 生成配置
        config = self.generate_config()
        return config

    def _print_status(self):
        """打印当前录制状态。"""
        print(f"\n{'='*50}")
        print(f"  录制状态: {'进行中' if self._running else '已停止'}")
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
    """从录制会话生成 sites.yaml 配置。"""

    def __init__(self, recording: RecordingSession):
        self.rec = recording

    def generate(self) -> dict:
        """生成站点配置字典。"""
        config = {
            "name": self.rec.site_name,
            "base_url": self.rec.base_url,
            "link_patterns": self._generate_link_patterns(),
            "extract_chains": self._generate_extract_chains(),
            "entry_points": self._generate_entry_points(),
        }
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
        for i, step in enumerate(self.rec.steps):
            if step.m3u8_urls or step.mp4_urls:
                # 当前步骤是播放页，上一步可能是详情页
                if i > 0:
                    prev_path = urlparse(self.rec.steps[i-1].url).path
                    video_detail_paths.add(self._generalize_path(prev_path))
                # 也可能是自己（详情页内嵌播放）
                cur_path = urlparse(step.url).path
                if not any(kw in cur_path for kw in ["/play/", "/vodplay/"]):
                    video_detail_paths.add(self._generalize_path(cur_path))

        for pattern in video_detail_paths:
            if pattern and pattern != "/":
                video_detail.append(pattern)

        # 排除模式：列表页、搜索页等
        list_keywords = ["/vodshow/", "/vodtype/", "/vodsearch/", "/topic/", "/tag/", "/static/"]
        for path in paths:
            gen = self._generalize_path(path)
            if any(kw in path for kw in list_keywords) and gen not in exclude:
                exclude.append(gen)

        # 如果没推断出来，给个默认
        if not video_detail:
            for path in paths:
                if re.search(r'/\d+', path) and "/play" not in path and "/vodshow" not in path:
                    video_detail.append(self._generalize_path(path))
                    break

        return {
            "video_detail": video_detail or ["/voddetail/\\d+"],
            "art_detail": art_detail,
            "exclude": exclude or ["/vodshow/", "/vodtype/", "/vodsearch/", "/static/"],
        }

    def _generate_extract_chains(self) -> dict:
        """从录制数据生成 extract_chains。"""
        chains = {}

        # 视频链
        if any(s.m3u8_urls or s.mp4_urls for s in self.rec.steps):
            chains["video"] = self._generate_video_chain()

        # 图片链
        if any(s.image_urls for s in self.rec.steps):
            chains["art"] = self._generate_art_chain()

        return chains

    def _generate_video_chain(self) -> dict:
        """生成视频提取链。"""
        # 找到播放页的路径模式
        play_paths = []
        detail_paths = []
        for step in self.rec.steps:
            path = urlparse(step.url).path
            if step.m3u8_urls or step.mp4_urls:
                play_paths.append(path)
            elif any(kw in path for kw in ["/voddetail/", "/detail/"]):
                detail_paths.append(path)

        # 生成 extract_js
        # 详情页：提取播放链接
        detail_js = """JSON.stringify([...document.querySelectorAll('a')].filter(a => {
  const href = a.href || '';
  return href.includes('/vodplay/') || href.includes('/play/');
}).map(a => ({
  href: a.href,
  text: a.textContent.trim().substring(0, 50),
  class: a.className
})).filter(a => a.href))"""

        # 播放页：提取流地址（用 iframe 方式，network requests 是运行时方案）
        play_js = """JSON.stringify((() => {
  const iframes = [...document.querySelectorAll('iframe')];
  for (const f of iframes) {
    const src = f.src || '';
    if (!src) continue;
    try {
      const url = new URL(src);
      const videoUrl = url.searchParams.get('url');
      if (videoUrl && (videoUrl.includes('.m3u8') || videoUrl.includes('.mp4') || videoUrl.includes('.flv'))) {
        return {player_iframe: src, stream_url: videoUrl};
      }
    } catch(e) {}
  }
  return {player_iframe: null, stream_url: null};
})())"""

        # 检测是否需要中间步骤（详情页 → 播放页）
        has_detail = bool(detail_paths)

        steps = []
        if has_detail:
            steps.append({"name": "detail", "extract_js": detail_js})
        steps.append({"name": "play", "extract_js": play_js})

        return {"steps": steps}

    def _generate_art_chain(self) -> dict:
        """生成图片提取链。"""
        art_js = """JSON.stringify((() => {
  const container = document.getElementById('read_tpc') || document.body;
  return [...container.querySelectorAll('img')]
    .map(img => img.src || img.dataset.src || img.dataset.original || '')
    .filter(s => s && !s.startsWith('data:'));
})())"""

        return {
            "steps": [
                {"name": "detail", "extract_js": art_js}
            ]
        }

    def _generate_entry_points(self) -> list[dict]:
        """从第一步生成入口点。"""
        if not self.rec.steps:
            return []

        first_url = self.rec.steps[0].url
        first_title = self.rec.steps[0].title or "入口"

        # 检测是否有流地址 → video 类型
        has_video = any(s.m3u8_urls or s.mp4_urls for s in self.rec.steps)
        entry_type = "video" if has_video else "art"

        return [
            {"name": first_title.split("-")[0].strip()[:20] or "入口", "url": first_url, "type": entry_type}
        ]

    @staticmethod
    def _generalize_path(path: str) -> str:
        """将 URL 路径泛化为正则模式。

        策略：保留第一个数字段（分类 ID）和文件后缀，中间所有内容（无论多少字符）替换为 \\d+。
        例: /voddetail/227275.html      → /voddetail/227275\\d+\\.html
            /vodshow/12--------2---.html → /vodshow/12\\d+\\.html
            /vodtype/3-6.html            → /vodtype/3\\d+\\.html
        """
        # 1. 找第一个数字段（分类 ID）
        m_cat = re.match(r'^/([^/]*?)(\d+)', path)
        if not m_cat:
            return re.sub(r'\d+', lambda _: r'\d+', path)

        prefix = m_cat.group(1)  # '/' 或 '/vodshow/'
        cat_id = m_cat.group(2)  # '12'
        after_cat = path[m_cat.end():]  # '--------2---.html'

        # 2. 找文件后缀（.html, .php 等）
        suffix_m = re.search(r'(\.[^/]+)$', after_cat)  # '.html'
        if suffix_m:
            suffix = suffix_m.group(1)  # '.html'
            middle_raw = after_cat[:suffix_m.start()]  # '--------2---'
        else:
            suffix = ''
            middle_raw = after_cat

        # 3. middle_raw 整体替换为 \\d+，不论内容是什么
        #    （包含分类分隔符 + 页码 + 其他字符，统一泛化）
        return f"{prefix}{cat_id}\\d+{suffix}"


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

    print(f"\n{'='*60}")
    print(f"  生成的 sites.yaml 配置:")
    print(f"{'='*60}")
    print(yaml_str)

    # 保存
    output_path = args.output or str(Path(__file__).parent.parent / "sites_generated.yaml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 自动生成的站点配置 — HAR 配置向导\n")
        f.write(yaml_str)
    print(f"\n  已保存到: {output_path}")


if __name__ == "__main__":
    main()
