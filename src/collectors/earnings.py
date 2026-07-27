"""财报采集：yfinance 取即将披露的财报日期，以及最近一期业绩的超预期/不及预期。"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta

import pandas as pd
import yfinance as yf

from ..config import WATCHLIST, Ticker
from ._yf import call_with_retry, pause


@dataclass
class EarningsInfo:
    symbol: str
    name: str
    region: str
    next_date: str = ""          # 下次财报日期 ISO(若已知)
    days_until: int | None = None
    last_date: str = ""          # 最近一期财报日期
    eps_actual: float | None = None
    eps_estimate: float | None = None
    surprise_pct: float | None = None    # (实际-预期)/|预期| * 100
    beat: bool | None = None
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_next_date(tk: yf.Ticker) -> tuple[str, int | None]:
    """从 calendar 里取下一次财报日期。yfinance 版本差异做兼容。"""
    try:
        cal = call_with_retry(lambda: tk.calendar)
    except Exception:
        return "", None
    ed = None
    if isinstance(cal, dict):
        ed = cal.get("Earnings Date")
        if isinstance(ed, (list, tuple)) and ed:
            ed = ed[0]
    elif isinstance(cal, pd.DataFrame) and "Earnings Date" in cal.index:
        try:
            ed = cal.loc["Earnings Date"].iloc[0]
        except Exception:
            ed = None
    if ed is None:
        return "", None
    try:
        d = pd.Timestamp(ed).date()
    except Exception:
        return "", None
    return d.isoformat(), (d - date.today()).days


def _extract_last_earnings(tk: yf.Ticker) -> dict:
    """取最近一期已公布的 EPS 实际 vs 预期。"""
    out: dict = {}
    try:
        df = call_with_retry(lambda: tk.earnings_dates)  # index=日期, 含 'EPS Estimate' / 'Reported EPS'
    except Exception:
        return out
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return out

    now = pd.Timestamp.now(tz=df.index.tz) if df.index.tz else pd.Timestamp.now()
    past = df[df.index <= now].sort_index(ascending=False)
    if past.empty:
        return out

    row = past.iloc[0]
    out["last_date"] = past.index[0].date().isoformat()
    est = row.get("EPS Estimate")
    act = row.get("Reported EPS")
    if pd.notna(est):
        out["eps_estimate"] = round(float(est), 4)
    if pd.notna(act):
        out["eps_actual"] = round(float(act), 4)
    if pd.notna(est) and pd.notna(act) and float(est) != 0:
        surprise = (float(act) - float(est)) / abs(float(est)) * 100
        out["surprise_pct"] = round(surprise, 2)
        out["beat"] = float(act) >= float(est)
    return out


def fetch_earnings(t: Ticker) -> EarningsInfo:
    info = EarningsInfo(symbol=t.symbol, name=t.name, region=t.region)
    try:
        tk = yf.Ticker(t.symbol)
        info.next_date, info.days_until = _extract_next_date(tk)
        last = _extract_last_earnings(tk)
        info.last_date = last.get("last_date", "")
        info.eps_actual = last.get("eps_actual")
        info.eps_estimate = last.get("eps_estimate")
        info.surprise_pct = last.get("surprise_pct")
        info.beat = last.get("beat")
    except Exception as exc:
        info.error = str(exc)
    return info


def collect_earnings() -> list[EarningsInfo]:
    # 财报日历/历史无法批量，逐标的拉取并在调用间小憩，摊薄请求速率避免限流
    out: list[EarningsInfo] = []
    for i, t in enumerate(WATCHLIST):
        if i:
            pause()
        out.append(fetch_earnings(t))
    return out


def upcoming_earnings(infos: list[EarningsInfo], within_days: int = 14) -> list[EarningsInfo]:
    return [
        e for e in infos
        if e.days_until is not None and 0 <= e.days_until <= within_days
    ]


if __name__ == "__main__":
    for e in collect_earnings():
        print(e.to_dict())
