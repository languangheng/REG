"""统一日志框架 — 每次运行独立目录

每次进程启动时，在 log/<时间戳>/ 下创建独立目录：
    log/20260612_091834/all.log   — 全量日志（DEBUG/INFO/WARNING/ERROR）
    log/20260612_091834/err.log   — 异常日志（仅 WARNING/ERROR）

排错规则：
    快速定位异常 → 看最新目录的 err.log
    查看完整流程 → 看最新目录的 all.log

工具函数：
    get_latest_log_dir()  — 返回最新的日志目录路径
    LOG_SESSION_DIR       — 本次运行的日志目录路径

使用方式：
    from crawler.logger import get_logger
    log = get_logger("模块名")
    log.info("正常消息")
    log.error("异常消息")
"""

import os
import sys
import logging
from datetime import datetime

# ── 日志根目录（项目根/log/） ─────────────────────────────────
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_BASE_DIR = os.path.join(_project_root, "log")

# ── 本次运行的时间戳目录（进程级唯一，模块导入时确定）─────────────
_session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_SESSION_DIR = os.path.join(LOG_BASE_DIR, _session_ts)
os.makedirs(LOG_SESSION_DIR, exist_ok=True)

ALL_LOG_PATH = os.path.join(LOG_SESSION_DIR, "all.log")
ERR_LOG_PATH = os.path.join(LOG_SESSION_DIR, "err.log")

# ── 日志格式 ─────────────────────────────────────────────────
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── 全量日志 Handler ─────────────────────────────────────────
_all_handler = logging.FileHandler(ALL_LOG_PATH, encoding="utf-8")
_all_handler.setLevel(logging.DEBUG)
_all_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── 异常日志 Handler ─────────────────────────────────────────
_err_handler = logging.FileHandler(ERR_LOG_PATH, encoding="utf-8")
_err_handler.setLevel(logging.WARNING)  # WARNING + ERROR
_err_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── 控制台 Handler（保留界面日志）─────────────────────────────
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))


def get_logger(name: str) -> logging.Logger:
    """获取统一日志器。

    Args:
        name: 模块名（如 "site_manager", "group_crawler"）

    Returns:
        Logger 实例，已配置全量 + 异常 + 控制台三个 Handler
    """
    logger = logging.getLogger(name)

    # 防止重复添加 Handler（多次调用 get_logger 时）
    if not logger.handlers:
        logger.addHandler(_all_handler)
        logger.addHandler(_err_handler)
        logger.addHandler(_console_handler)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 不传给 root logger

    return logger


def get_latest_log_dir() -> str | None:
    """返回最新一次运行的日志目录路径（按时间戳排序取最新）。

    用于排错时快速定位最新日志：
        latest = get_latest_log_dir()
        # latest -> "log/20260612_091834"

    Returns:
        最新日志目录的绝对路径，或 None（如果 log/ 目录不存在）
    """
    if not os.path.isdir(LOG_BASE_DIR):
        return None
    entries = sorted(
        [
            e for e in os.listdir(LOG_BASE_DIR)
            if os.path.isdir(os.path.join(LOG_BASE_DIR, e))
        ],
        reverse=True,
    )
    if not entries:
        return None
    return os.path.join(LOG_BASE_DIR, entries[0])


# ── 启动日志（写入本次会话目录）────────────────────────────────
_init_log = get_logger("logger")
_init_log.info("日志会话开始: session=%s, dir=%s", _session_ts, LOG_SESSION_DIR)
_init_log.info("  all.log  → %s", ALL_LOG_PATH)
_init_log.info("  err.log  → %s", ERR_LOG_PATH)
