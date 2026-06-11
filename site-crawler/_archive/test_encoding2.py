import sys, subprocess, tempfile, os
sys.path.insert(0, '.')
from crawler.config_wizard import OVERLAY_JS

# 写临时文件
t = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
t.write(OVERLAY_JS)
t.close()

# 先打开一个 session
env = os.environ.copy()
env["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + env.get("PATH", "")

# 先 navigate
r = subprocess.run(
    ['browser-act', '--session=enc_test', 'browser', 'open', 'direct_local_100797252049567848', 'https://www.baidu.com'],
    capture_output=True, timeout=30, env=env
)
print("Navigate:", r.stdout.decode('utf-8', errors='replace')[:100])

# 测试1: PowerShell pipe 传简单中文 JS
ps_cmd = f'Get-Content -Path "{t.name}" -Raw -Encoding UTF8 | browser-act --session=enc_test eval --stdin'
r = subprocess.run(
    ['powershell', '-NoProfile', '-Command', ps_cmd],
    capture_output=True, timeout=30, env=env
)
print("PS pipe result:", r.stdout.decode('utf-8', errors='replace')[:200])
print("PS pipe stderr:", r.stderr.decode('utf-8', errors='replace')[:200])

# 测试2: 直接注入一段简单中文测试
test_js = "document.title = '中文测试标题'; document.title"
r2 = subprocess.run(
    ['browser-act', '--session=enc_test', 'eval', test_js],
    capture_output=True, timeout=10, env=env
)
print("Simple Chinese eval:", r2.stdout.decode('utf-8', errors='replace')[:200])

# 测试3: 通过 PowerShell pipe 传中文
t2 = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
t2.write("document.title = 'PowerShell中文测试'; document.title")
t2.close()
ps_cmd2 = f'Get-Content -Path "{t2.name}" -Raw -Encoding UTF8 | browser-act --session=enc_test eval --stdin'
r3 = subprocess.run(
    ['powershell', '-NoProfile', '-Command', ps_cmd2],
    capture_output=True, timeout=10, env=env
)
print("PS pipe Chinese:", r3.stdout.decode('utf-8', errors='replace')[:200])

# 清理
for f in [t.name, t2.name]:
    try: os.unlink(f)
    except: pass
