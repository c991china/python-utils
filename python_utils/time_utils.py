"""时间相关小工具。"""

from __future__ import annotations

import time
from datetime import datetime, timezone


def now_iso() -> str:
    """返回当前 UTC 时间的 ISO8601 字符串。"""
    return datetime.now(timezone.utc).isoformat()


def humanize_duration(seconds: float) -> str:
    """把秒数转成人类可读的字符串，如 '1h 2m 3s'。"""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{sec}s")
    return " ".join(parts)


def parse_duration(text: str) -> float:
    """解析 '1h2m3s' / '90s' 这样的字符串为秒数。"""
    units = {"h": 3600, "m": 60, "s": 1}
    total = 0.0
    num = ""
    for ch in text.strip().lower():
        if ch.isdigit() or ch == ".":
            num += ch
        elif ch in units:
            if not num:
                raise ValueError(f"缺少数值: {text}")
            total += float(num) * units[ch]
            num = ""
        else:
            raise ValueError(f"非法字符: {ch}")
    if num:
        total += float(num)
    return total


if __name__ == "__main__":
    print(now_iso())
    print(humanize_duration(parse_duration("1h2m3s")))
