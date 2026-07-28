"""Server酱 Turbo 推送：https://sct.ftqq.com

POST https://sctapi.ftqq.com/<SENDKEY>.send  form: text(标题), desp(Markdown 内容)
- text（标题）为必填，上限 32 字；参数名是 text 而非 title。
- desp（内容）上限约 32KB，足够容纳日报。
"""
from __future__ import annotations

import requests

from ..config import SERVERCHAN_SENDKEY

_MAX_TITLE = 32     # Server酱 标题上限
_MAX_DESP = 31000   # 留余量


def push(title: str, markdown: str) -> bool:
    if not SERVERCHAN_SENDKEY:
        print("[serverchan] 未配置 SERVERCHAN_SENDKEY，跳过")
        return False
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    text = (title or "科技半导体日报").strip()[:_MAX_TITLE]
    desp = markdown[:_MAX_DESP]
    try:
        r = requests.post(url, data={"text": text, "desp": desp}, timeout=20)
        # 不直接 raise：失败时优先读服务端返回体，里面有可诊断的错误信息
        try:
            data = r.json()
        except Exception:
            data = None
        if data is None:
            print(f"[serverchan] 推送失败: HTTP {r.status_code} {r.text[:300]}")
            return False
        # Turbo 返回 code==0 为成功
        ok = data.get("code") == 0
        if not ok:
            print(f"[serverchan] 推送返回异常: HTTP {r.status_code} {data}")
        else:
            print("[serverchan] 推送成功")
        return ok
    except Exception as exc:
        print(f"[serverchan] 推送失败: {exc}")
        return False
