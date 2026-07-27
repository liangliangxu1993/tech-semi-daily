"""企业微信群机器人推送。

Webhook: 群设置 -> 添加机器人 -> 复制 Webhook。
markdown 消息单条上限 4096 字节，超出则按段分多条发送。
"""
from __future__ import annotations

import time

import requests

from ..config import WECOM_WEBHOOK

_MAX_BYTES = 4000   # 4096 上限留余量


def _chunk_by_bytes(text: str, limit: int = _MAX_BYTES) -> list[str]:
    """按行聚合，保证每块 UTF-8 字节数不超过 limit。"""
    chunks: list[str] = []
    cur = ""
    for line in text.split("\n"):
        candidate = (cur + "\n" + line) if cur else line
        if len(candidate.encode("utf-8")) > limit and cur:
            chunks.append(cur)
            cur = line
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return chunks


def push(title: str, markdown: str) -> bool:
    if not WECOM_WEBHOOK:
        print("[wecom] 未配置 WECOM_WEBHOOK，跳过")
        return False

    full = f"# {title}\n\n{markdown}" if not markdown.lstrip().startswith("#") else markdown
    chunks = _chunk_by_bytes(full)
    total = len(chunks)
    all_ok = True

    for idx, chunk in enumerate(chunks, 1):
        content = chunk if total == 1 else f"（{idx}/{total}）\n{chunk}"
        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        try:
            r = requests.post(WECOM_WEBHOOK, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            if data.get("errcode") != 0:
                print(f"[wecom] 第 {idx} 段返回异常: {data}")
                all_ok = False
            else:
                print(f"[wecom] 第 {idx}/{total} 段推送成功")
        except Exception as exc:
            print(f"[wecom] 第 {idx} 段推送失败: {exc}")
            all_ok = False
        if idx < total:
            time.sleep(1)   # 避免触发频率限制
    return all_ok
