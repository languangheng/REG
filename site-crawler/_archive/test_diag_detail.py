"""诊断详情页的播放按钮"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')

from crawler.browser_act import BrowserActClient

client = BrowserActClient(session="test1", browser_id="direct_local_100797252049567848")
snap = client.parsed_state()

print(f"URL: {snap.url}")
print(f"Title: {snap.title}")
print()

# 找所有包含"播放"的元素
for el in snap.elements:
    t = el.text.strip()
    if "播放" in t or "play" in t.lower() or "btn" in (el.class_name or "").lower():
        print(f"[{el.index}] tag={el.tag} cls='{el.class_name}' text='{t[:50]}'")
