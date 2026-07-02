# -*- coding: utf-8 -*-
"""
同花顺量化信号推送系统
Python 策略 → 生成信号 → 推送含深度链接的消息到手机
→ 点击链接直接跳转到同花顺个股页面
"""

from __future__ import annotations
import time
import threading
import logging
from datetime import datetime, time as dtime
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import re

# ─────────────────────────────────────────────
#  Part 1: 同花顺深度跳转链接构造
# ─────────────────────────────────────────────

class Market(Enum):
    """股票市场枚举"""
    Shanghai = "sh"   # 上交所 .SH
    Shenzhen = "sz"   # 深交所 .SZ
    GEM = "sz"        # 创业板 .SZ
    STAR = "sh"       # 科创板 .SH

@dataclass
class StockCode:
    """股票代码封装，自动识别市场"""
    code: str

    def __post_init__(self):
        # 去掉后缀
        self.code = re.sub(r'\.(SH|SZ|sh|sz)$', '', self.code).strip()

    @property
    def ths_code(self) -> str:
        """返回同花顺格式代码（6位数字）"""
        return self.code.zfill(6)

    @property
    def ths_url(self) -> str:
        """同花顺网页个股页 URL"""
        return f"http://stockpage.10jqka.com.cn/{self.ths_code}/"

    @property
    def ths_m_url(self) -> str:
        """同花顺移动端（手机浏览器）个股页 URL"""
        return f"http://m.10jqka.com.cn/{self.ths_code}/"

    def android_deep_link(self) -> str:
        """
        Android 深度跳转链接
        优先打开同花顺 App，未安装则跳转网页
        """
        # 标准 intent 格式
        intent = (
            f"intent://stockpage.10jqka.com.cn/{self.ths_code}/"
            f"#Intent;"
            f"scheme=http;"
            f"package=com.hexin.plat.android;"
            f"action=android.intent.action.VIEW;"
            f"end"
        )
        return intent

    def ios_deep_link(self) -> str:
        """
        iOS 深度跳转链接（同花顺 App URL Scheme）
        注：iOS 9+ 使用 Universal Link，ths:// 为推测格式
        """
        return f"ths://stockpage/{self.ths_code}"

    def fallback_url(self) -> str:
        """兜底网页链接（所有平台均可用）"""
        return self.ths_url


def make_clickable_link(stock_code: str, label: Optional[str] = None) -> str:
    """
    生成带超链接的 HTML，兼容 QQ/微信/飞书/短信展示

    Args:
        stock_code: 股票代码，如 "600519" 或 "600519.SH"
        label: 链接显示文字，默认 "查看 [股票名称/代码]"
    """
    code = StockCode(stock_code)
    url = code.android_deep_link()
    display = label or f"{code.ths_code}"

    # HTML <a> 标签，QQ/微信识别可点击
    return f'<a href="{url}">{display}</a>'


def make_qq_message(stock_code: str, stock_name: str, signal: str,
                     price: float, change_pct: float) -> str:
    """
    生成 QQ 推送消息内容（支持卡片格式）
    """
    emoji = "📈" if change_pct > 0 else "📉"
    signal_emoji = "🟢买入" if "买" in signal else ("🔴卖出" if "卖" in signal else "🟡信号")

    # 链接文本（QQ消息中点击会打开浏览器/App）
    link_text = f"👉 {stock_name}({stock_code})"

    msg = (
        f"{emoji} 【量化信号】{signal_emoji}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"股票：{link_text}\n"
        f"价格：{price:.2f} 元\n"
        f"涨跌：{'+' if change_pct > 0 else ''}{change_pct:.2f}%\n"
        f"信号：{signal}\n"
        f"时间：{datetime.now().strftime('%H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💡 点击链接直达同花顺个股页面"
    )
    return msg


# ─────────────────────────────────────────────
#  Part 2: 消息推送后端（Flask API）
# ─────────────────────────────────────────────

from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route("/api/push_signal", methods=["POST"])
def push_signal():
    """
    接收策略信号，推送给手机
    POST body (JSON):
    {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "signal": "MA金叉买入",
        "price": 1688.0,
        "change_pct": 2.35,
        "channel": "qq"   # or "wechat", "feishu", "sms"
    }
    """
    data = request.get_json()
    stock_code = data.get("stock_code", "")
    stock_name = data.get("stock_name", stock_code)
    signal = data.get("signal", "")
    price = data.get("price", 0.0)
    change_pct = data.get("change_pct", 0.0)
    channel = data.get("channel", "qq")

    code = StockCode(stock_code)
    msg = make_qq_message(stock_code, stock_name, signal, price, change_pct)

    # 根据渠道推送
    if channel == "qq":
        _send_to_qq(code.android_deep_link(), msg, stock_name)
    elif channel == "feishu":
        _send_to_feishu(code.android_deep_link(), msg)
    elif channel == "sms":
        _send_sms(code.fallback_url(), msg)
    else:
        _send_to_qq(code.android_deep_link(), msg, stock_name)

    logger.info(f"信号已推送: {stock_name}({stock_code}) via {channel}")
    return jsonify({"status": "ok", "code": stock_code, "channel": channel})


def _send_to_qq(deep_link: str, msg: str, stock_name: str):
    """
    通过 QQ 机器人推送消息
    需要配置 QQ_BOT_TOKEN 环境变量
    """
    try:
        import os
        token = os.environ.get("QQ_BOT_TOKEN", "")
        if not token:
            logger.warning("QQ_BOT_TOKEN 未设置，跳过 QQ 推送")
            return

        import requests
        payload = {
            "group_id": os.environ.get("QQ_GROUP_ID", ""),
            "message": msg,
            "auto_escape": False
        }
        # 消息中嵌入可点击链接
        link_msg = f"{msg}\n\n🔗 点击查看：[同花顺 {stock_name}]({deep_link})"
        payload["message"] = link_msg

        resp = requests.post(
            f"https://api.sgroup.qq.com/gateway/chat",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10
        )
        logger.info(f"QQ 推送响应: {resp.status_code}")
    except Exception as e:
        logger.error(f"QQ 推送失败: {e}")


def _send_to_feishu(deep_link: str, msg: str):
    """通过飞书机器人推送"""
    try:
        import os, requests
        webhook = os.environ.get("FEISHU_WEBHOOK", "")
        if not webhook:
            logger.warning("FEISHU_WEBHOOK 未设置")
            return

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {"tag": "div", "text": {"content": msg, "tag": "lark_md"}},
                    {"tag": "hr"},
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"content": "📊 打开同花顺", "tag": "lark_md"},
                                "type": "primary",
                                "value": {"url": deep_link}
                            }
                        ]
                    }
                ]
            }
        }
        requests.post(webhook, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"飞书推送失败: {e}")


def _send_sms(deep_link: str, msg: str):
    """短信推送（URL 作为短信链接）"""
    logger.info(f"短信内容: {msg[:50]}... URL: {deep_link}")
    # TODO: 接入阿里云/腾讯云短信 API


# ─────────────────────────────────────────────
#  Part 3: 策略引擎（示例：均线金叉策略）
# ─────────────────────────────────────────────

@dataclass
class TradingSignal:
    """交易信号"""
    stock_code: str
    stock_name: str
    signal_type: str          # "BUY" / "SELL" / "WATCH"
    signal_desc: str           # 如 "MA5 上穿 MA20 金叉"
    price: float
    change_pct: float
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_message(self) -> str:
        return make_qq_message(
            self.stock_code, self.stock_name,
            self.signal_desc, self.price, self.change_pct
        )


class StrategyEngine:
    """
    策略引擎基类
    子类实现 check() 方法即可自定义策略
    """

    def __init__(self, stock_list: list[tuple[str, str]]):
        """
        Args:
            stock_list: [(代码, 名称), ...]
        """
        self.stock_list = stock_list
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def check(self, stock_code: str, stock_name: str) -> Optional[TradingSignal]:
        """
        检查股票是否触发信号（子类重写）
        返回 TradingSignal 或 None
        """
        raise NotImplementedError

    def run(self, interval_seconds: int = 60):
        """后台定时运行策略检查"""
        self.running = True
        import akshare  # pip install akshare

        while self.running:
            try:
                for code, name in self.stock_list:
                    signal = self.check(code, name)
                    if signal:
                        # 推送信号到手机
                        self._push_signal(signal)
            except Exception as e:
                logger.error(f"策略检查异常: {e}")
            time.sleep(interval_seconds)

    def _push_signal(self, signal: TradingSignal):
        """将信号推送至后端"""
        try:
            import requests, os
            api_url = os.environ.get("PUSH_API_URL", "http://localhost:5000/api/push_signal")
            resp = requests.post(api_url, json={
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "signal": signal.signal_desc,
                "price": signal.price,
                "change_pct": signal.change_pct,
                "channel": os.environ.get("PUSH_CHANNEL", "qq")
            }, timeout=10)
            logger.info(f"信号推送结果: {resp.json()}")
        except Exception as e:
            logger.error(f"信号推送失败: {e}")

    def start_async(self, interval_seconds: int = 60):
        """异步启动策略（后台线程）"""
        self._thread = threading.Thread(
            target=self.run, args=(interval_seconds,), daemon=True
        )
        self._thread.start()
        logger.info("策略引擎已后台启动")

    def stop(self):
        self.running = False


# ─────────────────────────────────────────────
#  Part 4: 示例策略 - 均线金叉策略
# ─────────────────────────────────────────────

class MAMomentumStrategy(StrategyEngine):
    """
    均线金叉动量策略
    买入信号：MA5 上穿 MA20（金叉）
    卖出信号：MA5 下穿 MA20（死叉）
    """

    def check(self, stock_code: str, stock_name: str) -> Optional[TradingSignal]:
        try:
            import akshare as ak
            import pandas as pd

            # 获取日线数据（最近60天）
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
            df = df.tail(60).copy()
            df = df.sort_values("日期")

            close = df["收盘"].values
            ma5 = pd.Series(close).rolling(5).mean().values
            ma20 = pd.Series(close).rolling(20).mean().values

            if len(ma5) < 21:
                return None

            # 金叉：MA5 从下方穿越 MA20
            if ma5[-2] < ma20[-2] and ma5[-1] > ma20[-1]:
                today_close = close[-1]
                yesterday_close = close[-2]
                change_pct = (today_close - yesterday_close) / yesterday_close * 100
                return TradingSignal(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    signal_type="BUY",
                    signal_desc=f"MA5 上穿 MA20 金叉买入",
                    price=float(today_close),
                    change_pct=float(change_pct)
                )

            # 死叉：MA5 从上方穿越 MA20
            if ma5[-2] > ma20[-2] and ma5[-1] < ma20[-1]:
                today_close = close[-1]
                yesterday_close = close[-2]
                change_pct = (today_close - yesterday_close) / yesterday_close * 100
                return TradingSignal(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    signal_type="SELL",
                    signal_desc=f"MA5 下穿 MA20 死叉卖出",
                    price=float(today_close),
                    change_pct=float(change_pct)
                )

        except Exception as e:
            logger.error(f"检查 {stock_code} 失败: {e}")
        return None


# ─────────────────────────────────────────────
#  Part 5: 启动入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import os
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # 示例自选股池
    WATCH_LIST = [
        ("600519", "贵州茅台"),
        ("000001", "平安银行"),
        ("300750", "宁德时代"),
        ("601318", "中国平安"),
    ]

    # 启动推送 API 服务（可选，也可以直接调用 _push_signal）
    api_port = int(os.environ.get("PUSH_PORT", "5000"))

    # 启动策略引擎（后台每 5 分钟检查一次）
    strategy = MAMomentumStrategy(WATCH_LIST)
    strategy.start_async(interval_seconds=300)

    # 启动 Flask API（供外部调用）
    print(f"\n🚀 同花顺量化信号推送服务已启动")
    print(f"   策略检查间隔: 5分钟")
    print(f"   API 端口: {api_port}")
    print(f"   推送渠道: {os.environ.get('PUSH_CHANNEL', 'qq')}")
    print(f"\n📋 深度跳转链接示例：")
    demo = StockCode("600519")
    print(f"   安卓: {demo.android_deep_link()}")
    print(f"   网页: {demo.fallback_url()}")
    print()

    app.run(host="0.0.0.0", port=api_port, debug=False, threaded=True)
