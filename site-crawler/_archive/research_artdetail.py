"""调研：artdetail 页面中内容图片 vs 装饰图片的区分"""
from crawler.browser_act import BrowserActClient
import json

c = BrowserActClient(session="research2", browser_id=None)
c.navigate("https://www.mimimi.top/artdetail-38385.html")
c.wait(8)

js = """
JSON.stringify({
    // 所有 img 的详细信息
    imgs: [...document.querySelectorAll('img')].map(img => ({
        src: img.src,
        width: img.naturalWidth || img.width,
        height: img.naturalHeight || img.height,
        class: img.className,
        parent_class: img.parentElement?.className || '',
        parent_id: img.parentElement?.id || '',
        grandparent_class: img.parentElement?.parentElement?.className || '',
        alt: img.alt || '',
        loading: img.loading || ''
    })),
    // 内容区域检测
    content_area: (() => {
        const candidates = document.querySelectorAll('article, [class*="content"], [class*="article"], [id*="content"], [class*="detail"], [id*="detail"]');
        return [...candidates].map(el => ({
            tag: el.tagName,
            id: el.id,
            class: el.className,
            img_count: el.querySelectorAll('img').length
        }));
    })(),
    bg_images: [...document.querySelectorAll('[style*="background"]')].map(el => {
        const style = getComputedStyle(el);
        const bg = style.backgroundImage;
        const match = bg.match(/url\\(["']?([^"')]+)["']?\\)/);
        return match ? match[1] : null;
    }).filter(Boolean)
})
"""
result = c.evaluate_js(js)
data = json.loads(result)
print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])
c.close_session()
