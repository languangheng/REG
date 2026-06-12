"""站点管理 UI - Flask 本地 Web 服务（UI 1）

启动: python site_manager.py
访问: http://localhost:5050
"""

import json
import os
import sys
import io
import threading
import subprocess

from flask import Flask, render_template, jsonify, request, Response

from crawler.logger import get_logger

log = get_logger("site_manager")

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_JSON = os.path.join(BASE_DIR, "sites.json")


# ── 工具 ──────────────────────────────────────────────

def load_sites() -> list:
    """读取站点列表（供 UI 展示，支持分组格式）。"""
    if not os.path.isfile(SITES_JSON):
        return []
    with open(SITES_JSON, "r", encoding="utf-8") as f:
        raw = json.load(f)
    sites = raw.get("sites", {})
    result = []
    for key, val in sites.items():
        # 分组信息
        groups = []
        for g in val.get("groups", []):
            chains_raw = g.get("extract_chains", {})
            chain_names = list(chains_raw.keys()) if isinstance(chains_raw, dict) else []
            groups.append({
                "name": g.get("name", ""),
                "resource_type": g.get("resource_type", ""),
                "entry_points": g.get("entry_points", []),
                "extract_chains": chain_names,
            })

        # 兼容旧格式（无 groups 字段）
        if not groups:
            chains_raw = val.get("extract_chains", {})
            chain_names = list(chains_raw.keys()) if isinstance(chains_raw, dict) else []
            groups.append({
                "name": "默认分组",
                "resource_type": "video",
                "entry_points": val.get("entry_points", []),
                "extract_chains": chain_names,
            })

        result.append({
            "key": key,
            "name": val.get("name", key),
            "base_url": val.get("base_url", ""),
            "groups": groups,
        })
    return result


def read_sites_raw() -> dict:
    """读取完整站点配置（原始 dict）。"""
    if not os.path.isfile(SITES_JSON):
        return {}
    with open(SITES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sites(raw: dict):
    """写入站点配置（完整 dict）。"""
    with open(SITES_JSON, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


# ── 路由 ──────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sites", methods=["GET"])
def api_list_sites():
    return jsonify(load_sites())


@app.route("/api/sites/<key>", methods=["DELETE"])
def api_delete_site(key: str):
    raw = read_sites_raw()
    if "sites" in raw and key in raw["sites"]:
        del raw["sites"][key]
        save_sites(raw)
    return jsonify({"ok": True})


@app.route("/api/wizard/start", methods=["POST"])
def api_wizard_start():
    data = request.get_json(force=True)
    key = data.get("key", "").strip()
    name = data.get("name", "").strip()
    base_url = data.get("base_url", "").strip()
    entry = data.get("entry", "").strip() or base_url

    if not key or not name or not base_url:
        return jsonify({"ok": False, "error": "参数不完整"}), 400

    def run_wizard():
        from crawler.config_wizard import run_wizard
        run_wizard(key, name, base_url, entry)

    t = threading.Thread(target=run_wizard, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/crawl/<key>", methods=["GET"])
def api_crawl(key: str):
    """SSE 实时返回爬取进度（调用分组爬虫）。"""
    log.info("收到爬取请求: site=%s", key)

    raw = read_sites_raw()
    sites = raw.get("sites", {})
    if key not in sites:
        log.error("站点不存在: %s", key)
        return jsonify({"error": "site not found"}), 404

    site_config = sites[key]
    log.info("站点配置: name=%s, base_url=%s, groups=%d",
             site_config.get("name", ""), site_config.get("base_url", ""),
             len(site_config.get("groups", [])))

    def generate():
        # SSE 每行格式: data: <json>\n\n
        msg = json.dumps({"msg": f"开始爬取 {key}（分组模式）...", "type": "info"}, ensure_ascii=False)
        yield f"data: {msg}\n\n"

        # 调用分组爬虫（使用 -m 方式，确保 crawler 包可被导入）
        # 复用已有浏览器（与其他端点共享同一个 browser_id）
        browser_id = "direct_local_100797252049567848"
        cmd = [
            sys.executable,
            "-m", "crawler.group_crawler",
            "--site", key,
            "--deep",
            "--deep-limit", "0",
            "--wait", "4",
            "--max-pages", "50",
            "--browser-id", browser_id,
            "--output-dir", os.path.join(BASE_DIR, "output"),
        ]
        log.info("启动爬取子进程: cmd=%s", " ".join(cmd))

        # 显式设置 PYTHONPATH，确保 crawler 包可被导入
        import os as _os
        env = _os.environ.copy()
        env["PYTHONPATH"] = BASE_DIR + _os.pathsep + env.get("PYTHONPATH", "")
        # 强制子进程 stdout/stderr 用 UTF-8，避免 Windows GBK 控制台 emoji 编码崩溃
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR,
            env=env,
        )
        log.info("子进程已启动: pid=%d", proc.pid)
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            # 解析 [EVENT] 结构化事件
            if line.startswith("[EVENT] "):
                try:
                    event_data = json.loads(line[len("[EVENT] "):])
                    log.debug("SSE事件: %s", event_data.get("event", ""))
                    event_json = json.dumps(event_data, ensure_ascii=False)
                    yield f"data: {event_json}\n\n"
                except json.JSONDecodeError:
                    log.warning("SSE事件解析失败: %s", line[:100])
                    msg = json.dumps({"msg": line, "type": "event_err"}, ensure_ascii=False)
                    yield f"data: {msg}\n\n"
                continue

            # 普通日志行
            ltype = ""
            if "✅" in line or "OK" in line or "saved" in line.lower() or "导出" in line:
                ltype = "ok"
            elif "❌" in line or "error" in line.lower() or "失败" in line:
                ltype = "err"
                log.error("[子进程] %s", line)
            else:
                log.debug("[子进程] %s", line)
            msg = json.dumps({"msg": line, "type": ltype}, ensure_ascii=False)
            yield f"data: {msg}\n\n"

        ret = proc.wait()
        log.info("子进程退出: pid=%d, returncode=%d", proc.pid, ret)
        if ret != 0:
            log.error("子进程异常退出: pid=%d, returncode=%d", proc.pid, ret)
        msg = json.dumps({"msg": "爬取完成", "type": "ok", "done": True}, ensure_ascii=False)
        yield f"data: {msg}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ── HAR 录制向导 API ─────────────────────────────────

_har_wizard = None  # HarWizard 实例
_har_client = None   # BrowserActClient 实例
_har_events = []     # 事件队列
_har_subscribers = [] # SSE 订阅者


def _har_broadcast(event: dict):
    """向所有 SSE 订阅者广播事件。"""
    _har_events.append(event)
    data = json.dumps(event, ensure_ascii=False)
    for q in _har_subscribers:
        q.put(data)


@app.route("/wizard_har")
def wizard_har_page():
    return render_template("wizard_har.html")


@app.route("/api/har/start", methods=["POST"])
def api_har_start():
    global _har_wizard, _har_client

    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    log.info("HAR录制启动请求: url=%s", url)
    # URL 可以为空（复用已有会话时不需要 URL）

    try:
        from crawler.browser_act import BrowserActClient
        from crawler.config_wizard_har import HarWizard

        # 复用已有浏览器会话，避免触发 CF 验证
        _har_client = BrowserActClient(session="har_wizard", browser_id="direct_local_100797252049567848")
        _har_wizard = HarWizard(_har_client)
        _har_wizard.start(start_url=url, reuse_session=True)
        log.info("HAR录制启动成功")

        # 后台轮询收集数据（stop 时一次性取出）
        import threading

        def poll_loop():
            import time as _t
            while _har_wizard and _har_wizard._running:
                _har_wizard.poll()
                _t.sleep(2)

        t = threading.Thread(target=poll_loop, daemon=True)
        t.start()

        return jsonify({"ok": True})
    except Exception as e:
        log.error("HAR录制启动失败: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/har/events")
def api_har_events():
    """SSE 端点：实时推送录制事件。"""
    import queue

    q = queue.Queue()
    _har_subscribers.append(q)

    def generate():
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            _har_subscribers.remove(q)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/har/stop", methods=["POST"])
def api_har_stop():
    global _har_wizard
    if not _har_wizard:
        log.warning("HAR停止录制请求: 未在录制")
        return jsonify({"ok": False, "error": "未在录制"})

    try:
        har_path = _har_wizard.stop()
        log.info("HAR录制停止: har_path=%s", har_path)
        # 构建 summary
        rec = _har_wizard.recording
        steps = []
        all_streams = []
        all_images = []
        all_apis = []
        for s in rec.steps:
            steps.append({
                "url": s.url, "title": s.title,
                "m3u8_count": len(s.m3u8_urls), "mp4_count": len(s.mp4_urls),
                "api_count": len(s.api_urls), "img_count": len(s.image_urls),
            })
            for u in s.m3u8_urls:
                all_streams.append({"format": "m3u8", "url": u})
            for u in s.mp4_urls:
                all_streams.append({"format": "mp4", "url": u})
            all_images.extend(s.image_urls)
            all_apis.extend(s.api_urls)
        # 去重
        seen_img = set(); all_images = [u for u in all_images if not (u in seen_img or seen_img.add(u))]
        seen_api = set(); all_apis = [u for u in all_apis if not (u in seen_api or seen_api.add(u))]

        return jsonify({"ok": True, "har_path": har_path, "summary": {
            "steps": steps, "streams": all_streams,
            "images": all_images, "apis": all_apis,
        }})
    except Exception as e:
        log.error("HAR停止失败: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/har/generate", methods=["POST"])
def api_har_generate():
    global _har_wizard
    if not _har_wizard or not _har_wizard.recording.steps:
        log.warning("生成配置失败: 没有录制数据")
        return jsonify({"ok": False, "error": "没有录制数据"})

    try:
        from crawler.config_wizard_har import ConfigGenerator

        data = request.get_json(force=True) if request.is_json else {}
        group_name = data.get("group_name", "").strip()
        resource_type = data.get("resource_type", "video").strip()
        log.info("生成配置: group_name=%s, resource_type=%s", group_name, resource_type)

        gen = ConfigGenerator(_har_wizard.recording,
                              group_name=group_name,
                              resource_type=resource_type)
        config = gen.generate()

        site_key = _har_wizard.recording.site_name.replace(".", "_")

        # 保存到 sites.json
        raw = read_sites_raw()
        if "sites" not in raw:
            raw["sites"] = {}
        raw["sites"][site_key] = config
        save_sites(raw)

        # JSON 格式展示（供 UI 预览）
        config_json_str = json.dumps(config, ensure_ascii=False, indent=2)

        log.info("配置生成成功: site_key=%s, config_path=%s", site_key, SITES_JSON)
        return jsonify({"ok": True, "config_path": SITES_JSON, "json": config_json_str, "site_key": site_key})
    except Exception as e:
        log.error("配置生成失败: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/sites/<key>/groups/<group_name>/entries", methods=["POST"])
def api_add_entry(key: str, group_name: str):
    """向指定分组添加同模式入口 URL。"""
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    entry_name = data.get("name", "").strip()

    if not url:
        return jsonify({"ok": False, "error": "URL 不能为空"}), 400

    raw = read_sites_raw()
    sites = raw.get("sites", {})
    if key not in sites:
        return jsonify({"ok": False, "error": f"站点 {key} 不存在"}), 404

    site = sites[key]
    groups = site.get("groups", [])

    # 查找目标分组
    target = None
    for g in groups:
        if g.get("name") == group_name:
            target = g
            break

    if not target:
        return jsonify({"ok": False, "error": f"分组 '{group_name}' 不存在"}), 404

    # 添加入口
    entry_points = target.get("entry_points", [])
    new_entry = {"name": entry_name or f"入口{len(entry_points) + 1}", "url": url, "type": target.get("resource_type", "video")}
    entry_points.append(new_entry)
    target["entry_points"] = entry_points

    save_sites(raw)
    return jsonify({"ok": True, "entry": new_entry})


# ── Auto Analyze API ────────────────────────────────

_analyze_result_cache = {}  # url -> {config, json_str}


@app.route("/api/analyze")
def api_analyze():
    """SSE: 输入 URL 自动分析，实时返回日志。"""
    url = request.args.get("url", "").strip()
    is_homepage = request.args.get("is_homepage", "true").lower() in ("true", "1", "yes")
    if not url:
        return jsonify({"error": "missing url"}), 400

    def generate():
        import queue
        import time as _time
        from crawler.browser_act import BrowserActClient
        from crawler.auto_config import auto_config_multi

        client = BrowserActClient(session="auto_analyze", browser_id="direct_local_100797252049567848")

        q = queue.Queue()
        result_holder = [None]

        def on_log(line):
            """实时日志回调，将日志推入队列。"""
            ltype = ""
            if "✅" in line:
                ltype = "ok"
            elif "❌" in line or "⚠️" in line:
                ltype = "err"
            elif line.startswith("["):
                ltype = "info"
            q.put({"msg": line, "type": ltype})

        def run():
            try:
                result = auto_config_multi(url=url, client=client, on_log=on_log, is_homepage=is_homepage)
                result_holder[0] = result
            except Exception as e:
                result_holder[0] = e
            finally:
                q.put(None)  # sentinel: done

        t = threading.Thread(target=run, daemon=True)
        t.start()

        # 实时推送日志
        while True:
            try:
                item = q.get(timeout=30)
                if item is None:
                    break
                msg = json.dumps(item, ensure_ascii=False)
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"

        result = result_holder[0]
        if isinstance(result, Exception):
            msg = json.dumps({"msg": f"❌ 分析失败: {result}", "type": "err", "done": True, "success": False}, ensure_ascii=False)
            yield f"data: {msg}\n\n"
            return

        if result.success and result.config:
            config_json_str = json.dumps(result.config, ensure_ascii=False, indent=2)
            cache_key = (url, is_homepage)
            _analyze_result_cache[cache_key] = {"config": result.config, "json_str": config_json_str}
            msg = json.dumps({"done": True, "success": True, "config": result.config, "json": config_json_str, "is_homepage": is_homepage}, ensure_ascii=False)
        else:
            msg = json.dumps({"done": True, "success": False}, ensure_ascii=False)
        yield f"data: {msg}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/analyze/save", methods=["POST"])
def api_analyze_save():
    """保存自动分析结果到 sites.json。"""
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    is_homepage = data.get("is_homepage", True)
    cache_key = (url, is_homepage)
    cached = _analyze_result_cache.get(cache_key)
    if not cached:
        return jsonify({"ok": False, "error": "没有缓存的分析结果，请重新分析"}), 400

    config = cached["config"]
    site_key = config.get("name", url.replace("https://", "").replace("http://", "").split("/")[0].replace(".", "_"))

    # 将旧格式配置转换为分组格式
    if "groups" not in config:
        group = {
            "name": "默认分组",
            "resource_type": "video",  # auto_config 默认视频
        }
        # 提取分组级字段
        for field_name in ("entry_points", "link_patterns", "extract_chains", "pagination"):
            if field_name in config:
                group[field_name] = config.pop(field_name)
        config["groups"] = [group]
        # 移除旧的顶层字段
        config.pop("network_first", None)
        config.pop("_extra_categories", None)

    raw = read_sites_raw()
    if "sites" not in raw:
        raw["sites"] = {}
    raw["sites"][site_key] = config
    save_sites(raw)

    return jsonify({"ok": True})


if __name__ == "__main__":
    log.info("站点管理 UI 启动: host=127.0.0.1, port=5050")
    print("站点管理 UI 启动中...")
    print("请访问: http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)
