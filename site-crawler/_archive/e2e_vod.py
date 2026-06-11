"""端到端验证：列表页 -> voddetail -> vodplay -> stream URL（限制2个视频）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient
from crawler.parser import PageParser
import json

client = BrowserActClient(session="e2e_vod", browser_id=None)

# 第1步：列表页
print("[1] Opening list page...")
client.navigate("https://www.mimimi.top/vodshow/12--------2---.html")
client.wait(10)
md = client.get_markdown()
parser = PageParser(base_url="https://www.mimimi.top/vodshow/12--------2---.html")
page = parser.parse(md)
vod_links = page.video_links[:2]
print(f"  Total video links: {len(page.video_links)}, testing first 2")

# 第2步：逐个深入
for i, link in enumerate(vod_links, 1):
    print(f"\n[2.{i}] voddetail: {link['text'][:40]}")
    print(f"       URL: {link['url']}")
    client.navigate(link['url'])
    client.wait(6)
    play_links = client.get_voddetail_play_links()
    print(f"  Play links: {len(play_links)}")
    
    if play_links:
        play_url = play_links[0]['href']
        print(f"  [3.{i}] vodplay: {play_url}")
        client.navigate(play_url)
        client.wait(6)
        stream = client.get_vodplay_stream_url()
        print(f"  Stream URL: {stream.get('stream_url', '(none)')}")
        print(f"  Player iframe: {stream.get('player_iframe', '(none)')}")

client.close_session()
print("\nDone!")
