"""Tiny JSON-over-HTTP client built on urllib.

Yes, urllib. I know requests exists. The rule for this package is stdlib-only,
and for "GET a JSON document and give me a dict" urllib is enough. If you need
connection pooling, redirects with auth, or multipart uploads, use httpx and
skip this module.

What you get here that bare urlopen doesn't: a sane timeout default, retries on
transient failures only, and exceptions that carry the status code and a chunk
of the response body so you can see what the server actually said.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

__all__ = ["get_json", "NetError", "HttpStatusError", "USER_AGENT"]

USER_AGENT = "python-utils/0.4.2 (+https://github.com/c991china/python-utils)"

# Statuses worth trying again. 429 is rate limiting, 5xx is the server having a
# bad time. Everything else (400, 401, 403, 404) means retrying changes nothing.
_RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class NetError(RuntimeError):
    """Base class for anything this module raises."""


class HttpStatusError(NetError):
    """The server answered, but with a status we don't accept."""

    def __init__(self, url: str, status: int, body: str = "") -> None:
        self.url = url
        self.status = status
        self.body = body
        snippet = " ".join(body.split())[:200]
        super().__init__(f"HTTP {status} for {url}: {snippet or '<empty body>'}")


def get_json(
    url: str,
    *,
    timeout: float = 10.0,
    retries: int = 2,
    backoff: float = 0.5,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """GET `url` and parse the body as JSON.

    `retries` counts extra attempts, so retries=2 means up to three requests.
    Backoff doubles each time: 0.5s, then 1s.

    Raises:
        HttpStatusError: non-2xx response. Retried first if the status is
            transient (429/5xx and friends).
        NetError: DNS failure, connection refused, TLS error, read timeout, or
            a body that isn't valid JSON.

    Timeout is a single number covering connect and read. urlopen does not let
    you set them separately; that's another reason to reach for httpx on
    anything serious.
    """
    if retries < 0:
        raise ValueError("retries must be >= 0")
    if timeout <= 0:
        raise ValueError("timeout must be > 0")

    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}{'&' if '?' in url else '?'}{query}"

    request_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)

    delay = backoff
    last_error: NetError | None = None

    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    return json.loads(raw.decode(charset))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    # Don't retry this. A 200 with a broken body is not transient.
                    head = raw[:120].decode("utf-8", "replace")
                    raise NetError(
                        f"{url} returned {len(raw)} bytes that aren't JSON "
                        f"({exc.__class__.__name__}: {exc}); starts with {head!r}"
                    ) from exc

        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001 - best effort, never mask the status
                pass
            error = HttpStatusError(url, exc.code, body)
            if exc.code not in _RETRYABLE_STATUS:
                raise error from exc
            last_error = error

        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout):
                message = f"{url} timed out after {timeout}s"
            elif isinstance(reason, socket.gaierror):
                message = f"{url} could not resolve host ({reason})"
            else:
                message = f"{url} connection failed: {reason}"
            last_error = NetError(message)

        if attempt < retries:
            time.sleep(delay)
            delay *= 2

    assert last_error is not None
    raise last_error
