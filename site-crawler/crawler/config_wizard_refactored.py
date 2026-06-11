"""
Refactored config_wizard.py - Python-centric state management.
Uses BrowserActClient for all browser operations.
"""

import os
import sys
import time
import json
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from browser_act import BrowserActClient

# ── CSS (unchanged) ──
OVERLAY_CSS = """
.cw-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 2147483647; pointer-events: none; }
.cw-panel { position: fixed; top: 20px; right: 20px; width: 360px; background: #1a1a2e; color: #e0e0e0; border-radius: 12px; padding: 20px; font-family: 'Segoe UI', sans-serif; font-size: 14px; z-index: 2147483647; pointer-events: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.5); border: 1px solid #3a3a5e; }
.cw-step { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #00d4ff; }
.cw-detail { font-size: 13px; color: #a0a0c0; margin-bottom: 16px; line-height: 1.5; }
.cw-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.cw-btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
.cw-btn-primary { background: #00d4ff; color: #000; }
.cw-btn-primary:hover { background: #00b8e6; }
.cw-btn-ghost { background: transparent; color: #a0a0c0; border: 1px solid #3a3a5e; }
.cw-btn-ghost:hover { border-color: #00d4ff; color: #00d4ff; }
.cw-btn-danger { background: #ff4757; color: #fff; }
.cw-btn-danger:hover { background: #ff6b81; }
.cw-close { position: absolute; top: 12px; right: 12px; width: 24px; height: 24px; border-radius: 50%; border: none; background: rgba(255,255,255,0.1); color: #a0a0c0; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; }
.cw-log { margin-top: 12px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 6px; font-size: 12px; max-height: 120px; overflow-y: auto; font-family: monospace; }
.cw-log div { margin: 2px 0; }
.cw-highlight { outline: 3px solid #00d4ff !important; outline-offset: 2px !important; cursor: pointer !important; }
.cw-badge { display: inline-block; padding: 2px 8px; background: #00d4ff; color: #000; border-radius: 4px; font-size: 12px; font-weight: 600; margin-left: 8px; }
"""

# ── Stateless JS (reads state from Python, sends events) ──
OVERLAY_JS_STATELESS = """
(function() {
  if (window.__cw_injected) {
    // Update existing overlay with new state
    window.__cw_state = _cw_new_state;
    window.__cw_render && window.__cw_render();
    return;
  }
  window.__cw_injected = true;

  // State passed from Python
  var state = window.__cw_state || { stage: 'init' };

  function log(msg) {
    var el = document.getElementById('cw-log');
    if (el) {
      var d = document.createElement('div');
      d.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
      el.appendChild(d);
      el.scrollTop = el.scrollHeight;
    }
    console.log('[wizard]', msg);
  }

  function setStep(html) {
    var el = document.getElementById('cw-step');
    if (el) el.innerHTML = html;
  }

  function setDetail(html) {
    var el = document.getElementById('cw-detail');
    if (el) el.innerHTML = html;
  }

  function setActions(actions) {
    var el = document.getElementById('cw-actions');
    if (!el) return;
    el.innerHTML = '';
    actions.forEach(function(a) {
      var btn = document.createElement('button');
      btn.className = 'cw-btn ' + a.cls;
      btn.textContent = a.label;
      btn.onclick = function() {
        log('Action: ' + a.label);
        window.__cw_event = { type: a.event || 'button_click', label: a.label, data: a.data || {} };
        if (a.fn) a.fn();
      };
      el.appendChild(btn);
    });
  }

  function getSelector(el) {
    if (el.id) return '#' + el.id;
    if (el.className) return '.' + el.className.split(' ')[0];
    return el.tagName.toLowerCase();
  }

  function enableLinkSelection() {
    window.__cw_onlink = function(e) {
      if (state.stage !== 'selecting_link') return;
      e.preventDefault();
      e.stopPropagation();
      var a = e.currentTarget;
      window.__cw_selected_link = { href: a.href, text: a.textContent.trim().substring(0, 80), selector: getSelector(a) };
      log('Link clicked: ' + a.textContent.trim().substring(0, 40));
      document.querySelectorAll('.cw-highlight').forEach(function(el) {
        el.classList.remove('cw-highlight');
        el.removeEventListener('click', window.__cw_onlink);
      });
      window.__cw_event = { type: 'link_selected', data: window.__cw_selected_link };
    };
    document.querySelectorAll('a[href]').forEach(function(a) {
      a.classList.add('cw-highlight');
      a.addEventListener('click', window.__cw_onlink, true);
    });
    log('Click a link...');
  }

  function enablePlaySelection() {
    window.__cw_onplay = function(e) {
      if (state.stage !== 'selecting_play') return;
      e.preventDefault();
      e.stopPropagation();
      var a = e.currentTarget;
      window.__cw_play_link = { href: a.href, text: a.textContent.trim().substring(0, 80), selector: getSelector(a) };
      log('Play clicked: ' + a.textContent.trim().substring(0, 40));
      document.querySelectorAll('.cw-highlight').forEach(function(el) {
        el.classList.remove('cw-highlight');
        el.removeEventListener('click', window.__cw_onplay);
      });
      window.__cw_event = { type: 'play_selected', data: window.__cw_play_link };
    };
    document.querySelectorAll('a').forEach(function(a) {
      var t = a.textContent.trim().toLowerCase();
      if (t.includes('play') || t.includes('watch') || t.includes('hd')) {
        a.classList.add('cw-highlight');
        a.addEventListener('click', window.__cw_onplay, true);
      }
    });
    log('Click play button...');
  }

  function extractStreamUrl() {
    log('Extracting stream URL...');
    var links = Array.from(document.querySelectorAll('a[href*=".m3u8"], a[href*=".mp4"]'));
    if (links.length > 0) {
      var url = links[0].href;
      window.__cw_stream_url = url;
      log('Stream: ' + url.substring(0, 60));
      window.__cw_event = { type: 'stream_found', data: { url: url } };
    } else {
      var videos = document.querySelectorAll('video[src], video source[src]');
      if (videos.length > 0) {
        var url = videos[0].src || videos[0].getAttribute('src');
        window.__cw_stream_url = url;
        log('Video: ' + url.substring(0, 60));
        window.__cw_event = { type: 'stream_found', data: { url: url } };
      } else {
        log('No stream found');
        window.__cw_event = { type: 'stream_not_found' };
      }
    }
  }

  window.__cw_render = function() {
    var stage = state.stage;
    log('Stage: ' + stage);
    if (stage === 'init') {
      setStep('Config Wizard');
      setDetail('Click Start to begin configuration.');
      setActions([{ label: 'Start', cls: 'cw-btn-primary', event: 'start_wizard' }, { label: 'Cancel', cls: 'cw-btn-ghost', event: 'cancel' }]);
    } else if (stage === 'selecting_link') {
      setStep('Select a Link');
      setDetail('Click a video or content link on the page');
      setActions([{ label: 'Cancel', cls: 'cw-btn-ghost', event: 'cancel', fn: function() {
        document.querySelectorAll('.cw-highlight').forEach(function(el) { el.classList.remove('cw-highlight'); el.removeEventListener('click', window.__cw_onlink); });
        window.__cw_event = { type: 'back_to_init' };
      }}]);
      enableLinkSelection();
    } else if (stage === 'link_selected') {
      setStep('Link Selected');
      setDetail('Selected: ' + (state.selected_link ? state.selected_link.text : '') + '<br>Type: ' + state.link_type);
      setActions([{ label: 'Confirm', cls: 'cw-btn-primary', event: 'confirm_link' }, { label: 'Re-select', cls: 'cw-btn-ghost', event: 'reselect_link' }]);
    } else if (stage === 'navigating') {
      setStep('Navigating...');
      setDetail('Going to: ' + (state.selected_link ? state.selected_link.href : ''));
      setActions([]);
    } else if (stage === 'selecting_play') {
      setStep('Select Play Button');
      setDetail('Click the Play / Watch Now button on the detail page');
      setActions([{ label: 'Skip', cls: 'cw-btn-ghost', event: 'skip_play' }, { label: 'Cancel', cls: 'cw-btn-ghost', event: 'cancel' }]);
      enablePlaySelection();
    } else if (stage === 'play_selected') {
      setStep('Play Selected');
      setDetail('URL: ' + (state.play_link ? state.play_link.href : ''));
      setActions([{ label: 'Confirm', cls: 'cw-btn-primary', event: 'confirm_play' }, { label: 'Re-select', cls: 'cw-btn-ghost', event: 'reselect_play' }]);
    } else if (stage === 'extracting_stream') {
      setStep('Extracting Stream URL...');
      setDetail('Please wait...');
      setActions([]);
      setTimeout(extractStreamUrl, 1000);
    } else if (stage === 'stream_found') {
      setStep('Stream Found');
      setDetail('URL: ' + (state.stream_url ? state.stream_url.substring(0, 60) : ''));
      setActions([{ label: 'Confirm & Save', cls: 'cw-btn-primary', event: 'confirm_stream' }, { label: 'Retry', cls: 'cw-btn-ghost', event: 'retry_extract' }]);
    } else if (stage === 'done') {
      setStep('Done!');
      setDetail('Configuration saved. Close this panel.');
      setActions([{ label: 'Close', cls: 'cw-btn-primary', event: 'close' }]);
    }
  };

  // Create panel
  var panel = document.createElement('div');
  panel.className = 'cw-panel';
  panel.innerHTML = '<button class="cw-close" id="cw-close-btn">x</button><div class="cw-step" id="cw-step"></div><div class="cw-detail" id="cw-detail"></div><div class="cw-actions" id="cw-actions"></div><div class="cw-log" id="cw-log"></div>';

  var overlay = document.createElement('div');
  overlay.className = 'cw-overlay';
  overlay.appendChild(panel);
  document.body.appendChild(overlay);

  // Inject CSS
  if (!document.getElementById('cw-css')) {
    var css = document.createElement('style');
    css.id = 'cw-css';
    css.textContent = document.querySelector('style[data-id="cw-css"]') ? '' : '%s';
    if (css.textContent === '' && document.querySelector('style[data-id="cw-css"]')) {
      // already injected
    } else {
      document.head.appendChild(css);
    }
  }

  log('Wizard injected, stage=' + state.stage);
  window.__cw_render();

  // Close button handler
  document.getElementById('cw-close-btn').onclick = function() {
    window.__cw_event = {type: 'close_panel'};
  };
})();
""" % OVERLAY_CSS

# ── Build injection JS ──
def build_inject_js(state):
    """Build JS to inject, passing Python state to JS."""
    state_json = json.dumps(state, ensure_ascii=False)
    # Strip old overlay before creating new one
    js = """
(function() {
  // Remove old overlay
  var old = document.querySelector('.cw-overlay');
  if (old) old.remove();
  window.__cw_injected = false;

  // Pass Python state
  window.__cw_state = %s;

  // Run stateless overlay
  %s
})();
""" % (state_json, OVERLAY_JS_STATELESS)
    return js


# ── URL to pattern ──
def url_to_pattern(url):
    from urllib.parse import urlparse
    import re
    parsed = urlparse(url)
    pattern = re.sub(r'\d+', '(*)', parsed.path)
    return pattern


# ── Main wizard ──
def run_wizard(entry_url, site_name):
    """Run config wizard with Python-managed state."""
    print(f'[wizard] Starting wizard: {site_name}')
    print(f'[wizard] Entry: {entry_url}')

    # ── State (single source of truth) ──
    wizard_state = {
        'stage': 'init',
        'link_type': 'video',
        'selected_link': None,
        'play_link': None,
        'stream_url': None,
        'link_selector': None,
        'config': {
            'link_patterns': {'video_detail': [], 'art_detail': [], 'exclude': []},
            'extract_chains': {}
        },
        'site_name': site_name,
        'entry_url': entry_url,
    }

    session = f'wizard_{site_name}'
    client = BrowserActClient(session=session)

    print(f'[wizard] Opening entry page...')
    try:
        client.navigate(entry_url)
    except Exception as e:
        print(f'[wizard] Failed to open URL: {e}')
        return None

    time.sleep(2)

    # ── Main loop ──
    print(f'[wizard] Overlay ready. Use browser panel to configure.')
    last_url = entry_url
    last_stage = None

    while wizard_state['stage'] != 'done':
        current_url = None
        try:
            url_result = client.evaluate_js('window.location.href')
            if url_result and url_result != 'undefined':
                current_url = json.loads(url_result) if url_result.startswith('{') or url_result.startswith('"') else url_result.strip('"')
        except:
            pass

        if current_url and current_url != last_url:
            print(f'[wizard] URL changed: {last_url} -> {current_url}')
            last_url = current_url

        # Inject overlay with current state
        if wizard_state['stage'] != last_stage:
            print(f'[wizard] Stage: {wizard_state["stage"]}')
            last_stage = wizard_state['stage']

        js = build_inject_js(wizard_state)
        try:
            client.evaluate_js(js)
        except Exception as e:
            print(f'[wizard] Injection failed: {e}')
            time.sleep(2)
            continue

        # Poll for event from JS
        time.sleep(2)
        try:
            event_raw = client.evaluate_js('window.__cw_event')
            if event_raw and event_raw.strip() and event_raw != 'null':
                event = json.loads(event_raw)
                print(f'[wizard] Event: {event}')

                # Clear event
                client.evaluate_js('window.__cw_event = null')

                # Handle event
                handle_event(event, wizard_state, client)
        except Exception as e:
            # No event yet, keep polling
            pass

    # ── Done ──
    print(f'[wizard] Writing config...')
    write_config(wizard_state)
    print(f'[wizard] Wizard complete!')
    return wizard_state['config']


def handle_event(event, state, client):
    """Handle events from JS, update Python state."""
    event_type = event.get('type')
    data = event.get('data', {})

    if event_type == 'start_wizard':
        state['stage'] = 'selecting_link'

    elif event_type == 'link_selected':
        state['selected_link'] = data
        href = data.get('href', '')
        state['link_type'] = 'video'
        state['stage'] = 'link_selected'

    elif event_type == 'confirm_link':
        href = state['selected_link']['href']
        print(f'[wizard] Navigating to: {href}')
        state['stage'] = 'navigating'
        client.navigate(href)
        time.sleep(2)
        state['stage'] = 'selecting_play'

    elif event_type == 'reselect_link':
        state['stage'] = 'selecting_link'

    elif event_type == 'play_selected':
        state['play_link'] = data
        state['stage'] = 'play_selected'

    elif event_type == 'confirm_play':
        href = state['play_link']['href']
        print(f'[wizard] Navigating to play: {href}')
        state['stage'] = 'navigating'
        client.navigate(href)
        time.sleep(3)
        state['stage'] = 'extracting_stream'

    elif event_type == 'reselect_play':
        state['stage'] = 'selecting_play'

    elif event_type == 'stream_found':
        state['stream_url'] = data.get('url')
        state['stage'] = 'stream_found'

    elif event_type == 'stream_not_found':
        state['stage'] = 'stream_found'  # Allow manual retry

    elif event_type == 'retry_extract':
        state['stage'] = 'extracting_stream'

    elif event_type == 'confirm_stream':
        pattern = url_to_pattern(state['selected_link']['href'])
        if state['link_type'] == 'video':
            state['config']['link_patterns']['video_detail'].append(pattern)
        else:
            state['config']['link_patterns']['art_detail'].append(pattern)
        state['link_selector'] = state['selected_link'].get('selector')
        state['stage'] = 'done'

    elif event_type == 'cancel':
        print('[wizard] Cancelled by user')
        state['stage'] = 'done'

    elif event_type == 'close_panel':
        print('[wizard] Panel closed by user')
        state['stage'] = 'done'

    else:
        print(f'[wizard] Unknown event: {event_type}')


def write_config(state):
    """Write sites.yaml config."""
    config = state['config']
    site_name = state['site_name']

    config_dir = SCRIPT_DIR.parent / 'config'
    config_dir.mkdir(exist_ok=True)
    sites_file = config_dir / 'sites.yaml'

    if sites_file.exists():
        with open(sites_file, 'r', encoding='utf-8') as f:
            sites = yaml.safe_load(f) or {}
    else:
        sites = {}

    sites[site_name] = {
        'link_patterns': config['link_patterns'],
        'link_selector': state.get('link_selector'),
        'stream_url': state.get('stream_url'),
    }

    with open(sites_file, 'w', encoding='utf-8') as f:
        yaml.dump(sites, f, allow_unicode=True, sort_keys=False)

    print(f'[wizard] Config written to {sites_file}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    run_wizard(args.url, args.name)