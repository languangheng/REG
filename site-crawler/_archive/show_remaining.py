path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'OVERLAY_JS = r"""'
i = content.find(start_marker)
js_start = i + len(start_marker)
js_end = content.find('"""', js_start)
js = content[js_start:js_end]

import re
remaining = re.findall(r'[\u4e00-\u9fff]+', js)
# Write as UTF-8 to a file
with open('remaining_cn.txt', 'w', encoding='utf-8') as out:
    for s in sorted(set(remaining)):
        # Show context
        idx = js.find(s)
        ctx = js[max(0,idx-20):idx+len(s)+20]
        out.write(f"'{s}' -> context: ...{ctx}...\n")
print(f"Written {len(set(remaining))} remaining strings")
