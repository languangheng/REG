"""快速检查 HAR 录制状态"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')
from crawler.browser_act import BrowserActClient

c = BrowserActClient(session='har_wizard', browser_id='direct_local_100797252049567848')
s = c.parsed_state()
print(f'Current page: {s.url}')
print(f'Title: {s.title}')

# 检查 m3u8
reqs = c.network_requests(filter_str='m3u8')
for r in reqs[:3]:
    url = r.get('url', '')
    print(f'  m3u8: {url[:80]}')
