"""等 CF 通过后模拟用户浏览"""
import sys, time
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')
from crawler.browser_act import BrowserActClient
import re

c = BrowserActClient(session='har_wizard', browser_id='direct_local_100797252049567848')

# 等 CF
print('Waiting for CF bypass...')
for i in range(15):
    time.sleep(3)
    s = c.parsed_state()
    t = s.title
    if 'moment' not in t.lower() and '稍候' not in t and 'verify' not in t.lower():
        print(f'CF passed! Title: {t[:50]}')
        break
    print(f'  {i+1}: {t[:40]}')

print(f'URL: {s.url}')

# 获取视频链接
md = c.get_markdown()
links = re.findall(r'\[([^\]]+)\]\((https?://[^)]*voddetail/\d+\.html)\)', md)
print(f'Video links: {len(links)}')

if links:
    name, url = links[0]
    print(f'Navigate -> {name[:30]}')
    c.navigate(url)
    time.sleep(6)
    s2 = c.parsed_state()
    print(f'At: {s2.url}')

    # 找播放链接
    md2 = c.get_markdown()
    play_links = re.findall(r'\((https?://[^)]*vodplay/[^)]+)\)', md2)
    print(f'Play links: {len(play_links)}')
    if play_links:
        c.navigate(play_links[0])
        time.sleep(6)
        s3 = c.parsed_state()
        print(f'At: {s3.url}')

        # m3u8
        reqs = c.network_requests(filter_str='m3u8')
        m3u8s = [r for r in reqs if r.get('resource_type') in ('XHR', 'Fetch')]
        for r in m3u8s[:3]:
            u = r.get('url', '')
            print(f'  m3u8: {u[:80]}')

print('Done - check wizard_har page for events')
