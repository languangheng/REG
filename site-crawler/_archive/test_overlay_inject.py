"""最小测试：打开页面 → 注入覆盖层 JS → 验证弹窗"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from crawler.browser_act import BrowserActClient
from crawler.config_wizard import OVERLAY_JS

client = BrowserActClient(session="overlay_test")

# Step 1: 打开页面
print("[1] 打开 baidu.com ...")
try:
    result = client.navigate("https://www.baidu.com")
    print(f"    navigate 结果: {result[:200]}")
except Exception as e:
    print(f"    navigate 失败: {e}")
    sys.exit(1)

# 等页面加载
import time
time.sleep(5)

# Step 2: 先注入一个极简测试
print("[2] 注入极简 JS（红色横幅）...")
try:
    r = client.evaluate_js("document.body.innerHTML += '<div style=\"position:fixed;top:0;left:0;width:100%;height:40px;background:red;color:white;z-index:2147483647;text-align:center;line-height:40px;\">JS注入测试成功</div>'; 'ok'")
    print(f"    极简注入结果: {r[:200]}")
except Exception as e:
    print(f"    极简注入失败: {e}")

time.sleep(3)

# Step 3: 注入完整 OVERLAY_JS
print("[3] 注入完整覆盖层 JS...")
try:
    r = client.evaluate_js(OVERLAY_JS)
    print(f"    覆盖层注入结果: {r[:200]}")
except Exception as e:
    print(f"    覆盖层注入失败: {e}")

time.sleep(2)

# Step 4: 检查覆盖层是否存在
print("[4] 检查覆盖层元素...")
try:
    r = client.evaluate_js("document.getElementById('cw-panel') ? 'FOUND' : 'NOT_FOUND'")
    print(f"    cw-panel 元素: {r}")
except Exception as e:
    print(f"    检查失败: {e}")

# Step 5: 检查 __crawler_wizard 标记
print("[5] 检查 __crawler_wizard 标记...")
try:
    r = client.evaluate_js("String(window.__crawler_wizard)")
    print(f"    __crawler_wizard: {r}")
except Exception as e:
    print(f"    检查失败: {e}")

print("\n请在浏览器中确认：是否看到红色横幅和配置向导面板？")
print("等待 15 秒后关闭...")
time.sleep(15)

try:
    client.close_session()
except:
    pass
print("完成")
