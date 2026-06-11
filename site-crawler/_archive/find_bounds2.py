path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
# Find the end of OVERLAY_JS - it's the second """ after the start
i = c.find('OVERLAY_JS = r"""')
j1 = c.find('"""', i + 20)  # first closing """
# The actual end is the next """ 
j2 = c.find('"""', j1 + 3)
print("After OVERLAY_JS end:", repr(c[j2+3:j2+40]))
