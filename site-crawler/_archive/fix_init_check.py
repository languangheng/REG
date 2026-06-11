"""Fix: skip init if state restored (stage !== 'init')."""

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Find the initialization block and add stage check
old_init = '''  // ── Start ──
  setStep('Ready. Click Start to begin.');
  setActions([
    { label: 'Start Select', cls: 'btn-primary', fn: startSelectLink },
    { label: 'Cancel', cls: 'btn-ghost', fn: () => log('Cancel') },
  ]);
  log('Config Wizardready');'''

new_init = '''  // ── Start / Resume ──
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
  }'''

if old_init in c:
    c = c.replace(old_init, new_init, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed: init block now checks stage before showing Start button")
else:
    print("ERROR: could not find init block")
    # Try to find it
    idx = c.find('Ready. Click Start to begin')
    if idx >= 0:
        print(f"Found at {idx}")
        print(c[max(0,idx-100):idx+300])