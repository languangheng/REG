# -*- coding: utf-8 -*-
"""
同花顺式复杂条件选股
条件：非科创/非创业/非ST/非北交所
+ 60日高点=80日高点 | 2日内创3日新高<2次
+ 80日涨幅>8%或70日涨幅>8% | 240日高点!=80日高点
+ 240日高点=480日高点 | 8日涨幅>5%
+ (最低-3日低点<3)或(最低-8日均线<2)
"""

import warnings
warnings.filterwarnings("ignore")

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import sys
import io

# 解决 Windows GBK stdout 问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Step 1: 获取全市场股票列表（过滤用）
# ─────────────────────────────────────────────

def get_stock_list() -> pd.DataFrame:
    """获取 A 股全市场股票列表，过滤科创/创业/北交所/ST"""
    logger.info("Fetching A-share stock list...")
    df = ak.stock_info_a_code_name()
    df["code"] = df["code"].astype(str).str.zfill(6)

    # 排除科创板 688xxx
    df = df[~df["code"].str.startswith("688")]
    # 排除创业板 300xxx
    df = df[~df["code"].str.startswith("300")]
    # 排除北交所 8xxxx / 43xxx / 83xxx
    df = df[~df["code"].str.startswith("8")]
    df = df[~df["code"].str.startswith("43")]
    df = df[~df["code"].str.startswith("83")]
    # 排除 ST
    df = df[~df["name"].str.contains("ST", na=False)]
    # 排除 B 股
    df = df[~df["code"].str.startswith("B")]

    logger.info(f"After filtering: {len(df)} stocks remain")
    return df[["code", "name"]]


# ─────────────────────────────────────────────
#  Step 2: 获取单只股票历史数据
# ─────────────────────────────────────────────

def fetch_stock_history(code: str) -> pd.DataFrame:
    """
    获取单只股票日线历史数据（需要 >= 500 交易日）
    akshare 会返回所有历史日线，我们取最后 650 天
    """
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=(
                datetime.now() - timedelta(days=700)
            ).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq"  # 后复权，保证价格可比
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
    except Exception as e:
        return pd.DataFrame()


# ─────────────────────────────────────────────
#  Step 3: 核心筛选逻辑
# ─────────────────────────────────────────────

def check_conditions(df: pd.DataFrame, code: str, name: str) -> dict | None:
    """
    对单只股票执行全部 7 条价格条件检查
    数据切片约定：索引 0 = 最旧，-1 = 今天（最后一行）
    """
    if len(df) < 500:
        return None

    close = df["close"].values
    high  = df["high"].values
    low   = df["low"].values

    today = close[-1]
    d8  = close[-9]
    d70 = close[-71]
    d80 = close[-81]

    # Rolling High（取最近 N 天的最大值）
    def rh(window):
        return float(np.max(high[-window:]))

    high_60d  = rh(60)
    high_80d  = rh(80)
    high_240d = rh(240)
    high_480d = rh(480)

    # Rolling Low
    low_min_3d = float(np.min(low[-3:]))

    # 均线
    ma8 = float(np.mean(close[-8:]))

    # 涨跌幅（%）
    ret_8d  = (today / d8  - 1) * 100
    ret_70d = (today / d70 - 1) * 100
    ret_80d = (today / d80 - 1) * 100

    # ── 条件判定 ──

    # C1: 60日高点 == 80日高点（±0.01 容差）
    if not np.isclose(high_60d, high_80d, atol=0.01):
        return None

    # C2: 近2天内，创3日新高的次数 < 2
    new_high_3d_count = 0
    # 昨天: close[-2] vs high[-5:-2]（再往前3天的最高）
    # 前天: close[-3] vs high[-6:-3]
    for offset in [2, 3]:  # offset=2=昨天, offset=3=前天
        if len(close) >= offset + 4:
            cur_close = close[-offset]
            prev_3_high = float(np.max(high[-offset - 4:-offset]))
            if cur_close > prev_3_high:
                new_high_3d_count += 1
    if new_high_3d_count >= 2:
        return None

    # C3: 80日涨幅 > 8%  OR  70日涨幅 > 8%
    if not (ret_80d > 8 or ret_70d > 8):
        return None

    # C4: 240日高点 != 80日高点
    if np.isclose(high_240d, high_80d, atol=0.01):
        return None

    # C5: 240日高点 == 480日高点
    if not np.isclose(high_240d, high_480d, atol=0.01):
        return None

    # C6: 8日涨幅 > 5%
    if ret_8d <= 5:
        return None

    # C7: (最低-3日低点<3) OR (最低-8日均线<2)
    today_low = float(low[-1])
    cond_a = (today_low - low_min_3d) < 3
    cond_b = (today_low - ma8) < 2
    if not (cond_a or cond_b):
        return None

    # ── 全部通过 ──
    today_low = float(low[-1])
    return {
        "code": code,
        "name": name,
        "close": round(today, 2),
        "ret_8d":   round(ret_8d, 2),
        "ret_70d":  round(ret_70d, 2),
        "ret_80d":  round(ret_80d, 2),
        "high_60d": round(high_60d, 2),
        "high_80d": round(high_80d, 2),
        "high_240d": round(high_240d, 2),
        "high_480d": round(high_480d, 2),
        "low_min_3d": round(low_min_3d, 2),
        "ma8":       round(ma8, 2),
        "diff_3d":   round(today_low - low_min_3d, 2),
        "diff_ma8":  round(today_low - ma8, 2),
        "new_high_3d_count": new_high_3d_count,
    }


# ─────────────────────────────────────────────
#  Step 4: 并行全市场筛选
# ─────────────────────────────────────────────

def _screening_single(args):
    code, name = args
    df = fetch_stock_history(code)
    if df.empty:
        return None
    return check_conditions(df, code, name)


def run_screening() -> pd.DataFrame:
    """主函数：全市场并行筛选"""
    start_time = datetime.now()
    logger.info(f"=== Screening START {start.strftime('%Y-%m-%d %H:%M:%S')} ===")

    stock_list = get_stock_list()
    results = []

    # 并行：max_workers 控制并发（akshare 有限流，8-10 为宜）
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_screening_single, (row["code"], row["name"])): row
            for _, row in stock_list.iterrows()
        }

        done = 0
        total = len(futures)
        for future in as_completed(futures):
            done += 1
            if done % 200 == 0:
                logger.info(f"  Progress: {done}/{total}  ({done*100//total}%)")
            result = future.result()
            if result is not None:
                results.append(result)
                logger.info(f"  >>> MATCH: {result['code']} {result['name']}  "
                            f"80d={result['ret_80d']}%  "
                            f"240d_high={result['high_240d']}")

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"=== Screening DONE in {elapsed:.0f}s | "
                f"Matches: {len(results)} ===")

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values("ret_80d", ascending=False)
        return df_result
    return pd.DataFrame()


# ─────────────────────────────────────────────
#  Step 5: 打印结果
# ─────────────────────────────────────────────

def print_result(df: pd.DataFrame):
    if df.empty:
        print("\n" + "=" * 70)
        print("  NO STOCKS MATCH ALL CONDITIONS TODAY")
        print("  Possible reasons:")
        print("  - Market-wide correction (conditions too strict)")
        print("  - Insufficient historical data")
        print("  - Adjust parameters (e.g. lower 8% threshold)")
        print("=" * 70)
        return

    cols = ["code", "name", "close", "ret_8d", "ret_70d", "ret_80d",
            "high_60d", "high_80d", "high_240d", "high_480d",
            "low_min_3d", "ma8", "diff_3d", "diff_ma8", "new_high_3d_count"]

    print("\n" + "=" * 100)
    print(f"  RESULTS: {len(df)} STOCKS MATCH ALL CONDITIONS")
    print("=" * 100)
    print(f"{'CODE':<8} {'NAME':<10} {'CLOSE':>7} {'8d%':>7} {'70d%':>7} {'80d%':>7} "
          f"{'H60d':>7} {'H80d':>7} {'H240d':>8} {'H480d':>8} "
          f"{'L3d':>6} {'MA8':>7} {'L3d-dif':>8} {'MA8-dif':>8} {'3dN':>4}")
    print("-" * 100)

    for _, row in df.iterrows():
        print(
            f"{row['code']:<8} {row['name']:<10} {row['close']:>7.2f} "
            f"{row['ret_8d']:>7.2f} {row['ret_70d']:>7.2f} {row['ret_80d']:>7.2f} "
            f"{row['high_60d']:>7.2f} {row['high_80d']:>7.2f} {row['high_240d']:>8.2f} {row['high_480d']:>8.2f} "
            f"{row['low_min_3d']:>6.2f} {row['ma8']:>7.2f} "
            f"{row['diff_3d']:>8.2f} {row['diff_ma8']:>8.2f} {row['new_high_3d_count']:>4d}"
        )

    print("-" * 100)
    print("\n  [Condition Verification Guide]")
    print("  C1: 60d_H == 80d_H  (high_60d == high_80d)")
    print("  C2: 2d_3dNH_count < 2")
    print("  C3: 80d%>8 OR 70d%>8")
    print("  C4: 240d_H != 80d_H")
    print("  C5: 240d_H == 480d_H")
    print("  C6: 8d% > 5")
    print("  C7: (low-3d_low<3) OR (low-MA8<2)")

    # 保存 CSV
    csv_name = f"screening_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(csv_name, index=False, encoding="utf-8-sig")
    print(f"\n  CSV saved: {csv_name}")


# ─────────────────────────────────────────────
#  Entry
# ─────────────────────────────────────────────

if __name__ == "__main__":
    start = datetime.now()
    result = run_screening()
    print_result(result)
    print(f"\nTotal time: {(datetime.now()-start).total_seconds():.0f}s")
