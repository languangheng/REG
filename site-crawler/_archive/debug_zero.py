"""调研：0 图片的 artdetail 页面"""
from crawler.browser_act import BrowserActClient
import json

c = BrowserActClient(session="debug0", browser_id=None)

# 测试 0 图片的页面
for url in ["https://www.mimimi.top/artdetail-15486.html", "https://www.mimimi.top/artdetail-14775.html"]:
    print(f"\n=== {url} ===")
    c.navigate(url)
    c.wait(6)

    js = """
    JSON.stringify({
        read_tpc: document.getElementById('read_tpc') ? document.getElementById('read_tpc').querySelectorAll('img').length : null,
        all_img_count: document.querySelectorAll('img').length,
        content_imgs: (() => {
            const content = document.querySelector('[class*="article"]') || document.querySelector('[class*="content"]') || document.querySelector('[id*="content"]');
            return content ? [...content.querySelectorAll('img')].map(i => i.src).filter(s => s && !s.startsWith('data:')) : [];
        })(),
        all_imgs: [...document.querySelectorAll('img')].map(i => ({
            src: i.src, pid: i.parentElement?.id, pclass: i.parentElement?.className, gpclass: i.parentElement?.parentElement?.className
        })).filter(i => !i.src.includes('logo') && !i.src.includes('icon') && !i.src.includes('static') && !i.src.startsWith('data:')),
    })
    """
    result = c.evaluate_js(js)
    data = json.loads(result)
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

c.close_session()
