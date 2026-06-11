import sys, subprocess, tempfile, os
sys.path.insert(0, '.')
from crawler.config_wizard import OVERLAY_JS

env = os.environ.copy()
env["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + env.get("PATH", "")

# 打开页面
r = subprocess.run(
    ['browser-act', '--session=chk', 'browser', 'open', 'direct_local_100797252049567848', 'https://www.baidu.com'],
    capture_output=True, timeout=30, env=env
)
print("Navigate:", r.stdout.decode('utf-8', errors='replace')[:100])

# 注入 OVERLAY_JS
t = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
t.write(OVERLAY_JS)
t.close()
ps_cmd = f'Get-Content -Path "{t.name}" -Raw -Encoding UTF8 | browser-act --session=chk eval --stdin'
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], capture_output=True, timeout=30, env=env)
print("Inject:", r.stdout.decode('utf-8', errors='replace')[:100])

# 检查面板内容 - 用 escape 避免中文编码问题
check_js = "JSON.stringify({title: document.querySelector('#cw-panel h3')?.textContent, found: !!document.querySelector('#cw-panel'), wiz: !!window.__crawler_wizard})"
r = subprocess.run(['browser-act', '--session=chk', 'eval', check_js], capture_output=True, timeout=10, env=env)
raw = r.stdout.decode('utf-8', errors='replace')
print("Check raw:", raw[:200])

# 也用 PowerShell pipe 检查
t2 = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
t2.write(check_js)
t2.close()
ps2 = f'Get-Content -Path "{t2.name}" -Raw -Encoding UTF8 | browser-act --session=chk eval --stdin'
r2 = subprocess.run(['powershell', '-NoProfile', '-Command', ps2], capture_output=True, timeout=10, env=env)
raw2 = r2.stdout.decode('utf-8', errors='replace')
print("Check via PS:", raw2[:200])

for f in [t.name, t2.name]:
    try: os.unlink(f)
    except: pass
