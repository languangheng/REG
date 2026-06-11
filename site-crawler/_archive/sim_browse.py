"""模拟用户浏览，触发 HAR 录制事件"""
import sys, time
sys.path.insert(0, r'C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler')
from crawler.browser_act import BrowserActClient

c = BrowserActClient(session='har_wizard', browser_id='direct_local_100797252049567848')

# 1. 当前状态
s = c.parsed_state()
print(f'[1] Current: {s.url}')
print(f'    Title: {s.title[:50]}')

# 2. 获取 markdown，找视频链接
md = c.get_markdown()
import re
links = re.findall(r'\[([^\]]+)\]\((https?://[^)]*voddetail/\d+\.html)\)', md)
print(f'[2] Found {len(links)} video links')
if links:
    name, url = links[0]
    print(f'    Navigating to: {name[:30]} -> {url}')
    c.navigate(url)
    time.sleep(8)

    s2 = c.parsed_state()
    print(f'[3] Now at: {s2.url}')
    print(f'    Title: {s2.title[:50]}')

    # 3. 找播放链接
    md2 = c.get_markdown()
    play_links = re.findall(r'\((https?://[^)]*vodplay/[^)]+)\)', md2)
    if play_links:
        print(f'[4] Found {len(play_links)} play links')
        print(f'    Navigating to: {play_links[0][:60]}')
        c.navigate(play_links[0])
        time.sleep(8)

        s3 = c.parsed_state()
        print(f'[5] Now at: {s3.url}')
        print(f'    Title: {s3.title[:50]}')

        # 检测 m3u8
        reqs = c.network_requests(filter_str='m3u8')
        m3u8s = [r for r in reqs if r.get('resource_type') in ('XHR', 'Fetch')]
        for r in m3u8s[:3]:
            print(f'    m3u8: {r.get("url", "")[:80]}')
    else:
        print('[4] No play links found')
        # 尝试获取所有链接
        all_links = re.findall(r'\((https?://[^)]+)\)', md2)
        play_like = [l for l in all_links if 'play' in l or 'vod' in l]
        print(f'    Play-like links: {play_like[:3]}')
