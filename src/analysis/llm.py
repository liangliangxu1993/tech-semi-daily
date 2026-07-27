"""LLM 解读：把结构化数据（新闻+量化信号+价格+宏观）交给 Claude 生成中文综述与持股建议。

失败时返回 None，由上层降级为纯量化报告，绝不阻断推送。
"""
from __future__ import annotations

import json

from ..config import ANTHROPIC_API_KEY, LLM_MODEL, ENABLE_LLM

_DISCLAIMER = "以上内容由 AI 依据公开数据自动生成，仅供参考，不构成任何投资建议。市场有风险，决策需谨慎。"

_SYSTEM = """你是一名资深的科技与半导体产业分析师，服务于一位关注美/韩/中半导体产业的科技持股投资者。
你会收到当日结构化数据：分区新闻标题、量化信号、关注标的价格与技术面、宏观数据（美联储/油价/费半指数）。

请用【简体中文】输出一份精炼的每日简报，严格使用如下 Markdown 结构，不要寒暄：

## 📌 今日产业要点
（3-5 条 bullet，提炼当日最重要的产业动向，跨区域综合）

## 🌍 宏观影响
（结合美联储政策路径、油价、费半指数与全球局势，2-4 句解读对科技/半导体板块的影响）

## 💡 科技持股投资建议
（基于量化信号与新闻，给出分标的或分板块的倾向性观点，每条注明理由并引用具体信号/数据；
区分"关注/偏多""谨慎/偏空""观望"三类；务必客观、给出风险提示）

要求：
- 只依据提供的数据，不臆造数字或未提供的事实；数据缺失就说明"数据不足"。
- 语言专业、克制，避免绝对化措辞（如"必涨""稳赚"）。
- 总长度控制在 800 字以内。"""


def _build_payload(news, signals, prices, macro) -> dict:
    return {
        "news_by_region": {
            region: [{"title": it.title, "source": it.source} for it in items]
            for region, items in news.items()
        },
        "signals": [s.to_dict() for s in signals],
        "prices": [
            {
                "name": p.name, "region": p.region, "price": p.price,
                "chg_1d_%": p.change_pct_1d, "chg_5d_%": p.change_pct_5d,
                "rsi": p.rsi, "above_ma20": p.above_ma_short, "above_ma50": p.above_ma_long,
            }
            for p in prices if not p.error
        ],
        "macro": macro.to_dict(),
    }


def generate_analysis(news, signals, prices, macro) -> str | None:
    """成功返回 Markdown 文本（不含免责声明，由 render 统一附加）；不可用/失败返回 None。"""
    if not ENABLE_LLM or not ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic
    except ImportError:
        print("[llm] 未安装 anthropic SDK，跳过 LLM 分析")
        return None

    payload = _build_payload(news, signals, prices, macro)
    user_msg = (
        "以下是今日结构化数据（JSON）：\n\n```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n```\n\n请据此生成每日简报。"
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=LLM_MODEL,
            max_tokens=2000,
            temperature=0.3,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text").strip()
        return text or None
    except Exception as exc:
        print(f"[llm] 调用失败，降级为纯量化报告: {exc}")
        return None


def disclaimer() -> str:
    return _DISCLAIMER
