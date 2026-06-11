"""配置向导 - 注入覆盖层的交互式配置生成器（UI 2）

调用方式:
    from crawler.config_wizard import run_wizard
    run_wizard(key, name, base_url, entry_url)
"""

import json
import os
import sys
import io
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_JSON = os.path.join(BASE_DIR, "..", "sites.json")


# ── 覆盖层 HTML/JS ──────────────────────────────────

OVERLAY_JS = r"""
(() => {
  // Already injected, skip
  if (window.__crawler_wizard) return;
  window.__crawler_wizard = true;

  // Restore state from sessionStorage (survives page navigation)
  let __restored = false;
  try {
    const __saved = sessionStorage.getItem('cw_state');
    if (__saved) {
      const __parsed = JSON.parse(__saved);
      // state is defined below, we'll merge after it's created
      window.__cw_restored_state = __parsed;
      __restored = true;
      console.log('[wizard] State found in sessionStorage');
    }
  } catch(e) { console.error('[wizard] Restore error:', e); }

  // ── Styles ──
  const style = document.createElement('style');
  style.textContent = `
    #cw-overlay {
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      z-index: 2147483647; pointer-events: none; font-family: system-ui, sans-serif;
    }
    #cw-panel {
      pointer-events: auto; position: fixed; top: 12px; left: 12px;
      background: #1a1d27; border: 1px solid #6366f1; border-radius: 10px;
      padding: 14px 18px; min-width: 280px; color: #e5e7eb; font-size: 13px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.5); user-select: none;
    }
    #cw-panel h3 { margin: 0 0 8px 0; font-size: 14px; color: #a5b4fc; }
    #cw-panel .step { color: #9ca3af; margin-bottom: 10px; }
    #cw-panel .btn {
      display: inline-block; padding: 6px 14px; border-radius: 5px;
      border: none; cursor: pointer; font-size: 12px; margin-right: 6px;
    }
    #cw-panel .btn-primary { background: #6366f1; color: #fff; }
    #cw-panel .btn-primary:hover { background: #818cf8; }
    #cw-panel .btn-ghost { background: transparent; border: 1px solid #374151; color: #d1d5db; }
    #cw-panel .btn-ghost:hover { background: #1f2937; }
    #cw-panel .btn-danger { background: #dc2626; color: #fff; }
    #cw-panel .log { background: #0f1117; border: 1px solid #1f2937; border-radius: 4px; padding: 6px 8px; max-height: 120px; overflow-y: auto; font-size: 11px; color: #6b7280; margin-top: 8px; }
    #cw-panel .log .ok { color: #4ade80; }
    #cw-panel .log .err { color: #f87171; }
    .cw-highlight {
      outline: 3px solid #6366f1 !important; outline-offset: 2px !important;
      cursor: pointer !important; transition: outline 0.2s;
    }
    .cw-highlight:hover { outline-color: #a5b4fc !important; }
  `;
  document.head.appendChild(style);

  // ── Panel ──
  const overlay = document.createElement('div');
  overlay.id = 'cw-overlay';
  overlay.innerHTML = `
    <div id="cw-panel">
      <h3>🔧 Config Wizard</h3>
      <div class="step" id="cw-step">Initializing...</div>
      <div id="cw-actions"></div>
      <div class="log" id="cw-log"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  const stepEl = document.getElementById('cw-step');
  const actionsEl = document.getElementById('cw-actions');
  const logEl = document.getElementById('cw-log');

  function log(msg, cls='') {
    const d = document.createElement('div');
    d.className = cls;
    d.textContent = msg;
    logEl.appendChild(d);
    logEl.scrollTop = logEl.scrollHeight;
    console.log('[wizard]', msg);
  }

  function setStep(text) { stepEl.textContent = text; }
  function setActions(buttons) {
    actionsEl.innerHTML = '';
    buttons.forEach(b => {
      const btn = document.createElement('button');
      btn.className = 'btn ' + (b.cls || 'btn-primary');
      btn.textContent = b.label;
      btn.onclick = b.fn;
      actionsEl.appendChild(btn);
    });
  }

  // ── State ──
  let state = {
    stage: 'init',        // init | select_link | choose_type | detail | select_play | stream_found | done
    link_type: null,       // 'video' or 'image'
    selected_link: null,     // {href, text, selector}
    detail_url: null,
    play_link: null,
    stream_url: null,
    link_selector: null,    // similarlink' CSS selector
    config: { link_patterns: {video_detail:[], art_detail:[], exclude:[]}, extract_chains: {} }
  };
  window.__cw_state = state;

  // Merge restored state (from sessionStorage)
  if (window.__cw_restored_state) {
    Object.assign(state, window.__cw_restored_state);
    console.log('[wizard] State restored, stage:', state.stage);
    window.__cw_restored_state = null;
  }

  // Save state before navigation
  function saveState() {
    try {
      sessionStorage.setItem('cw_state', JSON.stringify(state));
    } catch(e) { console.error('[wizard] State save error:', e); }
  }
  window.__cw_saveState = saveState;

  // Auto-save on page unload (natural link clicks)
  window.addEventListener('beforeunload', () => saveState());

  // ── Util: generate CSS selector ──
  function getSelector(el) {
    if (el.id) return '#' + el.id;
    let path = [];
    let cur = el;
    while (cur && cur !== document.body) {
      let sel = cur.tagName.toLowerCase();
      if (cur.className && typeof cur.className === 'string') {
        const cls = cur.className.trim().split(/\s+/)[0];
        if (cls) sel += '.' + cls;
      }
      const parent = cur.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter(c => c.tagName === cur.tagName);
        if (siblings.length > 1) sel += `:nth-child(${[...parent.children].indexOf(cur)+1})`;
      }
      path.unshift(sel);
      cur = cur.parentElement;
      if (path.length > 4) break;
    }
    return path.join(' > ');
  }

  // ── Util: URL to regex pattern ──
  function urlToPattern(url) {
    const u = new URL(url);
    let path = u.pathname;
    // Replace numeric parts with regex
    path = path.replace(/\/\d+(?=\/|\.|$)/g, '/\\d+');
    path = path.replace(/\d+(?=\.html?)/, '\\d+');
    // escape
    path = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return path;
  }

  // ── Stage: init -> wait for user link selection ──
  function startSelectLink() {
    state.stage = 'select_link';
    setStep('Click a content link on the page (video or image)');
    setActions([
      { label: 'Cancel', cls: 'btn-ghost', fn: () => { log('Cancel'); startSelectLink(); } }
    ]);
    log('Selection mode active, click a link...');

    // Highlight all links
    document.querySelectorAll('a[href]').forEach(a => {
      a.classList.add('cw-highlight');
      a.addEventListener('click', onLinkClick, true);
    });
  }

  function onLinkClick(e) {
    if (state.stage !== 'select_link') return;
    e.preventDefault();
    e.stopPropagation();

    const a = e.currentTarget;
    state.selected_link = { href: a.href, text: a.textContent.trim().substring(0,80), selector: getSelector(a) };
    log(`Selected: ${a.textContent.trim().substring(0,40)}`);
    log(`URL: ${a.href}`);
    // Clear highlights
    document.querySelectorAll('.cw-highlight').forEach(el => {
      el.classList.remove('cw-highlight');
      el.removeEventListener('click', onLinkClick, true);
    });

    // Auto-detect type from URL
    const href = a.href;
    if (href.includes('/vodplay/') || href.includes('/play/') || href.includes('/video/')) {
      state.link_type = 'video';
      log('Auto-detected: video content');
    } else if (href.includes('/voddetail/') || href.includes('/detail/') || href.includes('/art/')) {
      state.link_type = 'video';  // Detail page, still video flow
      log('Auto-detected: video detail page');
    } else if (/\.(jpg|png|gif|webp)/i.test(href)) {
      state.link_type = 'image';
      log('Auto-detected: image content');
    } else {
      state.link_type = 'video';  // Default to video
      log('Default: video content');
    }

    // Navigate directly
    proceedToDetail();
  }

  function proceedToDetail() {
    const type = state.link_type;
    const pattern = urlToPattern(state.selected_link.href);
    if (type === 'video') {
      state.config.link_patterns.video_detail.push(pattern);
    } else {
      state.config.link_patterns.art_detail.push(pattern);
    }
    state.link_selector = state.selected_link.selector;
    log(`CSS selector: ${state.link_selector}`);
    log(`URL regex: ${pattern}`);

    state.stage = 'navigating';
    setStep(`Navigating to detail page...`);
    setActions([]);
    log(`Navigate to: ${state.selected_link.href}`);
    saveState();
    window.location.href = state.selected_link.href;
  }



  // ── Listen for page load (detail page)──
  let pageReady = false;
  function onPageLoad() {
    if (pageReady) return;
    pageReady = true;
    if (state.stage === 'navigating') {
      // Arrived at detail page
      state.detail_url = window.location.href;
      if (state.link_type === 'video') {
        setStep('Click Play / Watch Now button on this page/link');
        setActions([
          { label: 'Clicked Play', cls: 'btn-primary', fn: onPlaySelected },
          { label: 'Skip', cls: 'btn-ghost', fn: skipPlayStep },
        ]);
        // Highlight links with play text
        document.querySelectorAll('a').forEach(a => {
          const t = a.textContent.trim();
          if (t.includes('play') || t.includes('Play') || t.includes('HD') || t.includes('play')) {
            a.classList.add('cw-highlight');
          }
        });
        state.stage = 'select_play';
        log('Detail page loaded, click play link');
      } else if (state.stage === 'play_navigating') {
      // Arrived at player page
      setStep('Extracting stream URL...');
      setActions([
        { label: 'Confirm', cls: 'btn-primary', fn: onStreamFound },
        { label: 'Cancel', cls: 'btn-ghost', fn: () => { log('Cancelled'); startSelectLink(); } }
      ]);
      state.stage = 'stream_found';
      log('Player page loaded, extracting stream URL...');
      extractStreamUrl();
    } else {
        // Image type: extract images
        setStep('Extracting image links...');
        setActions([]);
        extractImageLinks();
      }
    }
  }
  window.addEventListener('load', () => setTimeout(onPageLoad, 500));

  // If document already loaded (re-injection case), trigger immediately
  if (document.readyState === 'complete') {
    setTimeout(onPageLoad, 500);
  }

  // ── playlinkselect ──
  function onPlaySelected() {
    // User clicked play, find player page URL
    // Actually navigated to player, listen for next load
    state.stage = 'play_navigating';
    setStep('Navigating to player page...');
    log('If redirected, waiting for player to load...');
    // Monitor navigation
    let checkCount = 0;
    const checkNav = setInterval(() => {
      checkCount++;
      if (window.location.href !== state.detail_url) {
        clearInterval(checkNav);
        log(`Player page: ${window.location.href}`);
        extractStreamUrl();
      }
      if (checkCount > 60) clearInterval(checkNav);
    }, 500);
  }

  function skipPlayStep() {
    log('Skipped play selection');
    extractStreamUrl();
  }

  // ── Extract stream URL ──
  function extractStreamUrl() {
    setStep('Detecting video stream URL...');
    setActions([]);
    // Scan iframe
    const iframes = [...document.querySelectorAll('iframe')];
    log(`Found ${iframes.length} iframe(s)`);
    for (const f of iframes) {
      const src = f.src || '';
      log(`iframe src: ${src.substring(0,80)}`);
      try {
        const u = new URL(src);
        const videoUrl = u.searchParams.get('url');
        if (videoUrl && (videoUrl.includes('.m3u8') || videoUrl.includes('.mp4'))) {
          state.stream_url = videoUrl;
          state.config.extract_chains.video = {
            steps: [
              { name: 'detail', extract_js: '...' },  // placeholder, replace later
              { name: 'play', extract_js: '...' },
            ]
          };
          log(`✅ Found stream: ${videoUrl}`, 'ok');
          setStep('✅ Video stream found!');
          setActions([
            { label: 'Confirm & Save Config', cls: 'btn-primary', fn: finishWizard },
            { label: 'Reselect', cls: 'btn-ghost', fn: startSelectLink },
          ]);
          return;
        }
      } catch(e) {}
      if (src.includes('.m3u8') || src.includes('.mp4')) {
        state.stream_url = src;
        log(`✅ Found stream: ${src}`, 'ok');
        setStep('✅ Video stream found!');
        setActions([
          { label: 'Confirm & Save Config', cls: 'btn-primary', fn: finishWizard },
          { label: 'Reselect', cls: 'btn-ghost', fn: startSelectLink },
        ]);
        return;
      }
    }
    log('Auto-detect failed, confirm player is loaded', 'err');
    setActions([
      { label: 'Refresh & Retry', cls: 'btn-primary', fn: () => location.reload() },
      { label: 'Skip', cls: 'btn-ghost', fn: finishWizard },
    ]);
  }

  // ── Extract image links ──
  function extractImageLinks() {
    const container = document.querySelector('#read_tpc') || document.body;
    const imgs = [...container.querySelectorAll('img')].map(img =>
      img.src || img.dataset.src || img.dataset.original || ''
    ).filter(Boolean);
    log(`✅ found ${imgs.length} image(s)`);
    state.config.extract_chains.art = { steps: [{ name: 'detail', extract_js: '...' }] };
    setStep(`✅ found ${imgs.length} image(s)`);
    setActions([
      { label: 'Confirm & Save Config', cls: 'btn-primary', fn: finishWizard },
      { label: 'Reselect', cls: 'btn-ghost', fn: startSelectLink },
    ]);
  }

  // ── Finish ──
  function finishWizard() {
    setStep('Config generated, saving...');
    setActions([]);
    // Statesave to window，for Python backend read
    window.__cw_result = {
      link_type: state.link_type,
      link_selector: state.link_selector,
      selected_url: state.selected_link?.href,
      stream_url: state.stream_url,
      config: state.config,
    };
    log('✅ Config saved to window.__cw_result', 'ok');
    log('You can close this window now.', 'ok');
    setStep('✅ Config complete! You can close this window.');
    setActions([
      { label: 'Close Window', cls: 'btn-primary', fn: () => window.close() },
    ]);
  }

  // ── Start / Resume ──
  if (state.stage === 'init') {
    // Fresh start
    setStep('Ready. Click Start to begin.');
    setActions([
      { label: 'Start Select', cls: 'btn-primary', fn: startSelectLink },
      { label: 'Cancel', cls: 'btn-ghost', fn: () => log('Cancel') },
    ]);
    log('Config Wizard ready');
  } else {
    // Resumed state - onPageLoad will handle the rest
    console.log('[wizard] Resumed at stage:', state.stage);
    log('Resuming from: ' + state.stage);
  }
})();
"""


# ── Python 端：驱动向导流程 ──────────────────────────

def run_wizard(key: str, name: str, base_url: str, entry_url: str):
    """Launch the config wizard, open browser and inject overlay."""
    print(f"[wizard] Starting wizard: {key}")
    print(f"[wizard] Entry: {entry_url}")

    from crawler.browser_act import BrowserActClient

    client = BrowserActClient(session=f"wizard_{key}", browser_id=None)

    try:
        # Step 1: open entry page
        print("[wizard] Opening entry page...")
        client.navigate(entry_url)
        client.wait(8)

        # Step 2: inject overlay
        print("[wizard] Injecting config wizard overlay...")
        client.evaluate_js(OVERLAY_JS)
        client.wait(2)

        print("[wizard] Overlay injected. Use the browser panel to complete setup.")
        print("[wizard] Waiting for user to finish (window close or __cw_result)...")

        # Track URL for navigation detection
        def get_url():
            try:
                return client.evaluate_js("window.location.href")
            except Exception:
                return None

        last_url = get_url()

        # Step 3: poll window.__cw_result
        max_wait = 600  # 10 min max
        start = time.time()
        result = None
        while time.time() - start < max_wait:
            # Check for result
            try:
                val = client.evaluate_js("JSON.stringify(window.__cw_result || null)")
                if val and val != "null":
                    result = json.loads(val)
                    print(f"[wizard] Got config result")
                    break
            except Exception:
                pass

            # Check for URL change (navigation)
            current_url = get_url()
            if current_url and last_url and current_url != last_url:
                print(f"[wizard] Navigation detected: {current_url}")
                print("[wizard] Waiting for page load...")
                client.wait(5)
                print("[wizard] Re-injecting overlay...")
                try:
                    client.evaluate_js(OVERLAY_JS)
                    client.wait(2)
                    print("[wizard] Re-injection complete. Continue using the panel.")
                except Exception as e:
                    print(f"[wizard] Re-injection failed: {e}")
                last_url = current_url
            elif current_url and not last_url:
                last_url = current_url

            time.sleep(3)

        if not result:
            print("[wizard] Timeout, no result received")
            return

        # Step 4: generate config and write sites.yaml
        print("[wizard] Generating config file...")
        config = build_config(key, name, base_url, entry_url, result)
        write_config(key, config)
        print(f"[wizard] Config written to sites.yaml")

    except Exception as e:
        print(f"[wizard] Error: {e}")
    finally:
        try:
            client.close_session()
        except Exception:
            pass


def build_config(key: str, name: str, base_url: str, entry_url: str, result: dict) -> dict:
    """根据向导结果生成 sites.yaml 中的配置 dict。"""
    link_type = result.get("link_type", "video")
    link_selector = result.get("link_selector", "")
    stream_url = result.get("stream_url")

    # 从 selected_url 提取 URL 模式
    selected_url = result.get("selected_url", entry_url)
    import re
    url_pattern = ""
    try:
        u = re.sub(r"\d+", r"\\d+", selected_url.split("?")[0])
        # 只替换路径中的数字
        parts = u.split("/")
        pat_parts = []
        for p in parts:
            if re.search(r"\d", p):
                pat_parts.append(re.sub(r"\d+", r"\\d+", p))
            else:
                pat_parts.append(p)
        url_pattern = "/" + "/".join(pat_parts[3:]) if len(pat_parts) > 3 else "/".join(pat_parts)
        url_pattern = url_pattern.replace(r"\\d+\.html", r"\\d+\.html")
        # 简化：只保留路径部分
        url_pattern = "/" + "/".join(
            re.sub(r"\d+", r"\\d+", p) for p in selected_url.split("/")[3:] if p
        )
    except Exception:
        url_pattern = ""

    # 构建 extract_chains JS
    if link_type == "video":
        detail_js = """
JSON.stringify([...document.querySelectorAll('a')].filter(a => {
    const href = a.href || '';
    return href.includes('/vodplay/') || href.includes('/play/');
}).map(a => ({
    href: a.href,
    text: a.textContent.trim().substring(0, 50),
    class: a.className
})).filter(a => a.href))
""".strip()

        play_js = """
JSON.stringify((() => {
    const iframes = [...document.querySelectorAll('iframe')];
    for (const f of iframes) {
        const src = f.src || '';
        if (!src) continue;
        try {
            const url = new URL(src);
            const videoUrl = url.searchParams.get('url');
            if (videoUrl && (videoUrl.includes('.m3u8') || videoUrl.includes('.mp4'))) {
                return {player_iframe: src, stream_url: videoUrl};
            }
        } catch(e) {}
        if (src.includes('.m3u8') || src.includes('.mp4')) {
            return {player_iframe: src, stream_url: src};
        }
    }
    return {player_iframe: null, stream_url: null};
})())
""".strip()

        extract_chains = {
            "video": {
                "steps": [
                    {"name": "detail", "extract_js": detail_js},
                    {"name": "play", "extract_js": play_js},
                ]
            }
        }
        video_detail_patterns = [url_pattern] if url_pattern else []
        art_detail_patterns = []
    else:
        detail_js = """
JSON.stringify((() => {
    const container = document.getElementById('read_tpc') || document.body;
    return [...container.querySelectorAll('img')]
        .map(img => img.src || img.dataset.src || img.dataset.original || '')
        .filter(s => s && !s.startsWith('data:'));
})())
""".strip()

        extract_chains = {
            "art": {
                "steps": [
                    {"name": "detail", "extract_js": detail_js},
                ]
            }
        }
        video_detail_patterns = []
        art_detail_patterns = [url_pattern] if url_pattern else []

    return {
        "name": name,
        "base_url": base_url,
        "link_patterns": {
            "video_detail": video_detail_patterns,
            "art_detail": art_detail_patterns,
            "exclude": [
                "/vodtype/", "/vodshow/", "/vodsearch/",
                "/topic/", "/tag/", "/static/",
            ],
        },
        "extract_chains": extract_chains,
        "entry_points": [
            {"name": "Default Entry", "url": entry_url, "type": link_type}
        ],
    }


def write_config(key: str, config: dict):
    """写入 sites.json。"""
    path = os.path.normpath(SITES_JSON)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = {}

    if "sites" not in raw:
        raw["sites"] = {}

    raw["sites"][key] = config

    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"[wizard] Written to {path}")
