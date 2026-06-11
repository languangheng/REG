"""调试脚本2：检查翻页区域的 DOM 元素"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from crawler.browser_act import BrowserActClient

URL = "https://www.mimimi.top/vodshow/12-----------.html"

print(f"=== 调试翻页 DOM ===", flush=True)
client = BrowserActClient()

try:
    snap = client.ensure_session(url=URL, max_wait_cf=60)
    print(f"页面加载: {snap.title}", flush=True)

    # 滚动到底部
    for _ in range(8):
        client.scroll_down()

    snap = client.parsed_state()
    print(f"\n=== 翻页区域元素 ===", flush=True)

    # 找所有可能是翻页的元素
    for el in snap.elements:
        text = (el.text or "").strip()
        # 数字文本 or 翻页关键词
        if text.isdigit() or any(kw in text.lower() for kw in ["下一页", "下页", "next", "上一页", "上页", "prev"]):
            print(f"  index={el.index} tag={el.tag} text='{text}' href='{el.href}' class='{el.class_name}' role='{el.role}'", flush=True)

    # 也看看 find_next_page 返回什么
    next_el = snap.find_next_page()
    if next_el:
        print(f"\n  find_next_page => index={next_el.index} text='{next_el.text}' href='{next_el.href}' class='{next_el.class_name}'", flush=True)
    else:
        print(f"\n  find_next_page => None", flush=True)

except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
