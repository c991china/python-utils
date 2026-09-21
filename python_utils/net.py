"""HTTP 网络助手：简单的 GET / JSON 请求。"""
from __future__ import annotations

import json
import urllib.request


def http_get(url: str, timeout: int = 10, headers: dict | None = None) -> str:
    """发送 GET 请求，返回响应文本。"""
    req = urllib.request.Request(
        url, headers=headers or {"User-Agent": "python-utils/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def http_get_json(url: str, timeout: int = 10) -> dict:
    """发送 GET 请求并解析为 JSON。"""
    return json.loads(http_get(url, timeout))
