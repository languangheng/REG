path = r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\crawler\config_wizard.py"
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
i = c.find('OVERLAY_JS')
print('OVERLAY_JS at:', i)
# find the closing triple quote
j = c.find('"""', i + 20)
print('first """ after start:', j)
k = c.find('"""', j + 3)
print('second """ (end of js):', k)
print('context around k:', repr(c[k:k+30]))
