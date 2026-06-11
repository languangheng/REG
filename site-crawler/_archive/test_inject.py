"""测试 JS 注入是否生效"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient

client = BrowserActClient(session="wizard_test", browser_id=None)

print("[1] 打开测试页...")
client.navigate("https://www.mimimi.top")
client.wait(8)

print("[2] 注入测试 JS（弹窗）...")
try:
    result = client.evaluate_js("document.title")
    print(f"  当前页面标题: {result}")
except Exception as e:
    print(f"  ❌ evaluate_js 失败: {e}")

print("[3] 注入简单覆盖层...")
simple_js = """
(function(){
  if (window.__cw_test) return;
  window.__cw_test = true;
  const d = document.createElement('div');
  d.id = 'cw-test';
  d.style.cssText = 'position:fixed;top:0;left:0;width:300px;background:red;color:#fff;z-index:2147483647;padding:20px;font-size:16px;';
  d.textContent = '✅ 注入成功！请看到这个红框。';
  document.body.appendChild(d);
  return 'injected';
})();
"""
try:
    result = client.evaluate_js(simple_js)
    print(f"  注入结果: {result}")
except Exception as e:
    print(f"  ❌ 注入失败: {e}")

print("[4] 等待 30 秒，请在浏览器中确认是否看到红色框...")
import time
time.sleep(30)

print("[5] 检查元素是否存在...")
result = client.evaluate_js("!!document.getElementById('cw-test')")
print(f"  cw-test 元素存在: {result}")

client.close_session()
print("完成")
