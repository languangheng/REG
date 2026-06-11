"""Fix state persist - correct version."""

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# ── 1. Add state restore after "window.__crawler_wizard = true;"
old1 = '  window.__crawler_wizard = true;'
new1 = '''  window.__crawler_wizard = true;

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
  } catch(e) { console.error('[wizard] Restore error:', e); }'''

if old1 in c:
    c = c.replace(old1, new1, 1)
    print("1. Added state restore logic")
else:
    print("ERROR: marker 1 not found")

# ── 2. After "window.__cw_state = state;" add saveState + beforeunload
old2 = '  window.__cw_state = state;'
new2 = '''  window.__cw_state = state;

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
  window.addEventListener('beforeunload', () => saveState());'''

if old2 in c:
    c = c.replace(old2, new2, 1)
    print("2. Added saveState function + beforeunload listener")
else:
    print("ERROR: marker 2 not found")

# ── 3. Add saveState() before "window.location.href = state.selected_link.href;"
old3 = '    window.location.href = state.selected_link.href;'
new3 = '    saveState();\n    window.location.href = state.selected_link.href;'

if old3 in c:
    c = c.replace(old3, new3, 1)
    print("3. Added saveState() before navigation")
else:
    print("WARNING: marker 3 not found (may already be fixed)")

# ── 4. Verify onPageLoad handles restored state
if 'state.stage === \'play_navigating\'' in c:
    print("4. onPageLoad already handles play_navigating stage")
else:
    print("4. Need to add play_navigating handler to onPageLoad")
    # Add it
    old4 = '''    } else {
        // Image type: extract images
        setStep('Extracting image links...');
        setActions([]);
        extractImageLinks();
      }
    }
  }
  window.addEventListener('load', () => setTimeout(onPageLoad, 500));'''

    new4 = '''    } else if (state.stage === 'play_navigating') {
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
  window.addEventListener('load', () => setTimeout(onPageLoad, 500));'''

    if old4 in c:
        c = c.replace(old4, new4, 1)
        print("   -> Added play_navigating handler")
    else:
        print("   WARNING: Could not add play_navigating handler")

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print("\nDone! State persistence should now work across page navigations.")