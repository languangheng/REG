import sys, tempfile
sys.path.insert(0, '.')
from crawler.config_wizard import OVERLAY_JS

t = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
t.write(OVERLAY_JS)
t.close()
print(f"File: {t.name}")

with open(t.name, 'rb') as f:
    data = f.read()
    print(f"Total bytes: {len(data)}")
    print(f"Has BOM: {data[:3] == b'\\xef\\xbb\\xbf'}")
    # 找中文片段
    idx = data.find('配置'.encode('utf-8'))
    if idx >= 0:
        print(f"'配置' found at byte {idx}: {data[idx:idx+20]}")
    else:
        print("'配置' NOT found in file!")

# 也看看 PowerShell 读取后是什么
import subprocess
r = subprocess.run(
    ['powershell', '-NoProfile', '-Command', 
     f'[System.IO.File]::ReadAllText("{t.name}", [System.Text.Encoding]::UTF8).Length'],
    capture_output=True, timeout=10
)
print(f"PS read length: {r.stdout.decode().strip()}")
