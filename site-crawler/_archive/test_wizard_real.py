"""直接测试 wizard 注入 - 写文件规避 PowerShell 转义问题"""

import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient
from crawler.config_wizard import OVERLAY_JS

print("=" * 60)
print("  测试 OVERLAY_JS 注入")
print("=" * 60)

client = BrowserActClient(session="wizard_real_test", browser_id=None)

print("[1] 打开入口页...")
client.navigate("https://www.mimimi.top")
time.sleep(8)
print("  ✅ 页面已打开")

print("[2] 注入 OVERLAY_JS（长 JS，通过 stdin）...")
try:
    result = client.evaluate_js(OVERLAY_JS)
    print(f"  注入结果: {result[:200]}")
except Exception as e:
    print(f"  ❌ 注入失败: {e}")

print("[3] 检查覆盖层是否已添加到页面...")
check = client.evaluate_js(
    "JSON.stringify({"
    "  overlay: !!document.getElementById('cw-overlay'),"
    "  style: !!document.getElementById('cw-style'),"
    "  btn: !!document.getElementById('cw-start-btn'),"
    "  body_child_count: document.body.children.length"
    "})"
)
print(f"  检查结果: {check}")

print()
print("=" * 60)
print("  请在浏览器窗口中查看是否有覆盖层")
print("  覆盖层应在页面左上角，红色/橙色渐变背景")
print("  如果没有看到，请打开浏览器控制台（F12）查看错误")
print("=" * 60)
print()
print("等待 60 秒让你查看...")
time.sleep(60)

print("清理 session...")
try:
    client.close_session()
except Exception:
    pass
print("完成")
