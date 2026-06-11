path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'OVERLAY_JS = r"""'
i = content.find(start_marker)
js_start = i + len(start_marker)
js_end = content.find('"""', js_start)
before = content[:i]
after = content[js_end + 3:]
js = content[js_start:js_end]

# Final batch of remaining Chinese
final_replacements = {
    "同类": "similar",
    "后端读取": "backend read",
    "存到": "save to",
    "已就绪": "ready",
    "找到": "found",
    "把": "",
    "的": "'",
    "让": "for",
    "已": "",
    "跳过": "Skip",
    "选择": "select",
}

for cn, en in final_replacements.items():
    if cn in js:
        js = js.replace(cn, en)
        print(f"  Replaced: '{cn}' -> '{en}'")

import re
remaining = re.findall(r'[\u4e00-\u9fff]+', js)
if remaining:
    print(f"WARNING: {len(set(remaining))} still remaining: {set(remaining)}")
else:
    print("All clean!")

new_content = before + start_marker + js + '"""' + after
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("File saved.")
