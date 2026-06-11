"""启动 Flask + 初始化浏览器会话（已过 CF）"""
import sys, time
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')
from crawler.browser_act import BrowserActClient

# 创建会话并导航
c = BrowserActClient(session="har_wizard", browser_id="direct_local_100797252049567848")
print("Creating session & navigating...")
c.navigate("https://www.mimimi.top/vodshow/12-----------.html")

# 等 CF
print("Waiting for CF bypass...")
for i in range(20):
    time.sleep(3)
    s = c.parsed_state()
    t = s.title
    if 'moment' not in t.lower() and '稍候' not in t and 'verify' not in t.lower() and 'checking' not in t.lower():
        print(f"CF passed! Title: {t[:60]}")
        print(f"URL: {s.url}")
        break
    print(f"  {i+1}: {t[:40]}")
else:
    print("CF not passed after 60s - may need manual intervention")
    print(f"Current: {s.url} | {s.title}")
