path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'OVERLAY_JS = r"""'
i = content.find(start_marker)
js_start = i + len(start_marker)
js_end = content.find('"""', js_start)
js = content[js_start:js_end]

import re
# Find all Chinese text strings in JS
cn_strings = re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff01-\uff60]+', js)
unique = sorted(set(cn_strings))
# Write to file for inspection
with open('cn_strings.txt', 'w', encoding='utf-8') as out:
    for s in unique:
        out.write(s + '\n')
print(f"Found {len(unique)} unique Chinese strings, written to cn_strings.txt")
