"""最小验证脚本 - 直接激活配置向导

用法:
    python test_wizard.py
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 测试参数
KEY = "test_mimimi"
NAME = "mimimi.top"
BASE_URL = "https://www.mimimi.top"
ENTRY_URL = "https://www.mimimi.top/vodshow/12-----------.html"

print("=" * 60)
print("  配置向导 - 最小验证")
print("=" * 60)
print(f"  Key:       {KEY}")
print(f"  Name:      {NAME}")
print(f"  Base URL:  {BASE_URL}")
print(f"  Entry URL: {ENTRY_URL}")
print("=" * 60)
print()

# 先检查 browser-act 是否可用
print("[1] 检查 browser-act...")
try:
    from crawler.browser_act import BrowserActClient
    client = BrowserActClient(session="wizard_test", browser_id=None)
    browsers = client.list_browsers()
    print(f"  ✅ browser-act 可用，当前浏览器数: {len(browsers)}")
    if not browsers:
        print("  ⚠️  没有浏览器，向导会自动创建一个")
except Exception as e:
    print(f"  ❌ browser-act 不可用: {e}")
    print("  请先运行: uv tool install browser-act-cli --python 3.12")
    sys.exit(1)

# 启动向导
print()
print("[2] 启动配置向导...")
print("  请在弹出的浏览器窗口中按提示操作")
print("  向导完成后，配置会保存到 sites.yaml")
print()

try:
    from crawler.config_wizard import run_wizard
    run_wizard(KEY, NAME, BASE_URL, ENTRY_URL)
    print()
    print("=" * 60)
    print("  ✅ 向导已完成！")
    print(f"  配置已保存到 sites.yaml (key={KEY})")
    print("=" * 60)
except Exception as e:
    print()
    print("=" * 60)
    print(f"  ❌ 向导失败: {e}")
    import traceback
    traceback.print_exc()
    print("=" * 60)
    sys.exit(1)
