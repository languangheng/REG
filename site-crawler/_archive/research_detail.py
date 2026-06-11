"""调研：voddetail 和 artdetail 页面中图片和视频播放地址的 HTML 结构"""
from crawler.browser_act import BrowserActClient
import json

c = BrowserActClient(session="research", browser_id=None)

# 1. voddetail 页面
print("=== voddetail ===")
c.navigate("https://www.mimimi.top/voddetail/682172.html")
c.wait(8)

# 提取视频播放地址
js_video = """
JSON.stringify({
    // video 标签
    videos: [...document.querySelectorAll('video')].map(v => ({
        src: v.src,
        sources: [...v.querySelectorAll('source')].map(s => ({src: s.src, type: s.type})),
        poster: v.poster
    })),
    // iframe 播放器
    iframes: [...document.querySelectorAll('iframe')].map(f => ({src: f.src, id: f.id, class: f.className})),
    // 常见播放器容器
    player_divs: [...document.querySelectorAll('[id*="player"],[class*="player"]')].map(d => ({
        id: d.id, class: d.className, html_len: d.innerHTML.length, tag: d.tagName
    })),
    // 页面所有图片
    images: [...document.querySelectorAll('img')].map(img => img.src).filter(s => s && !s.startsWith('data:')),
    // background-image
    bg_images: [...document.querySelectorAll('[style*="background"]')].map(el => {
        const style = getComputedStyle(el);
        const bg = style.backgroundImage;
        const match = bg.match(/url\\(["']?([^"')]+)["']?\\)/);
        return match ? match[1] : null;
    }).filter(Boolean),
    title: document.title
})
"""
result = c.evaluate_js(js_video)
data = json.loads(result)
print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])

# 2. artdetail 页面
print("\n=== artdetail ===")
c.navigate("https://www.mimimi.top/artdetail-33507.html")
c.wait(8)

js_art = """
JSON.stringify({
    images: [...document.querySelectorAll('img')].map(img => img.src).filter(s => s && !s.startsWith('data:')),
    bg_images: [...document.querySelectorAll('[style*="background"]')].map(el => {
        const style = getComputedStyle(el);
        const bg = style.backgroundImage;
        const match = bg.match(/url\\(["']?([^"')]+)["']?\\)/);
        return match ? match[1] : null;
    }).filter(Boolean),
    title: document.title,
    img_count: document.querySelectorAll('img').length
})
"""
result2 = c.evaluate_js(js_art)
data2 = json.loads(result2)
print(json.dumps(data2, indent=2, ensure_ascii=False)[:3000])

c.close_session()
