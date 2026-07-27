"""yfinance 访问封装：批量拉取 + 限流重试，缓解 Yahoo Finance 429（Too Many Requests）。

要点：
- Yahoo 会按「请求次数」限流。逐标的调用 16+ 次极易触发 429，
  故行情/宏观统一用 yf.download 一次性批量拉取，把请求数从 N 降到 1。
- 对仍可能出现的 429/网络抖动做指数退避重试。
- 无法批量的接口（如财报日历）用 history_with_retry 单点重试。
"""
from __future__ import annotations

import time

import pandas as pd
import yfinance as yf

_MAX_RETRIES = 4
_BASE_DELAY = 2.0          # 指数退避基数（秒）：2,4,8...
_PER_CALL_PAUSE = 0.6      # 单点循环间的固定间隔，进一步降低限流概率


def _is_rate_limit(exc: Exception) -> bool:
    txt = str(exc).lower()
    return (
        exc.__class__.__name__ == "YFRateLimitError"
        or "429" in txt
        or "too many requests" in txt
        or "rate limit" in txt
    )


def _split(df: pd.DataFrame | None, symbols: list[str]) -> dict[str, pd.DataFrame]:
    """把 yf.download 的结果拆成 {symbol: DataFrame}。兼容单/多标的两种列结构。"""
    out: dict[str, pd.DataFrame] = {}
    if df is None or df.empty:
        return {s: pd.DataFrame() for s in symbols}
    if len(symbols) == 1:
        out[symbols[0]] = df
        return out
    for s in symbols:
        try:
            sub = df[s].dropna(how="all")
        except Exception:
            sub = pd.DataFrame()
        out[s] = sub
    return out


def download_history(
    symbols,
    period: str = "3mo",
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """批量拉取多标的历史行情，带限流重试。返回 {symbol: DataFrame}。

    单次请求覆盖全部标的，是缓解 429 的关键。个别标的无数据时其 DataFrame 为空，
    不影响其它标的。整体被限流时按指数退避重试。
    """
    if isinstance(symbols, str):
        symbols = [symbols]
    symbols = list(symbols)
    if not symbols:
        return {}

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            df = yf.download(
                tickers=symbols,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            result = _split(df, symbols)
            # 全空且非最后一次尝试：可能被静默限流，退避后重试
            if all(v.empty for v in result.values()) and attempt < _MAX_RETRIES - 1:
                time.sleep(_BASE_DELAY * (2 ** attempt))
                continue
            return result
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc) and attempt < _MAX_RETRIES - 1:
                time.sleep(_BASE_DELAY * (2 ** attempt))
                continue
            raise
    if last_exc:
        raise last_exc
    return {s: pd.DataFrame() for s in symbols}


def history_with_retry(symbol: str, period: str, interval: str = "1d") -> pd.DataFrame:
    """单标的历史行情，带限流重试。用于无法批量的场景。"""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return yf.Ticker(symbol).history(
                period=period, interval=interval, auto_adjust=False
            )
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc) and attempt < _MAX_RETRIES - 1:
                time.sleep(_BASE_DELAY * (2 ** attempt))
                continue
            raise
    if last_exc:
        raise last_exc
    return pd.DataFrame()


def call_with_retry(fn, *args, **kwargs):
    """对任意 yfinance 调用（如取 calendar/earnings_dates）做限流重试。"""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc) and attempt < _MAX_RETRIES - 1:
                time.sleep(_BASE_DELAY * (2 ** attempt))
                continue
            raise
    if last_exc:
        raise last_exc
    return None


def pause() -> None:
    """单点循环之间的固定小憩，摊薄请求速率。"""
    time.sleep(_PER_CALL_PAUSE)
