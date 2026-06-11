"""调试 voddetail 链接"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')
from crawler.browser_act import BrowserActClient
from crawler.fast_crawler import extract_links_from_markdown
from crawler.auto_config import _path_pattern

client = BrowserActClient(session="auto_config_test", browser_id="direct_local_100797252049567848")
md = client.get_markdown()
links = extract_links_from_markdown(md, base_url="https://www.mimimi.top/vodshow/12-----------.html")

# 看 voddetail 链接
for l in links:
    pat = _path_pattern(l["url"])
    if "voddetail" in pat:
        text = l["text"][:30]
        url = l["url"][:60]
        print(f"{pat}: {text} -> {url}")

# 统计各 pattern 数量
from collections import Counter
patterns = Counter(_path_pattern(l["url"]) for l in links)
for pat, cnt in patterns.most_common(10):
    print(f"  {pat}: {cnt}")
