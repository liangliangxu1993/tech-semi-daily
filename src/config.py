"""全局配置：关注标的、新闻查询、量化阈值、运行参数。

大部分开关来自环境变量（配合 .env / GitHub Secrets），业务清单直接写在本文件，
需要调整关注股票或新闻关键词时改这里即可。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 环境变量开关
# ---------------------------------------------------------------------------
PUSH_CHANNEL = os.getenv("PUSH_CHANNEL", "serverchan").strip().lower()
SERVERCHAN_SENDKEY = os.getenv("SERVERCHAN_SENDKEY", "").strip()
WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK", "").strip()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5").strip()
ENABLE_LLM = os.getenv("ENABLE_LLM", "1").strip() not in ("0", "false", "False", "")

FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()

# 时区：报告标题日期按北京时间显示
TIMEZONE = "Asia/Shanghai"


# ---------------------------------------------------------------------------
# 关注标的（按区域）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Ticker:
    symbol: str          # yfinance 代码
    name: str            # 中文/展示名
    region: str          # US / KR / CN


WATCHLIST: list[Ticker] = [
    # 美国
    Ticker("NVDA", "英伟达", "US"),
    Ticker("AMD", "AMD", "US"),
    Ticker("AVGO", "博通", "US"),
    Ticker("INTC", "英特尔", "US"),
    Ticker("QCOM", "高通", "US"),
    Ticker("MU", "美光", "US"),
    Ticker("AMAT", "应用材料", "US"),
    Ticker("LRCX", "泛林", "US"),
    Ticker("TSM", "台积电(ADR)", "US"),
    Ticker("ASML", "阿斯麦(ADR)", "US"),
    # 韩国
    Ticker("005930.KS", "三星电子", "KR"),
    Ticker("000660.KS", "SK海力士", "KR"),
    # 中国
    Ticker("0981.HK", "中芯国际(港)", "CN"),
    Ticker("688981.SS", "中芯国际(A)", "CN"),
    Ticker("002371.SZ", "北方华创", "CN"),
    Ticker("688012.SS", "中微公司", "CN"),
]

# 宏观 / 大盘代码
MACRO_TICKERS = {
    "wti": "CL=F",       # WTI 原油期货
    "brent": "BZ=F",     # 布伦特原油期货
    "sox": "^SOX",       # 费城半导体指数
    "nasdaq": "^IXIC",   # 纳斯达克综合
    "us10y": "^TNX",     # 10 年美债收益率(值为收益率*10)
}


# ---------------------------------------------------------------------------
# 新闻抓取：Google News RSS 分区查询
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NewsSource:
    region: str          # 展示用区域标签
    query: str           # 搜索关键词
    hl: str              # 界面语言
    gl: str              # 地区
    ceid: str            # country:lang


NEWS_SOURCES: list[NewsSource] = [
    NewsSource("美国", "semiconductor OR chip OR AI chip earnings", "en-US", "US", "US:en"),
    NewsSource("韩国", "반도체 OR 삼성전자 OR SK하이닉스", "ko", "KR", "KR:ko"),
    NewsSource("中国", "半导体 OR 芯片 OR 集成电路", "zh-CN", "CN", "CN:zh-Hans"),
    NewsSource("全球局势/宏观", "Fed rate decision OR oil price OR chip export control", "en-US", "US", "US:en"),
]

# 每个来源最多取多少条
NEWS_PER_SOURCE = int(os.getenv("NEWS_PER_SOURCE", "8"))
# 只保留最近多少小时内的新闻
NEWS_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "36"))


# ---------------------------------------------------------------------------
# 量化阈值
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Thresholds:
    oil_move_pct: float = 3.0        # 油价单日涨跌幅提示阈值(%)
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    fomc_near_days: int = 7          # 距 FOMC 会议多少天内提示
    ma_short: int = 20
    ma_long: int = 50
    rsi_period: int = 14


THRESHOLDS = Thresholds()


# ---------------------------------------------------------------------------
# FOMC 会议日历（静态维护，用于"临近议息"提示；每年更新一次即可）
# 来源：美联储官网 https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
# ---------------------------------------------------------------------------
FOMC_MEETINGS_2026 = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]


def summary() -> dict:
    """返回当前有效配置的简报，便于启动时打印排查。"""
    return {
        "push_channel": PUSH_CHANNEL,
        "serverchan": bool(SERVERCHAN_SENDKEY),
        "wecom": bool(WECOM_WEBHOOK),
        "llm_enabled": ENABLE_LLM and bool(ANTHROPIC_API_KEY),
        "llm_model": LLM_MODEL,
        "fred": bool(FRED_API_KEY),
        "watchlist": len(WATCHLIST),
        "news_sources": len(NEWS_SOURCES),
    }
