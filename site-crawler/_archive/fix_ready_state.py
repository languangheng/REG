"""Fix: trigger onPageLoad immediately if document already loaded."""

path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Find the last line of onPageLoad registration and add readyState check
old_reg = '''  window.addEventListener('load', () => setTimeout(onPageLoad, 500));'''

new_reg = '''  window.addEventListener('load', () => setTimeout(onPageLoad, 500));

  // If document already loaded (re-injection case), trigger immediately
  if (document.readyState === 'complete') {
    setTimeout(onPageLoad, 500);
  }'''

if old_reg in c:
    c = c.replace(old_reg, new_reg, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed: onPageLoad will trigger immediately if document already loaded")
else:
    print("ERROR: could not find onPageLoad registration")
    idx = c.find("window.addEventListener('load'")
    if idx >= 0:
        print(f"Found at {idx}: {repr(c[idx:idx+80])}")