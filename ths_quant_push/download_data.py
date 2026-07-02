# -*- coding: utf-8 -*-
"""
全市场A股历史数据下载器
下载到本地 D:\Download\data\ 目录
每个股票一个 CSV，下次筛选直接读本地，速度飞快
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
import io
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

# 解决 Windows GBK stdout 问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DATA_DIR = r"D:\Download\data"
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def get_stock_list() -> pd.DataFrame:
    """获取全市场股票列表（含代码、名称）"""
    logger.info("Fetching A-share stock list...")
    df = ak.stock_info_a_code_name()
    df["code"] = df["code"].astype(str).str.zfill(6)
    logger.info(f"Total A-share stocks: {len(df)}")
    return df[["code", "name"]]


def _download_single(args):
    """下载单只股票历史数据（后复权，650天）"""
    code, name = args
    file_path = os.path.join(DATA_DIR, f"{code}.csv")

    # 如果已存在且文件非空，跳过
    if os.path.exists(file_path):
        try:
            existing = pd.read_csv(file_path, nrows=1)
            if len(existing) > 400:  # 已有足够数据
                return code, "skip"
        except Exception:
            pass

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=(
                datetime.now() - timedelta(days=700)
            ).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq"
        )
        if df is None or len(df) < 100:
            return code, "fail"

        # 统一列名
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount", "涨跌幅": "pct_chg",
            "涨跌额": "chg", "换手率": "turnover",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        return code, "ok"
    except Exception as e:
        return code, f"error:{e}"


def download_all():
    """主函数：并行下载全市场数据"""
    stock_list = get_stock_list()
    total = len(stock_list)
    ok_count = 0
    skip_count = 0
    fail_count = 0

    start_time = datetime.now()

    logger.info(f"=" * 60)
    logger.info(f"  Data Downloader - Target: {DATA_DIR}")
    logger.info(f"  Total stocks to process: {total}")
    logger.info(f"  Concurrent workers: 10")
    logger.info(f"=" * 60)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_download_single, (row["code"], row["name"])): row
            for _, row in stock_list.iterrows()
        }

        with tqdm(total=total, desc="Downloading", ncols=80) as pbar:
            for future in as_completed(futures):
                code, status = future.result()
                pbar.update(1)

                if status == "ok":
                    ok_count += 1
                elif status == "skip":
                    skip_count += 1
                else:
                    fail_count += 1
                    if fail_count <= 5:
                        logger.warning(f"  Failed: {code} -> {status}")

                # 每500支更新一次进度信息
                processed = ok_count + skip_count + fail_count
                if processed % 500 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = processed / elapsed if elapsed > 0 else 0
                    eta = (total - processed) / rate if rate > 0 else 0
                    logger.info(f"  [{processed}/{total}] OK:{ok_count} "
                                f"Skip:{skip_count} Fail:{fail_count} "
                                f"ETA:{eta:.0f}s")

    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info(f"\n" + "=" * 60)
    logger.info(f"  Download Summary")
    logger.info(f"  Time elapsed: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    logger.info(f"  Downloaded:  {ok_count}")
    logger.info(f"  Skipped:     {skip_count}  (already exists, >400 rows)")
    logger.info(f"  Failed:      {fail_count}")
    logger.info(f"  Data saved:  {DATA_DIR}")
    logger.info(f"=" * 60)

    # 统计文件大小
    total_size = 0
    file_count = 0
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            fp = os.path.join(DATA_DIR, f)
            total_size += os.path.getsize(fp)
            file_count += 1
    logger.info(f"  Total files: {file_count}  |  Total size: {total_size/1024/1024:.1f} MB")


if __name__ == "__main__":
    download_all()
