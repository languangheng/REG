"""测试 JS 注入是否生效（带调试输出）"""

import sys, io, os, time, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 确保 browser-act 在 PATH
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ.get("PATH", "")

print("=" * 60)
print("  测试 JS 注入")
print("=" * 60)

# 手动调 browser-act，看输出
print("\n[1] 检查 browser-act...")
r = subprocess.run(["browser-act", "--help"], capture_output=True, text=True, encoding="utf-8", timeout=10)
print(f"  exit code: {r.returncode}")
print(f"  stdout (前100字): {r.stdout[:100]}")
print(f"  stderr (前100字): {r.stderr[:100]}")

print("\n[2] 尝试打开页面...")
r2 = subprocess.run(
    ["browser-act", "--session", "inject_test", "navigate", "https://www.mimimi.top"],
    capture_output=True, text=True, encoding="utf-8", timeout=30
)
print(f"  exit code: {r2.returncode}")
print(f"  stdout: {r2.stdout[:200]}")
print(f"  stderr: {r2.stderr[:200]}")

print("\n[3] 注入简单 JS...")
simple_js = "document.title"
r3 = subprocess.run(
    ["browser-act", "--session", "inject_test", "eval", simple_js],
    capture_output=True, text=True, encoding="utf-8", timeout=15
)
print(f"  exit code: {r3.returncode}")
print(f"  stdout: {r3.stdout[:200]}")
print(f"  stderr: {r3.stderr[:200]}")

print("\n[4] 注入带 DOM 操作的 JS...")
js2 = "document.body.innerHTML += '<div id=test_inject style=\"position:fixed;top:0;left:0;background:red;color:#fff;padding:20px;z-index:2147483647;\">注入成功</div>'; 'ok';"
r4 = subprocess.run(
    ["browser-act", "--session", "inject_test", "eval", js2],
    capture_output=True, text=True, encoding="utf-8", timeout=15
)
print(f"  exit code: {r4.returncode}")
print(f"  stdout: {r4.stdout[:200]}")
print(f"  stderr: {r4.stderr[:200]}")

print("\n[5] 等待 20 秒，请在浏览器中确认是否看到红色横幅...")
time.sleep(20)

# 清理
r5 = subprocess.run(
    ["browser-act", "session", "close", "inject_test"],
    capture_output=True, text=True, encoding="utf-8", timeout=10
)
print(f"\n  清理完成: {r5.stdout[:100]}")
print("=" * 60)
print("  测试完成")
print("=" * 60)
