"""HTTP client helpers — safe remote requests with byte limits and timeouts."""

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("michi.http_client")

USER_AGENT = "MichiMusicPlayer/0.1"
_DEFAULT_TIMEOUT = 15
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


class HttpResult:
    def __init__(self):
        self.ok: bool = False
        self.status: int = 0
        self.data: Any = None
        self.error: str = ""
        self.truncated: bool = False


def http_get_json(
    url: str,
    timeout: float = _DEFAULT_TIMEOUT,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    headers: dict | None = None,
) -> HttpResult:
    """GET a URL and parse the response as JSON. Truncates at max_bytes."""
    raw = _http_get_bytes(url, timeout, max_bytes, headers)
    result = HttpResult()
    result.status = raw.status
    result.error = raw.error
    result.truncated = raw.truncated
    if not raw.ok:
        return result
    try:
        result.data = json.loads(raw.data.decode("utf-8"))
        result.ok = True
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        result.error = f"Invalid JSON: {e}"
    return result


def http_get_bytes(
    url: str,
    timeout: float = _DEFAULT_TIMEOUT,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    headers: dict | None = None,
) -> HttpResult:
    """GET a URL and return raw bytes. Truncates at max_bytes."""
    return _http_get_bytes(url, timeout, max_bytes, headers)


def _http_get_bytes(url: str, timeout: float, max_bytes: int,
                    headers: dict | None = None) -> HttpResult:
    result = HttpResult()
    req = Request(url)
    req.add_header("User-Agent", USER_AGENT)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urlopen(req, timeout=timeout) as resp:
            result.status = resp.status
            body = resp.read(max_bytes + 1)
            if len(body) > max_bytes:
                result.truncated = True
                body = body[:max_bytes]
            result.data = body
            result.ok = True
    except HTTPError as e:
        result.status = e.code
        result.error = str(e)
    except URLError as e:
        result.error = str(e)
    except OSError as e:
        result.error = str(e)
    return result


def validate_url(url: str) -> bool:
    """Check if URL has a valid http/https scheme and non-empty host."""
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False
