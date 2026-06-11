"""深度优先验证：列表页 -> 详情页 -> 播放页，一条链走到底"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient

client = BrowserActClient(session="df_test", browser_id=None)

# 第1步：分类列表页
print("[1] Category page: https://www.mimimi.top/vodtype/12.html")
client.navigate("https://www.mimimi.top/vodtype/12.html")
client.wait(6)
md = client.get_markdown()
# 提取 voddetail 链接
js1 = """
JSON.stringify([...document.querySelectorAll('a')].filter(a => a.href.includes('/voddetail/')).map(a => ({
    href: a.href, text: a.textContent.trim().substring(0, 60)
})).slice(0, 5))
"""
links = json.loads(client.evaluate_js(js1))
print(f"  Found {len(links)} detail links, first 5:")
for l in links:
    print(f"    {l['text'][:50]} -> {l['href']}")

# 第2步：详情页
print("\n[2] Detail page: https://www.mimimi.top/voddetail/227277.html")
client.navigate("https://www.mimimi.top/voddetail/227277.html")
client.wait(6)
play_links = client.get_voddetail_play_links()
print(f"  Play links: {len(play_links)}")
for pl in play_links:
    print(f"    {pl['text']} -> {pl['href']}")

# 第3步：播放页 - 提取流地址
print("\n[3] Play page: https://www.mimimi.top/vodplay/227277-1-1.html")
client.navigate("https://www.mimimi.top/vodplay/227277-1-1.html")
client.wait(6)
stream = client.get_vodplay_stream_url()
print(f"  Stream URL: {stream.get('stream_url', '(none)')}")
print(f"  Player iframe: {stream.get('player_iframe', '(none)')}")

client.close_session()
print("\nDone!")
