"""测试方案 A：一键自动配置"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')

from crawler.browser_act import BrowserActClient
from crawler.auto_config import auto_config, format_config_yaml

SESSION = "test1"
BROWSER_ID = "direct_local_100797252049567848"

client = BrowserActClient(session=SESSION, browser_id=BROWSER_ID)

result = auto_config(
    list_url="https://www.mimimi.top/vodshow/12-----------.html",
    client=client,
)

print("\n" + "=" * 60)
print("执行日志:")
for line in result.log:
    print(f"  {line}")

if result.errors:
    print("\n错误:")
    for e in result.errors:
        print(f"  ❌ {e}")

if result.success:
    print("\n" + "=" * 60)
    print("生成的配置:")
    print(format_config_yaml(result.config))
else:
    print("\n❌ 配置生成失败")
