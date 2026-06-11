"""端到端验证：列表页 → voddetail → vodplay 播放链接"""
from crawler.browser_act import BrowserActClient
from crawler.parser import PageParser
import json

client = BrowserActClient(session="e2e_test", browser_id=None)

# 第1步：列表页提取 voddetail 链接
print("=== 第1步：列表页 ===")
client.navigate("https://www.mimimi.top/vodshow/12--------2---.html")
client.wait(10)
md = client.get_markdown()
parser = PageParser(base_url="https://www.mimimi.top/vodshow/12--------2---.html")
page = parser.parse(md)
vod_links = page.video_links[:1]  # 只取第1个
print(f"  视频: {len(page.video_links)}, 取第1个: {vod_links[0]['url']}")

# 第2步：进入 voddetail，找播放链接
print("\n=== 第2步：voddetail → 播放链接 ===")
client.navigate(vod_links[0]['url'])
client.wait(6)
play_links = client.get_voddetail_play_links()
print(f"  播放链接: {json.dumps(play_links, ensure_ascii=False, indent=2)}")

# 第3步：进入 vodplay 页面，看看有什么
if play_links:
    print("\n=== 第3步：vodplay 页面 ===")
    play_url = play_links[0]['href']
    client.navigate(play_url)
    client.wait(6)
    
    # 看看有没有 video 标签或 iframe
    js = """
    JSON.stringify({
        videos: [...document.querySelectorAll('video')].map(v => ({src: v.src, poster: v.poster})),
        iframes: [...document.querySelectorAll('iframe')].map(f => ({src: f.src, id: f.id, class: f.className})),
        player_divs: [...document.querySelectorAll('[id*="player"],[class*="player"]')].map(d => ({id: d.id, class: d.className, tag: d.tagName})),
    })
    """
    result = client.evaluate_js(js)
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

client.close_session()
print("\n✅ 验证完成")
