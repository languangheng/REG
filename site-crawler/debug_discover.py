#!/usr/bin/env python3
"""测试 _discover_category_links 修复"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from crawler.browser_act import BrowserActClient
from crawler.auto_config import _discover_category_links

c = BrowserActClient()
c.ensure_session("https://www.mimimi.top", max_wait_cf=15)
cats = _discover_category_links(c, "https://www.mimimi.top")
print("Found:", len(cats))
for cat in cats:
    nav = "Y" if cat["is_nav"] else "N"
    text = cat["text"][:20].replace("\n", " ")
    print(f"  nav={nav} [{text}] {cat['path']}")
