"""检查 HAR 录制状态"""
import sys
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')
from crawler.browser_act import BrowserActClient

c = BrowserActClient(session='har_wizard', browser_id='direct_local_100797252049567848')
s = c.parsed_state()
print(f'URL: {s.url}')

reqs = c.network_requests()
print(f'Total network requests: {len(reqs)}')
m3u8 = [r for r in reqs if 'm3u8' in r.get('url', '')]
print(f'M3U8 requests: {len(m3u8)}')
for r in m3u8[:2]:
    print(f'  {r.get("url", "")[:80]}')
