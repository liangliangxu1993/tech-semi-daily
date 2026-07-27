"""量化规则：把采集到的价格/财报/宏观数据转成可解释的结构化信号。

信号既进报告"量化信号"栏，也作为 LLM 的输入依据。零 API 成本。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from ..config import THRESHOLDS
from ..collectors.prices import PriceSnapshot
from ..collectors.earnings import EarningsInfo
from ..collectors.macro import MacroSnapshot


# 信号级别：info(中性提示) / bullish(偏多) / bearish(偏空) / warning(风险)
@dataclass
class Signal:
    level: str
    category: str        # 财报 / 均线 / 动量 / 油价 / 美联储 / 板块
    subject: str         # 标的或对象
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _price_signals(prices: list[PriceSnapshot]) -> list[Signal]:
    out: list[Signal] = []
    for p in prices:
        if p.error or p.price is None:
            continue
        # 均线金叉/死叉（用价格相对 MA 的位置近似 + 短长均线关系）
        if p.ma_short is not None and p.ma_long is not None:
            if p.ma_short > p.ma_long and p.above_ma_short:
                out.append(Signal("bullish", "均线", p.name,
                                   f"价{p.price} 站上 MA{THRESHOLDS.ma_short}({p.ma_short})，"
                                   f"且短均线上穿长均线，多头排列"))
            elif p.ma_short < p.ma_long and not p.above_ma_short:
                out.append(Signal("bearish", "均线", p.name,
                                   f"价{p.price} 跌破 MA{THRESHOLDS.ma_short}({p.ma_short})，"
                                   f"且短均线在长均线下方，空头排列"))
        # RSI 超买超卖
        if p.rsi is not None:
            if p.rsi >= THRESHOLDS.rsi_overbought:
                out.append(Signal("warning", "动量", p.name,
                                   f"RSI={p.rsi} 超买，注意短期回调风险"))
            elif p.rsi <= THRESHOLDS.rsi_oversold:
                out.append(Signal("info", "动量", p.name,
                                   f"RSI={p.rsi} 超卖，可能出现技术反弹"))
        # 单日大幅波动
        if p.change_pct_1d is not None and abs(p.change_pct_1d) >= 5:
            lvl = "bullish" if p.change_pct_1d > 0 else "bearish"
            out.append(Signal(lvl, "动量", p.name,
                               f"最近交易日 {p.change_pct_1d:+.2f}%，异动明显"))
    return out


def _earnings_signals(earnings: list[EarningsInfo]) -> list[Signal]:
    out: list[Signal] = []
    for e in earnings:
        # 最近一期业绩超预期/不及预期
        if e.surprise_pct is not None and e.beat is not None:
            if e.beat:
                out.append(Signal("bullish", "财报", e.name,
                                   f"最近一期({e.last_date}) EPS 超预期 {e.surprise_pct:+.1f}%"
                                   f"（实际{e.eps_actual} vs 预期{e.eps_estimate}）"))
            else:
                out.append(Signal("bearish", "财报", e.name,
                                   f"最近一期({e.last_date}) EPS 不及预期 {e.surprise_pct:+.1f}%"
                                   f"（实际{e.eps_actual} vs 预期{e.eps_estimate}）"))
        # 即将披露财报
        if e.days_until is not None and 0 <= e.days_until <= 7:
            out.append(Signal("info", "财报", e.name,
                               f"{e.days_until} 天后（{e.next_date}）披露财报，关注预期差"))
    return out


def _macro_signals(macro: MacroSnapshot) -> list[Signal]:
    out: list[Signal] = []
    for p in macro.points:
        if p.error or p.value is None:
            continue
        if p.key in ("wti", "brent") and p.change_pct_1d is not None:
            if abs(p.change_pct_1d) >= THRESHOLDS.oil_move_pct:
                lvl = "warning"
                direction = "跳涨" if p.change_pct_1d > 0 else "跳水"
                out.append(Signal(lvl, "油价", p.name,
                                   f"{p.name} {direction} {p.change_pct_1d:+.2f}% 至 {p.value}，"
                                   f"或影响通胀与成本预期"))
        if p.key == "sox" and p.change_pct_1d is not None:
            lvl = "bullish" if p.change_pct_1d > 0 else "bearish"
            out.append(Signal(lvl, "板块", "费城半导体指数",
                               f"^SOX {p.change_pct_1d:+.2f}% 至 {p.value}，反映半导体板块整体情绪"))

    # 美联储议息临近
    if macro.days_to_fomc is not None and 0 <= macro.days_to_fomc <= THRESHOLDS.fomc_near_days:
        if macro.fed_funds_rate is not None:
            rate_txt = f"，当前利率约 {macro.fed_funds_rate}%（{macro.fed_rate_source}）"
        else:
            rate_txt = ""
        out.append(Signal("warning", "美联储", "FOMC",
                           f"{macro.days_to_fomc} 天后（{macro.next_fomc}）召开 FOMC 议息会议"
                           f"{rate_txt}，警惕政策扰动"))
    return out


def build_signals(prices, earnings, macro) -> list[Signal]:
    signals: list[Signal] = []
    signals += _earnings_signals(earnings)
    signals += _price_signals(prices)
    signals += _macro_signals(macro)
    # 排序：warning > bearish/bullish > info
    order = {"warning": 0, "bearish": 1, "bullish": 2, "info": 3}
    signals.sort(key=lambda s: order.get(s.level, 9))
    return signals


if __name__ == "__main__":  # 简单自测（无网络时用空数据）
    print(build_signals([], [], MacroSnapshot(points=[])))
