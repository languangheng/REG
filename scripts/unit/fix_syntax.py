# -*- coding: utf-8 -*-
fpath = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit\generate_paper_v3.py"
content = open(fpath, 'r', encoding='utf-8').read()

# Fix the syntax error: ]], space_after=6) should be ], space_after=6)
old = "    '而非\"从第一原理的严格推导\"。这一步需要数学突破。', False, False]], space_after=6)"
new = "    '而非\"从第一原理的严格推导\"。这一步需要数学突破。', False, False)], space_after=6)"

if old in content:
    content = content.replace(old, new, 1)
    print("Fixed!")
else:
    print("NOT FOUND - printing nearby:")
    for i, line in enumerate(content.split('\n')):
        if 'space_after=6' in line and ']]' in line:
            print(f"Line {i}: {repr(line)}")

open(fpath, 'w', encoding='utf-8').write(content)
