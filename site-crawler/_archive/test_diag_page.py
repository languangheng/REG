"""诊断翻页按钮"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')

from crawler.browser_act import BrowserActClient

client = BrowserActClient(session="test1", browser_id="direct_local_100797252049567848")
snap = client.parsed_state()

# 找所有 btn 元素
for el in snap.elements:
    if "btn" in (el.class_name or ""):
        print(f"[{el.index}] tag={el.tag} cls='{el.class_name}' text='{el.text.strip()[:30]}' href='{getattr(el, 'href', '')}'")
