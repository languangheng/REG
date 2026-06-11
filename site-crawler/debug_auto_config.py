"""调试脚本：直接对 mimimi 列表页跑 auto_config，结果写文件"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from crawler.browser_act import BrowserActClient
from crawler.auto_config import auto_config

URL = "https://www.mimimi.top/vodshow/12-----------.html"
OUT = os.path.join(os.path.dirname(__file__), "debug_result.txt")

logs = []
def on_log(line):
    logs.append(line)

client = BrowserActClient()

try:
    result = auto_config(URL, client, max_wait_cf=60, on_log=on_log)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("=== 结果 ===\n")
        f.write(f"errors: {result.errors}\n")
        f.write(f"success: {result.success}\n")
        f.write(f"\n=== 日志 ===\n")
        for line in logs:
            f.write(f"{line}\n")
        f.write(f"\n=== 配置 ===\n")
        f.write(f"{result.config}\n")
except Exception as e:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"ERROR: {e}\n")
        import traceback
        f.write(traceback.format_exc())
