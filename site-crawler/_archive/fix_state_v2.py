"""Fix state persist v2 - simpler approach without regex."""

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check what we have after previous fix
count = content.count('saveState()')
print(f"Current saveState() calls: {count}")

# Find all window.location.href assignments
import re
matches = list(re.finditer(r'window\.location\.href\s*=', content))
print(f"\nFound {len(matches)} window.location.href assignments:")
for m in matches:
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 100)
    snippet = content[start:end]
    print(f"  - Pos {m.start()}: ...{repr(snippet)}...")

# The regex error was in my previous script. Let me just do simple string replace
# for the specific case I know about.

# Actually, let me just check: does proceedToDetail already have saveState?
idx = content.find('proceedToDetail')
if idx >= 0:
    snippet = content[idx:idx+500]
    if 'saveState()' in snippet:
        print("\nproceedToDetail already has saveState() - good")
    else:
        print("\nproceedToDetail missing saveState() - need to add")

# Let me also check the onPlaySelected function
idx = content.find('onPlaySelected')
if idx >= 0:
    snippet = content[idx:idx+500]
    print(f"\nonPlaySelected snippet: {repr(snippet)}")

# Now let me fix the actual issue: make sure saveState is called before navigation
# The proceedToDetail function should already have saveState (from previous fix).
# But we also need to handle the case where user clicks a play link naturally.

# Actually, the simplest fix is to use beforeunload event to save state
# Let me add that to the overlay JS.

# Find the end of the state definition / beginning of event listeners
# Add a beforeunload listener to save state

old_after_state = '''  window.__cw_state = state;

  // Save state before navigation
  function saveState() {
    try {
      sessionStorage.setItem('cw_state', JSON.stringify(state));
    } catch(e) { console.error('[wizard] State save error:', e); }
  }
  window.__cw_saveState = saveState;'''

new_with_beforeunload = '''  window.__cw_state = state;

  // Save state before navigation
  function saveState() {
    try {
      sessionStorage.setItem('cw_state', JSON.stringify(state));
    } catch(e) { console.error('[wizard] State save error:', e); }
  }
  window.__cw_saveState = saveState;

  // Auto-save state before page unload (covers natural link clicks)
  window.addEventListener('beforeunload', () => saveState());'''

if old_after_state in content:
    content = content.replace(old_after_state, new_with_beforeunload)
    print("\nAdded beforeunload listener to auto-save state")
else:
    print("\nWARNING: Could not find saveState definition to add beforeunload")
    # Try to find where to add it
    idx = content.find('window.__cw_state = state;')
    if idx >= 0:
        print(f"Found '__cw_state = state' at {idx}")

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("\nDone! State should now persist across ALL navigations (including natural link clicks).")