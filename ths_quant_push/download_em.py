# -*- coding: utf-8 -*-
"""
全市场A股历史数据下载器 - 东方财富直连版
D:\Download\data\  每个股票一个 CSV（后复权日线，650天）
"""

import warnings
warnings.filterwarnings("ignore")

import os, sys, io, time, requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DATA_DIR = r"D:\Download\data"
os.makedirs(DATA_DIR, exist_ok=True)

# HTTP 会话（复用连接）
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://quote.eastmoney.com/",
})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 计数器（线程安全）
_count_lock = Lock()
ok_count = skip_count = fail_count = 0


# ─────────────────────────────────────────────
#  Step 1: 获取全市场股票列表
# ─────────────────────────────────────────────

def get_em_stock_list() -> list[tuple[str, str, str]]:
    """
    从东方财富获取 A 股全量股票列表
    返回: [(code, name, market_id), ...]
    市场ID格式: 1=沪市主板, 0=深市
    """
    all_stocks = []

    # 东方财富市场代码：
    # m:0+t:6  深市主板
    # m:0+t:80 沪市主板
    # m:1+t:2  沪市（包含主板）
    # m:0+t:13 深市（包含主板和创业板）
    markets = [
        ("0", "m:0+t:6+m:0+t:80", "深圳+沪市主板"),
        # 排除 300(创业板) 和 002(中小板) / 8xxxx(北交所) 在下面过滤
    ]

    for mtype, fs_filter, desc in markets:
        page = 1
        while True:
            url = (
                "http://80.push2.eastmoney.com/api/qt/clist/get"
                f"?pn={page}&pz=500&po=1&np=1"
                f"&ut=bd1d9ddb04089700cf9c27f6f7426281"
                f"&fltt=2&invt=2&fid=f3"
                f"&fs={fs_filter}"
                f"&fields=f12,f14"
            )
            try:
                r = _session.get(url, timeout=10)
                data = r.json()
                items = data["data"]["diff"]
                total = data["data"]["total"]
            except Exception as e:
                logger.warning(f"获取列表第{page}页失败: {e}")
                break

            for item in items:
                code = item["f12"]  # "600519"
                name = item["f14"]  # "贵州茅台"

                # 过滤掉科创板(688)、创业板(300)、北交所(8/43/83)、ST
                if code.startswith(("688", "300", "8", "43", "83", "B")):
                    continue
                if "ST" in name or "*ST" in name:
                    continue

                # 市场ID: 沪市=1, 深市=0
                market_id = "1" if code.startswith("6") else "0"
                all_stocks.append((code, name, market_id))

            logger.info(f"  {desc} page{page}: +{len(items)}, total so far: {len(all_stocks)}")
            if page * 500 >= total:
                break
            page += 1
            time.sleep(0.1)

    logger.info(f"\nTotal filtered stocks: {len(all_stocks)}")
    return all_stocks


# ─────────────────────────────────────────────
#  Step 2: 下载单只股票历史K线（东方财富接口）
# ─────────────────────────────────────────────

def download_single(args) -> tuple[str, str]:
    """
    下载单只股票历史K线，保存为 CSV
    返回: (code, status)
    """
    global ok_count, skip_count, fail_count

    code, name, market_id = args
    file_path = os.path.join(DATA_DIR, f"{code}.csv")

    # 已存在且有足够数据 → 跳过
    if os.path.exists(file_path):
        try:
            existing = pd.read_csv(file_path, nrows=2, encoding="utf-8-sig")
            if len(existing) >= 400:
                with _count_lock:
                    skip_count += 1
                return code, "skip"
        except Exception:
            pass

    # secid: 0.代码=深市, 1.代码=沪市
    secid = f"{market_id}.{code}"

    # 请求最近 700 天的后复权日线数据
    # fqt=1: 后复权
    # klt=101: 日K线
    url = (
        "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}"
        f"&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
        f"&klt=101&fqt=1"
        f"&beg={(datetime.now() - timedelta(days=750)).strftime('%Y%m%d')}"
        f"&end=20500101"
        f"&smplmt=750&lmt=1000000"
    )

    try:
        r = _session.get(url, timeout=15)
        data = r.json()
        klines = data["data"]["klines"]  # list of "date,open,close,high,low,..."
        if not klines:
            with _count_lock:
                fail_count += 1
            return code, "empty"

        rows = []
        for line in klines:
            parts = line.split(",")
            rows.append({
                "date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
                "amount": float(parts[6]),
                "pct_chg": float(parts[8]) if len(parts) > 8 else 0.0,
            })

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        with _count_lock:
            ok_count += 1
        return code, "ok"

    except Exception as e:
        with _count_lock:
            fail_count += 1
        return code, f"error:{str(e)[:50]}"


# ─────────────────────────────────────────────
#  Step 3: 主函数
# ─────────────────────────────────────────────

def download_all():
    global ok_count, skip_count, fail_count
    ok_count = skip_count = fail_count = 0

    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("  Data Downloader - EastMoney Direct API")
    logger.info(f"  Target: {DATA_DIR}")
    logger.info("=" * 60)

    # Step 1: 获取股票列表
    stock_list = get_em_stock_list()
    total = len(stock_list)
    if total == 0:
        logger.error("No stocks found! Check network.")
        return

    logger.info(f"\nStarting download for {total} stocks...")
    logger.info(f"Workers: 10  |  Batch: 500")

    # Step 2: 并行下载
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(download_single, stock): stock
            for stock in stock_list
        }

        done = 0
        last_log_time = time.time()

        for future in as_completed(futures):
            done += 1
            code, status = future.result()

            now = time.time()
            if now - last_log_time >= 5:  # 每5秒输出一次进度
                elapsed = now - start_time
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                logger.info(
                    f"  [{done:>5}/{total}] "
                    f"OK:{ok_count} Skip:{skip_count} Fail:{fail_count} "
                    f"Speed:{rate:.1f}/s ETA:{eta:.0f}s"
                )
                last_log_time = now

            if status not in ("ok", "skip") and fail_count <= 3:
                logger.warning(f"  Failed {code}: {status}")

    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info(f"\n" + "=" * 60)
    logger.info(f"  Download Summary")
    logger.info(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    logger.info(f"  Downloaded: {ok_count}")
    logger.info(f"  Skipped:    {skip_count}  (already exists)")
    logger.info(f"  Failed:     {fail_count}")
    logger.info("=" * 60)

    # 文件统计
    total_size = 0
    file_count = 0
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            total_size += os.path.getsize(os.path.join(DATA_DIR, f))
            file_count += 1
    logger.info(f"  Files: {file_count}  |  Size: {total_size/1024/1024:.1f} MB")


if __name__ == "__main__":
    download_all()
