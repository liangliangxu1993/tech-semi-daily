"""新闻采集：通过 Google News RSS 按区域抓取半导体/科技资讯。

Google News RSS 免费、无需鉴权，且 GitHub Actions（Azure 美国节点）可直连。
用 hl/gl/ceid 切换语言区，用 q 传关键词。
"""
from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta

import feedparser
import requests

from ..config import NEWS_SOURCES, NEWS_PER_SOURCE, NEWS_MAX_AGE_HOURS, NewsSource

_RSS_BASE = "https://news.google.com/rss/search"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# 网络超时（秒）：feedparser.parse 自身不支持超时，故先用 requests 抓取
_HTTP_TIMEOUT = 15


@dataclass
class NewsItem:
    region: str
    title: str
    source: str
    link: str
    published: str        # ISO 字符串，无法解析时为空

    def to_dict(self) -> dict:
        return asdict(self)


def _build_url(src: NewsSource) -> str:
    params = {
        "q": src.query,
        "hl": src.hl,
        "gl": src.gl,
        "ceid": src.ceid,
    }
    return f"{_RSS_BASE}?{urllib.parse.urlencode(params)}"


def _parse_published(entry) -> tuple[str, datetime | None]:
    """返回 (ISO字符串, aware datetime)。解析失败返回 ('', None)。"""
    tstruct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not tstruct:
        return "", None
    dt = datetime.fromtimestamp(time.mktime(tstruct), tz=timezone.utc)
    return dt.isoformat(), dt


def fetch_region(src: NewsSource) -> list[NewsItem]:
    url = _build_url(src)
    # 关键：用 requests 带超时抓取，再交给 feedparser 解析字节，
    # 避免 feedparser.parse(url) 在目标不可达时无限挂起。
    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_MAX_AGE_HOURS)

    items: list[NewsItem] = []
    for entry in feed.entries:
        iso, dt = _parse_published(entry)
        if dt is not None and dt < cutoff:
            continue
        # Google News 标题形如 "标题 - 媒体名"，尽量拆出媒体名
        raw_title = getattr(entry, "title", "").strip()
        source_name = ""
        src_obj = getattr(entry, "source", None)
        if src_obj is not None:
            source_name = getattr(src_obj, "title", "") or ""
        if not source_name and " - " in raw_title:
            raw_title, source_name = raw_title.rsplit(" - ", 1)

        items.append(
            NewsItem(
                region=src.region,
                title=raw_title.strip(),
                source=source_name.strip(),
                link=getattr(entry, "link", ""),
                published=iso,
            )
        )
        if len(items) >= NEWS_PER_SOURCE:
            break
    return items


def collect_news() -> dict[str, list[NewsItem]]:
    """按区域返回新闻。键为 region 展示名。"""
    result: dict[str, list[NewsItem]] = {}
    for src in NEWS_SOURCES:
        try:
            result[src.region] = fetch_region(src)
        except Exception as exc:  # 单个源失败不影响整体
            print(f"[news] 抓取失败 region={src.region}: {exc}")
            result[src.region] = []
    return result


if __name__ == "__main__":
    data = collect_news()
    for region, items in data.items():
        print(f"\n=== {region} ({len(items)}) ===")
        for it in items:
            print(f"- [{it.source}] {it.title}")
