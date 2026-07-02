# -*- coding: utf-8 -*-
import pathlib

p = pathlib.Path(r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit\generate_paper_v2.py')
content = p.read_text('utf-8')

# The file contains the literal text: \u632振荡 (invalid unicode escape + 振 + 荡)
# Fix: replace with \u6327振荡 (振 = U+6327, 荡 = U+8361)
old = '\\u632振荡'   # literal backslash + u632 + 振 + 荡
new = '\\u6327振荡'  # literal backslash + u6327 (振) + 荡

if old in content:
    content = content.replace(old, new)
    p.write_text(content, 'utf-8')
    print('Fixed! Replaced', repr(old), 'with', repr(new))
else:
    print('Pattern not found')
