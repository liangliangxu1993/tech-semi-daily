"""宏观数据采集：原油、费半指数、纳指、美债收益率，以及美联储利率与议息日程。"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime

import pandas as pd
import requests

from ..config import MACRO_TICKERS, FRED_API_KEY, FOMC_MEETINGS_2026, THRESHOLDS
from ._yf import download_history


@dataclass
class MacroPoint:
    key: str
    name: str
    value: float | None = None
    change_pct_1d: float | None = None
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MacroSnapshot:
    points: list[MacroPoint]
    fed_funds_rate: float | None = None
    fed_rate_source: str = ""            # "FRED" 或 "^TNX代理"
    next_fomc: str = ""
    days_to_fomc: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["points"] = [p.to_dict() for p in self.points]
        return d


_NAMES = {
    "wti": "WTI原油",
    "brent": "布伦特原油",
    "sox": "费城半导体指数",
    "nasdaq": "纳斯达克综合",
    "us10y": "美债10年收益率",
}


def _point_from(key: str, hist: pd.DataFrame | None) -> MacroPoint:
    p = MacroPoint(key=key, name=_NAMES.get(key, key))
    try:
        if hist is None or hist.empty or "Close" not in hist.columns:
            p.error = "无数据"
            return p
        close = hist["Close"].dropna()
        if close.empty:
            p.error = "无数据"
            return p
        p.value = round(float(close.iloc[-1]), 2)
        if len(close) >= 2 and close.iloc[-2] != 0:
            p.change_pct_1d = round((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100, 2)
        # ^TNX 报的是收益率×10，还原成百分比
        if key == "us10y" and p.value is not None:
            p.value = round(p.value, 2)
    except Exception as exc:
        p.error = str(exc)
    return p


def _fetch_fed_funds_rate() -> tuple[float | None, str]:
    """优先用 FRED 取有效联邦基金利率(FEDFUNDS)；无 key 则返回 (None, '')。"""
    if not FRED_API_KEY:
        return None, ""
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "FEDFUNDS",
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if obs and obs[0].get("value") not in (".", None, ""):
            return round(float(obs[0]["value"]), 2), "FRED"
    except Exception as exc:
        print(f"[macro] FRED 获取失败: {exc}")
    return None, ""


def _next_fomc() -> tuple[str, int | None]:
    today = date.today()
    for d in FOMC_MEETINGS_2026:
        md = date.fromisoformat(d)
        if md >= today:
            return d, (md - today).days
    return "", None


def collect_macro() -> MacroSnapshot:
    # 批量拉取全部宏观标的，单请求降低限流概率
    try:
        frames = download_history(list(MACRO_TICKERS.values()), period="1mo", interval="1d")
    except Exception as exc:
        print(f"[macro] 批量宏观行情获取失败: {exc}")
        frames = {}
    points = [_point_from(k, frames.get(sym)) for k, sym in MACRO_TICKERS.items()]

    rate, source = _fetch_fed_funds_rate()
    if rate is None:
        # 退化：用 10 年美债收益率作为利率走势代理
        us10y = next((p for p in points if p.key == "us10y"), None)
        if us10y and us10y.value is not None:
            rate = us10y.value
            source = "^TNX代理(10Y美债)"

    next_fomc, days = _next_fomc()
    return MacroSnapshot(
        points=points,
        fed_funds_rate=rate,
        fed_rate_source=source,
        next_fomc=next_fomc,
        days_to_fomc=days,
    )


if __name__ == "__main__":
    snap = collect_macro()
    print(snap.to_dict())
