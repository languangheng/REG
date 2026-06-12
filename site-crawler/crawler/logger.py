"""统一日志框架 — 双文件日志（全量 + 异常）

使用方式:
    from crawler.logger import get_logger
    log = get_logger("模块名")
    log.info("正常消息")
    log.error("异常消息")

日志文件:
    out/all.log     — 全量日志（DEBUG/INFO/WARNING/ERROR）
    out/error.log   — 异常日志（仅 WARNING/ERROR）

排错只看日志文件:
    快速定位异常 → 看 out/error.log
    查看完整流程 → 看 out/all.log
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# ── 日志目录 ─────────────────────────────────────────────
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_project_root, "out")
os.makedirs(LOG_DIR, exist_ok=True)

ALL_LOG_PATH = os.path.join(LOG_DIR, "all.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error.log")

# ── 日志格式 ─────────────────────────────────────────────
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── 全量日志 Handler ─────────────────────────────────────
_all_handler = RotatingFileHandler(
    ALL_LOG_PATH,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=3,
    encoding="utf-8",
)
_all_handler.setLevel(logging.DEBUG)
_all_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── 异常日志 Handler ─────────────────────────────────────
_error_handler = RotatingFileHandler(
    ERROR_LOG_PATH,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=2,
    encoding="utf-8",
)
_error_handler.setLevel(logging.WARNING)  # WARNING + ERROR
_error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── 控制台 Handler（保留界面日志）─────────────────────────
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))


def get_logger(name: str) -> logging.Logger:
    """获取统一日志器。

    Args:
        name: 模块名（如 "site_manager", "group_crawler"）

    Returns:
        Logger 实例，已配置全量+异常+控制台三个 Handler
    """
    logger = logging.getLogger(name)

    # 防止重复添加 Handler（多次调用 get_logger 时）
    if not logger.handlers:
        logger.addHandler(_all_handler)
        logger.addHandler(_error_handler)
        logger.addHandler(_console_handler)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 不传给 root logger

    return logger


# ── 初始化日志 ─────────────────────────────────────────────
_init_log = get_logger("logger_init")
_init_log.info("日志系统初始化: all.log=%s, error.log=%s", ALL_LOG_PATH, ERROR_LOG_PATH)