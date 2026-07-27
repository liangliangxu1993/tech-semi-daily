"""股价与技术指标采集：yfinance 拉历史行情，自算 MA/RSI/涨跌幅。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import pandas as pd

from ..config import WATCHLIST, THRESHOLDS, Ticker
from ._yf import download_history


@dataclass
class PriceSnapshot:
    symbol: str
    name: str
    region: str
    price: float | None = None
    change_pct_1d: float | None = None     # 最近一个交易日涨跌幅(%)
    change_pct_5d: float | None = None      # 近 5 交易日涨跌幅(%)
    ma_short: float | None = None           # MA20
    ma_long: float | None = None            # MA50
    rsi: float | None = None
    above_ma_short: bool | None = None
    above_ma_long: bool | None = None
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _rsi(close: pd.Series, period: int) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _pct(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return round((a - b) / b * 100, 2)


def _snapshot_from(t: Ticker, hist: pd.DataFrame | None) -> PriceSnapshot:
    snap = PriceSnapshot(symbol=t.symbol, name=t.name, region=t.region)
    try:
        if hist is None or hist.empty or "Close" not in hist.columns:
            snap.error = "无行情数据"
            return snap
        close = hist["Close"].dropna()
        if close.empty:
            snap.error = "无行情数据"
            return snap

        snap.price = round(float(close.iloc[-1]), 2)
        if len(close) >= 2:
            snap.change_pct_1d = _pct(close.iloc[-1], close.iloc[-2])
        if len(close) >= 6:
            snap.change_pct_5d = _pct(close.iloc[-1], close.iloc[-6])

        if len(close) >= THRESHOLDS.ma_short:
            snap.ma_short = round(float(close.tail(THRESHOLDS.ma_short).mean()), 2)
            snap.above_ma_short = snap.price > snap.ma_short
        if len(close) >= THRESHOLDS.ma_long:
            snap.ma_long = round(float(close.tail(THRESHOLDS.ma_long).mean()), 2)
            snap.above_ma_long = snap.price > snap.ma_long

        snap.rsi = _rsi(close, THRESHOLDS.rsi_period)
    except Exception as exc:
        snap.error = str(exc)
    return snap


def collect_prices() -> list[PriceSnapshot]:
    # 一次性批量拉取全部标的，把请求数从 N 降到 1，显著降低被 Yahoo 限流概率
    symbols = [t.symbol for t in WATCHLIST]
    try:
        frames = download_history(symbols, period="3mo", interval="1d")
    except Exception as exc:
        print(f"[prices] 批量行情获取失败: {exc}")
        frames = {}
    return [_snapshot_from(t, frames.get(t.symbol)) for t in WATCHLIST]


if __name__ == "__main__":
    for s in collect_prices():
        print(s.to_dict())
