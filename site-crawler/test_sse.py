#!/usr/bin/env python3
"""测试 /api/analyze SSE 端点是否会立即推送心跳"""

import requests
import sys

url = "http://localhost:5050/api/analyze?url=https://www.baidu.com"
print(f"连接 SSE: {url}")
print("=" * 60)

try:
    response = requests.get(url, stream=True, timeout=30)
    response.encoding = "utf-8"

    print("✅ SSE 连接成功，等待事件...\n")

    event_count = 0
    for line in response.iter_lines(decode_unicode=True):
        if line:
            print(f"[{event_count}] {line}")
            event_count += 1

            # 如果收到心跳或日志，说明没有阻塞
            if line.startswith(": heartbeat") or line.startswith("data:"):
                print("✅ SSE 正常推送（没有阻塞 5 分钟）")
                break

        # 最多等 10 秒
        if event_count > 20:
            print("⚠️ 收到多个事件，但未收到完成信号")
            break

except requests.exceptions.Timeout:
    print("❌ 超时（30秒）")
except Exception as e:
    print(f"❌ 错误: {e}")
finally:
    print("\n" + "=" * 60)
    print(f"共收到 {event_count} 个事件")
    sys.exit(0)
