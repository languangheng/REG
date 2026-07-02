# -*- coding: utf-8 -*-
"""
同花顺式复杂条件选股 - 稳定版
直接用 akshare 串行请求，加入重试和超时控制
"""

import warnings
warnings.filterwarnings("ignore")

import os, sys, io, time, random
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Step 1: 获取股票列表（带重试）
# ─────────────────────────────────────────────

def get_stock_list_with_retry(max_retries=3) -> pd.DataFrame:
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching stock list (attempt {attempt+1})...")
            df = ak.stock_info_a_code_name()
            df["code"] = df["code"].astype(str).str.zfill(6)
            # 过滤
            df = df[~df["code"].str.startswith("688")]  # 科创板
            df = df[~df["code"].str.startswith("300")]  # 创业板
            df = df[~df["code"].str.startswith("8")]   # 北交所
            df = df[~df["code"].str.startswith("43")]
            df = df[~df["code"].str.startswith("83")]
            df = df[~df["name"].str.contains("ST", na=False)]
            df = df[~df["code"].str.startswith("B")]
            logger.info(f"Stock list OK: {len(df)} stocks after filter")
            return df[["code", "name"]]
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    raise RuntimeError("Failed to fetch stock list after all retries")


# ─────────────────────────────────────────────
#  Step 2: 获取单只股票历史数据（带重试）
# ─────────────────────────────────────────────

def fetch_history_with_retry(code: str, max_retries=2) -> pd.DataFrame:
    """获取后复权日线，最多重试 max_retries 次"""
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=(datetime.now() - timedelta(days=700)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq"
            )
            if df is None or len(df) < 480:
                return pd.DataFrame()
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "涨跌幅": "pct_chg",
                "涨跌额": "chg", "换手率": "turnover",
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(random.uniform(0.5, 2.0))
    return pd.DataFrame()


# ─────────────────────────────────────────────
#  Step 3: 核心筛选逻辑
# ─────────────────────────────────────────────

def check_conditions(df: pd.DataFrame, code: str, name: str) -> dict | None:
    if len(df) < 500:
        return None

    close = df["close"].values
    high  = df["high"].values
    low   = df["low"].values

    today = close[-1]
    d8  = close[-9]
    d70 = close[-71]
    d80 = close[-81]

    def rh(w): return float(np.max(high[-w:]))

    high_60d  = rh(60)
    high_80d  = rh(80)
    high_240d = rh(240)
    high_480d = rh(480)
    low_min_3d = float(np.min(low[-3:]))
    ma8 = float(np.mean(close[-8:]))
    today_low = float(low[-1])

    ret_8d  = (today / d8  - 1) * 100
    ret_70d = (today / d70 - 1) * 100
    ret_80d = (today / d80 - 1) * 100

    # C1: 60日高点 == 80日高点
    if not np.isclose(high_60d, high_80d, atol=0.01): return None
    # C2: 近2天创3日新高次数 < 2
    cnt = 0
    for off in [2, 3]:
        if len(close) >= off + 4:
            if close[-off] > float(np.max(high[-off-4:-off])):
                cnt += 1
    if cnt >= 2: return None
    # C3: 80日涨幅>8% OR 70日涨幅>8%
    if not (ret_80d > 8 or ret_70d > 8): return None
    # C4: 240日高点 != 80日高点
    if np.isclose(high_240d, high_80d, atol=0.01): return None
    # C5: 240日高点 == 480日高点
    if not np.isclose(high_240d, high_480d, atol=0.01): return None
    # C6: 8日涨幅 > 5%
    if ret_8d <= 5: return None
    # C7: (最低-3日低点<3) OR (最低-8日均线<2)
    if not ((today_low - low_min_3d < 3) or (today_low - ma8 < 2)): return None

    return {
        "code": code, "name": name,
        "close": round(today, 2),
        "ret_8d": round(ret_8d, 2), "ret_70d": round(ret_70d, 2), "ret_80d": round(ret_80d, 2),
        "high_60d": round(high_60d, 2), "high_80d": round(high_80d, 2),
        "high_240d": round(high_240d, 2), "high_480d": round(high_480d, 2),
        "low_min_3d": round(low_min_3d, 2), "ma8": round(ma8, 2),
        "diff_3d": round(today_low - low_min_3d, 2),
        "diff_ma8": round(today_low - ma8, 2),
        "new_high_3d_count": cnt,
    }


# ─────────────────────────────────────────────
#  Step 4: 主筛选函数（串行 + 限速，防封禁）
# ─────────────────────────────────────────────

def run_screening():
    start_time = datetime.now()
    logger.info(f"=== Screening START {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===")

    stock_list = get_stock_list_with_retry()
    results = []
    total = len(stock_list)

    for i, (_, row) in enumerate(stock_list.iterrows(), 1):
        code, name = row["code"], row["name"]

        # 进度打印
        if i % 50 == 0 or i == 1:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            logger.info(f"  [{i:>5}/{total}] {i*100//total}%  Speed:{rate:.1f}/s  ETA:{eta:.0f}s")

        # 获取数据
        df = fetch_history_with_retry(code)
        if df.empty:
            continue

        # 检查条件
        result = check_conditions(df, code, name)
        if result:
            results.append(result)
            logger.info(f"  >>> MATCH #{len(results)}: {code} {name}  "
                        f"80d={result['ret_80d']}%  H240={result['high_240d']}  H480={result['high_480d']}")

        # 限速：每请求一次休息 0.1~0.3 秒，防止被封
        time.sleep(random.uniform(0.1, 0.3))

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"\n=== DONE in {elapsed:.0f}s ({elapsed/60:.1f}min) | Matches: {len(results)} ===")

    if results:
        df_result = pd.DataFrame(results).sort_values("ret_80d", ascending=False)
        return df_result
    return pd.DataFrame()


# ─────────────────────────────────────────────
#  Step 5: 输出结果
# ─────────────────────────────────────────────

def print_result(df: pd.DataFrame):
    if df.empty:
        print("\n" + "=" * 70)
        print("  NO STOCKS MATCH ALL CONDITIONS TODAY")
        print("=" * 70)
        return

    print("\n" + "=" * 110)
    print(f"  RESULTS: {len(df)} STOCKS MATCH ALL CONDITIONS")
    print("=" * 110)
    hdr = f"{'CODE':<8}{'NAME':<10}{'CLOSE':>8}{'8d%':>7}{'70d%':>7}{'80d%':>7}{'H60d':>8}{'H80d':>8}{'H240d':>9}{'H480d':>9}{'L3d':>7}{'MA8':>8}{'L3d-d':>8}{'MA8-d':>8}{'3dN':>4}"
    print(hdr)
    print("-" * 130)
    for _, r in df.iterrows():
        print(
            f"{r['code']:<8}{r['name']:<10}{r['close']:>8.2f}"
            f"{r['ret_8d']:>7.2f}{r['ret_70d']:>7.2f}{r['ret_80d']:>7.2f}"
            f"{r['high_60d']:>8.2f}{r['high_80d']:>8.2f}"
            f"{r['high_240d']:>9.2f}{r['high_480d']:>9.2f}"
            f"{r['low_min_3d']:>7.2f}{r['ma8']:>8.2f}"
            f"{r['diff_3d']:>8.2f}{r['diff_ma8']:>8.2f}{r['new_high_3d_count']:>4d}"
        )
    print("-" * 130)

    fn = f"screening_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(fn, index=False, encoding="utf-8-sig")
    print(f"\n  Saved: {fn}")


if __name__ == "__main__":
    start = datetime.now()
    result = run_screening()
    print_result(result)
    print(f"\nTotal time: {(datetime.now()-start).total_seconds():.0f}s")
