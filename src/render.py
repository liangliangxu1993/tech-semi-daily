"""报告渲染：把采集数据 + 量化信号 + LLM 解读组装成 Markdown。"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .config import TIMEZONE
from .analysis.llm import disclaimer

_LEVEL_EMOJI = {
    "bullish": "🟢",
    "bearish": "🔴",
    "warning": "🟠",
    "info": "🔵",
}
_REGION_EMOJI = {"美国": "🇺🇸", "韩国": "🇰🇷", "中国": "🇨🇳", "全球局势/宏观": "🌍"}


def _today_str() -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
    week = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    return now.strftime(f"%Y-%m-%d 周{week} %H:%M")


def _news_section(news) -> str:
    lines = ["## 📰 分区资讯"]
    for region, items in news.items():
        emoji = _REGION_EMOJI.get(region, "•")
        lines.append(f"\n### {emoji} {region}")
        if not items:
            lines.append("- （暂无最新条目）")
            continue
        for it in items:
            src = f"（{it.source}）" if it.source else ""
            lines.append(f"- [{it.title}]({it.link}){src}")
    return "\n".join(lines)


def _earnings_section(earnings) -> str:
    upcoming = [e for e in earnings if e.days_until is not None and 0 <= e.days_until <= 14]
    recent = [e for e in earnings if e.surprise_pct is not None]
    lines = ["## 📊 财报追踪"]
    if upcoming:
        lines.append("\n**即将披露（14 日内）：**")
        for e in sorted(upcoming, key=lambda x: x.days_until):
            lines.append(f"- {e.name}（{e.symbol}）：{e.next_date}，还有 {e.days_until} 天")
    if recent:
        lines.append("\n**最近业绩表现：**")
        for e in recent:
            flag = "✅超预期" if e.beat else "⚠️不及预期"
            lines.append(
                f"- {e.name}：{flag} {e.surprise_pct:+.1f}%"
                f"（实际 {e.eps_actual} / 预期 {e.eps_estimate}，{e.last_date}）"
            )
    if not upcoming and not recent:
        lines.append("- （近期无可用财报数据）")
    return "\n".join(lines)


def _macro_section(macro) -> str:
    lines = ["## 🌍 宏观 · 美联储 · 油价 · 费半"]
    for p in macro.points:
        if p.error or p.value is None:
            continue
        chg = f"（{p.change_pct_1d:+.2f}%）" if p.change_pct_1d is not None else ""
        lines.append(f"- {p.name}：{p.value}{chg}")
    if macro.fed_funds_rate is not None:
        lines.append(f"- 联邦基金利率：约 {macro.fed_funds_rate}%（{macro.fed_rate_source}）")
    if macro.next_fomc:
        lines.append(f"- 下次 FOMC 议息：{macro.next_fomc}（还有 {macro.days_to_fomc} 天）")
    return "\n".join(lines)


def _prices_section(prices) -> str:
    lines = ["## 📈 关注标的行情"]
    by_region: dict[str, list] = {}
    for p in prices:
        by_region.setdefault(p.region, []).append(p)
    region_names = {"US": "🇺🇸 美国", "KR": "🇰🇷 韩国", "CN": "🇨🇳 中国"}
    for region, group in by_region.items():
        lines.append(f"\n### {region_names.get(region, region)}")
        for p in group:
            if p.error or p.price is None:
                lines.append(f"- {p.name}：数据获取失败")
                continue
            chg = f"{p.change_pct_1d:+.2f}%" if p.change_pct_1d is not None else "—"
            rsi = f"RSI {p.rsi}" if p.rsi is not None else ""
            lines.append(f"- {p.name}：{p.price}（{chg}）{('· ' + rsi) if rsi else ''}")
    return "\n".join(lines)


def _signals_section(signals) -> str:
    lines = ["## 🎯 量化信号"]
    if not signals:
        lines.append("- （今日无触发的量化信号）")
        return "\n".join(lines)
    for s in signals:
        emoji = _LEVEL_EMOJI.get(s.level, "•")
        lines.append(f"- {emoji} [{s.category}] {s.subject}：{s.message}")
    return "\n".join(lines)


def render_report(news, earnings, macro, prices, signals, llm_text: str | None) -> tuple[str, str]:
    """返回 (title, markdown_body)。"""
    title = f"科技半导体日报 · {_today_str()}"

    parts = [f"# {title}\n"]

    if llm_text:
        parts.append(llm_text.strip())
    else:
        parts.append("> ⚠️ 本期 LLM 解读不可用，以下为纯量化 + 资讯汇总。")

    parts.append(_signals_section(signals))
    parts.append(_news_section(news))
    parts.append(_earnings_section(earnings))
    parts.append(_macro_section(macro))
    parts.append(_prices_section(prices))

    parts.append(f"\n---\n\n> {disclaimer()}")

    body = "\n\n".join(parts)
    return title, body
