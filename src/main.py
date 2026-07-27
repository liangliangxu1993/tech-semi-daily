"""编排入口：采集 → 量化分析 → LLM 解读 → 渲染 → 推送。

用法：
    python -m src.main              # 完整运行并推送
    python -m src.main --dry-run    # 只生成报告打印到终端，不推送
    python -m src.main --save out.md  # 额外把报告写入文件
"""
from __future__ import annotations

import argparse
import sys

# 本地运行时加载 .env（GitHub Actions 用 env 注入，dotenv 缺失也不报错）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from . import config
from .collectors.news import collect_news
from .collectors.prices import collect_prices
from .collectors.earnings import collect_earnings
from .collectors.macro import collect_macro
from .analysis.rules import build_signals
from .analysis.llm import generate_analysis
from .render import render_report


def run(dry_run: bool = False, save_path: str | None = None) -> int:
    print("[main] 配置:", config.summary())

    print("[main] 采集新闻…")
    news = collect_news()
    print("[main] 采集行情…")
    prices = collect_prices()
    print("[main] 采集财报…")
    earnings = collect_earnings()
    print("[main] 采集宏观…")
    macro = collect_macro()

    print("[main] 生成量化信号…")
    signals = build_signals(prices, earnings, macro)
    print(f"[main] 触发信号 {len(signals)} 条")

    print("[main] LLM 解读…")
    llm_text = generate_analysis(news, signals, prices, macro)
    print("[main] LLM:", "已生成" if llm_text else "不可用/已降级")

    title, body = render_report(news, earnings, macro, prices, signals, llm_text)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{body}")
        print(f"[main] 报告已保存到 {save_path}")

    if dry_run:
        print("\n" + "=" * 60 + " DRY RUN 报告预览 " + "=" * 60 + "\n")
        print(body)
        return 0

    # 推送
    ok = _dispatch(title, body)
    return 0 if ok else 1


def _dispatch(title: str, body: str) -> bool:
    channel = config.PUSH_CHANNEL
    results: list[bool] = []

    if channel in ("serverchan", "both"):
        from .push.serverchan import push as sc_push
        results.append(sc_push(title, body))
    if channel in ("wecom", "both"):
        from .push.wecom import push as wc_push
        results.append(wc_push(title, body))

    if not results:
        print(f"[main] 未知或未启用推送渠道: {channel}")
        return False
    return any(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="科技半导体每日资讯推送")
    parser.add_argument("--dry-run", action="store_true", help="只生成报告不推送")
    parser.add_argument("--save", metavar="PATH", help="把报告额外保存到文件")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, save_path=args.save)


if __name__ == "__main__":
    sys.exit(main())
