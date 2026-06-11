"""调研：voddetail 页面中播放按钮和播放链接"""
from crawler.browser_act import BrowserActClient
import json

c = BrowserActClient(session="vod_research", browser_id=None)
c.navigate("https://www.mimimi.top/voddetail/226212.html")
c.wait(8)

# 提取播放相关链接
js = """
JSON.stringify({
    // 所有 a 链接中包含 play/vodplay 的
    play_links: [...document.querySelectorAll('a')].filter(a => {
        const href = a.href || '';
        return href.includes('vodplay') || href.includes('/play/') || href.includes('play-');
    }).map(a => ({
        href: a.href,
        text: a.textContent.trim().substring(0, 50),
        class: a.className,
        id: a.id
    })),
    // 带有"播放"文本的按钮/链接
    play_buttons: [...document.querySelectorAll('a, button')].filter(el => {
        const text = el.textContent.trim();
        return text.includes('播放') || text.includes('立即') || text.includes('在线') || text.includes('开始');
    }).map(el => ({
        tag: el.tagName,
        href: el.href || '',
        text: el.textContent.trim().substring(0, 50),
        class: el.className,
        id: el.id,
        onclick: el.getAttribute('onclick') || ''
    })),
    // 播放线路/选集
    tab_links: [...document.querySelectorAll('[class*="tab"] a, [class*="playlist"] a, [class*="episode"] a, [role="tab"] a')].map(a => ({
        href: a.href,
        text: a.textContent.trim().substring(0, 30),
        class: a.className
    })),
    title: document.title
})
"""
result = c.evaluate_js(js)
data = json.loads(result)
print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])

c.close_session()
