"""Server酱 Turbo 推送：https://sct.ftqq.com

POST https://sctapi.ftqq.com/<SENDKEY>.send  form: title, desp(Markdown)
desp 上限约 32KB，足够容纳日报。
"""
from __future__ import annotations

import requests

from ..config import SERVERCHAN_SENDKEY

_MAX_DESP = 31000   # 留余量


def push(title: str, markdown: str) -> bool:
    if not SERVERCHAN_SENDKEY:
        print("[serverchan] 未配置 SERVERCHAN_SENDKEY，跳过")
        return False
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    desp = markdown[:_MAX_DESP]
    try:
        r = requests.post(url, data={"title": title[:100], "desp": desp}, timeout=20)
        r.raise_for_status()
        data = r.json()
        # Turbo 返回 code==0 为成功
        ok = data.get("code") == 0
        if not ok:
            print(f"[serverchan] 推送返回异常: {data}")
        else:
            print("[serverchan] 推送成功")
        return ok
    except Exception as exc:
        print(f"[serverchan] 推送失败: {exc}")
        return False
