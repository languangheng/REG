#!/usr/bin/env python3
"""端到端测试 auto_config_multi (带日志输出)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from crawler.browser_act import BrowserActClient
from crawler.auto_config import auto_config_multi

c = BrowserActClient()
logs = []

def on_log(msg):
    logs.append(msg)
    print(msg)

result = auto_config_multi(
    url="https://www.mimimi.top/",
    client=c,
    max_wait_cf=30,
    max_categories=5,  # 先试5个
    on_log=on_log,
)

print(f"\n=== 结果 ===")
print(f"success: {result.success}")
print(f"errors: {result.errors}")
if result.config:
    eps = result.config.get("entry_points", [])
    print(f"entry_points count: {len(eps)}")
    for ep in eps:
        print(f"  - {ep.get('name','?')} | type={ep.get('type','?')} | url={ep.get('url','?')[:60]}")
    extra = result.config.get("_extra_categories", [])
    print(f"_extra_categories: {len(extra)}")
    for c2 in extra[:3]:
        print(f"  - [{c2.get('text')}] {c2.get('url')}")
else:
    print("NO CONFIG")
