"""调试：看链接提取和路径模式"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')

from crawler.browser_act import BrowserActClient
from crawler.fast_crawler import extract_links_from_markdown
from crawler.auto_config import _path_pattern, _cluster_links

client = BrowserActClient(session="auto_config_test", browser_id="direct_local_100797252049567848")
md = client.get_markdown()

print(f"Markdown 长度: {len(md)}")
print(f"前 500 字: {md[:500]}")
print()

links = extract_links_from_markdown(md, base_url="https://www.mimimi.top/vodshow/12-----------.html")
print(f"链接数: {len(links)}")
for l in links[:10]:
    print(f"  {l['text'][:40]} -> {l['url'][:80]}")
    print(f"    pattern: {_path_pattern(l['url'])}")

print()
clusters = _cluster_links(links, "https://www.mimimi.top/vodshow/12-----------.html")
print(f"聚类数: {len(clusters)}")
for c in clusters[:5]:
    print(f"  {c['pattern']}: {c['count']} 个")
