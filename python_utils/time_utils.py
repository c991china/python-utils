"""Duration parsing, humanizing, and a retry decorator.

parse_duration exists because I got tired of writing `int(os.environ["TIMEOUT"])`
and then explaining to people that 30 is seconds, not milliseconds. Config
strings like "2h30m" are unambiguous to a human and cheap to parse.
"""

from __future__ import annotations

import functools
import re
import time
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["parse_duration", "humanize_delta", "retry"]

F = TypeVar("F", bound=Callable[..., Any])

_UNIT_SECONDS = {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0}
_TOKEN = re.compile(r"\s*(\d+(?:\.\d+)?)\s*([dhms])", re.IGNORECASE)


def parse_duration(value: str | int | float) -> float:
    """Parse a duration into seconds.

    Accepts a bare number (already in seconds) or a compound string using d/h/m/s:

        parse_duration("90")      -> 90.0
        parse_duration("2h30m")   -> 9000.0
        parse_duration("1.5h")    -> 5400.0
        parse_duration("1d2h3m4s")-> 93784.0

    Units must be in descending order? No, I don't enforce that. "30m2h" gives
    7800 seconds and I decided that's fine. Duplicated units also sum, so
    "1h1h" is 7200. Weird input, predictable output.

    Raises ValueError on anything unparseable, including an empty string.
    Raises TypeError for non-string, non-numeric input.
    """
    if isinstance(value, bool):
        # bool is an int subclass and True == 1 is almost never what was meant.
        raise TypeError("expected a duration string or number, got bool")

    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError(f"duration must be >= 0, got {value!r}")
        return float(value)

    if not isinstance(value, str):
        raise TypeError(f"expected str, int or float, got {type(value).__name__}")

    text = value.strip()
    if not text:
        raise ValueError("empty duration string")

    if text.isdigit():
        return float(text)

    total = 0.0
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None:
            raise ValueError(f"cannot parse duration {value!r} near {text[pos:]!r}")
        total += float(match.group(1)) * _UNIT_SECONDS[match.group(2).lower()]
        pos = match.end()

    return total


def humanize_delta(seconds: float, *, precision: int = 2) -> str:
    """Turn a second count into a short string. 9000 -> '2h 30m'.

    `precision` caps how many components are shown, most significant first.
    Zero is special-cased to '0s'. Negative values get a leading '-'.

    Deliberately coarse: this rounds to whole seconds and drops anything below
    a second, so 0.4 renders as '0s'. It's for log lines and status output, not
    for measuring anything.
    """
    if precision < 1:
        raise ValueError("precision must be >= 1")

    whole = int(round(seconds))
    if whole == 0:
        return "0s"

    sign = "-" if whole < 0 else ""
    whole = abs(whole)

    parts: list[str] = []
    for label, unit in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if whole >= unit:
            count, whole = divmod(whole, unit)
            parts.append(f"{count}{label}")
        if len(parts) == precision:
            break

    return sign + " ".join(parts)


def retry(
    times: int = 3,
    *,
    backoff: float = 0.5,
    factor: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator that retries a function on failure with exponential backoff.

        @retry(times=4, backoff=0.2)
        def fetch(url):
            ...

    `times` is the total number of attempts, not the number of retries. So
    times=3 means up to three calls. Sleeps `backoff` before the second attempt,
    then backoff * factor before the third, and so on. The final exception is
    re-raised unchanged so the traceback points at the real failure.

    Sync only. Wrapping an async function with this returns a coroutine that is
    never awaited and no retries happen. I left async out rather than write a
    version that silently misbehaves; if you need it, wrap the awaits yourself.
    """
    if times < 1:
        raise ValueError("times must be >= 1")
    if backoff < 0:
        raise ValueError("backoff must be >= 0")
    if factor < 1:
        raise ValueError("factor must be >= 1")

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = backoff
            last_exc: BaseException | None = None

            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: PERF203 - the loop is the point
                    last_exc = exc
                    if attempt == times:
                        break
                    time.sleep(delay)
                    delay *= factor

            # Unreachable unless times < 1, which we already rejected.
            assert last_exc is not None
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator
