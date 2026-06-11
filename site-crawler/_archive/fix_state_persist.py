"""Fix: persist state across page navigation using sessionStorage."""

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state save/restore functions after state definition
# Find: let state = { ... }; window.__cw_state = state;
# Add after it: saveState/restoreState functions

old_state_init = '''  // ── State ──
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
  window.__cw_state = state;'''

new_state_init = '''  // ── State ──
  let state = {
    stage: 'init',        // init | select_link | navigating | detail | select_play | play_navigating | stream_found | done
    link_type: null,       // 'video' or 'image'
    selected_link: null,     // {href, text, selector}
    detail_url: null,
    play_link: null,
    stream_url: null,
    link_selector: null,    // CSS selector for similar links
    config: { link_patterns: {video_detail:[], art_detail:[], exclude:[]}, extract_chains: {} }
  };

  // Restore state from sessionStorage (survives page navigation)
  try {
    const saved = sessionStorage.getItem('cw_state');
    if (saved) {
      const parsed = JSON.parse(saved);
      // Merge saved state into current state
      Object.assign(state, parsed);
      console.log('[wizard] Restored state:', state.stage);
    }
  } catch(e) { console.error('[wizard] State restore error:', e); }
  window.__cw_state = state;

  // Save state before navigation
  function saveState() {
    try {
      sessionStorage.setItem('cw_state', JSON.stringify(state));
    } catch(e) { console.error('[wizard] State save error:', e); }
  }
  window.__cw_saveState = saveState;'''

if old_state_init in content:
    content = content.replace(old_state_init, new_state_init)
    print("Step 1: Added saveState/restoreState")
else:
    print("ERROR: old_state_init not found")
    idx = content.find('// ── State ──')
    if idx >= 0:
        print("Found '// ── State ──' at", idx)
        print(repr(content[idx:idx+300]))

# 2. Add saveState() before window.location.href navigations
# In proceedToDetail():
content = content.replace(
    '    log(`Navigate to: ${state.selected_link.href}`);\n    window.location.href = state.selected_link.href;',
    '    log(`Navigate to: ${state.selected_link.href}`);\n    saveState();\n    window.location.href = state.selected_link.href;'
)
print("Step 2: Added saveState before detail page navigation")

# In onPlaySelected() or similar - find all window.location.href assignments
import re
count = 0
def replace_navigation(m):
    global count
    count += 1
    return m.group(0).replace('window.location.href = ', 'saveState();\n    window.location.href = ')
# Only replace navigations that don't already have saveState before them
# Simple approach: just add saveState() before each window.location.href
new_content = re.sub(
    r'(?<!\bsaveState\(\);\s*\n\s*)(\s+)window\.location\.href\s*=',
    r'\1saveState();\n\1window.location.href = ',
    content
)
if new_content != content:
    content = new_content
    print(f"Step 3: Added saveState before all window.location.href ({count} replacements)")
else:
    print("Step 3: No additional replacements needed")

# 4. Modify onPageLoad to use restored state
old_onPageLoad = '''  // ── Listen for page load (detail page)──
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
      } else {
        // Image type: extract images
        setStep('Extracting image links...');
        setActions([]);
        extractImageLinks();
      }
    }
  }
  window.addEventListener('load', () => setTimeout(onPageLoad, 500));'''

new_onPageLoad = '''  // ── Listen for page load (detail page)──
  let pageReady = false;
  function onPageLoad() {
    if (pageReady) return;
    pageReady = true;
    console.log('[wizard] onPageLoad, stage:', state.stage);
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
      } else {
        // Image type: extract images
        setStep('Extracting image links...');
        setActions([]);
        extractImageLinks();
      }
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
    }
  }
  window.addEventListener('load', () => setTimeout(onPageLoad, 500));'''

if old_onPageLoad in content:
    content = content.replace(old_onPageLoad, new_onPageLoad)
    print("Step 4: Modified onPageLoad to handle play_navigating stage")
else:
    print("WARNING: old_onPageLoad not found - may already be modified")
    idx = content.find('function onPageLoad')
    if idx >= 0:
        print("Found onPageLoad at", idx)
        print(repr(content[idx:idx+200]))

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("\nDone! State persistence across navigation should now work.")