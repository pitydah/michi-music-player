from __future__ import annotations

import contextlib
import unicodedata
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs, quote

from core.radio.models import RadioError

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_URL_LENGTH = 2048


class UrlNormalizationError(ValueError):
    def __init__(self, message: str, error: RadioError = RadioError.URL_INVALID):
        super().__init__(message)
        self.error = error


def validate_and_normalize_url(raw: str) -> str:
    if not raw or not raw.strip():
        raise UrlNormalizationError("URL is empty", RadioError.URL_MALFORMED)

    raw = raw.strip()

    if len(raw) > MAX_URL_LENGTH:
        raise UrlNormalizationError("URL exceeds maximum length", RadioError.URL_MALFORMED)

    if _looks_like_local_path(raw):
        raise UrlNormalizationError("Local file paths are not allowed", RadioError.URL_UNSUPPORTED_SCHEME)

    if "://" not in raw:
        raw = "https://" + raw

    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()

    if scheme not in ALLOWED_SCHEMES:
        raise UrlNormalizationError(
            f"Unsupported scheme: {scheme}", RadioError.URL_UNSUPPORTED_SCHEME,
        )

    if not parsed.hostname:
        raise UrlNormalizationError("Missing hostname", RadioError.URL_MALFORMED)

    raw_hostname = parsed.hostname.lower()
    raw_hostname = _normalize_hostname(raw_hostname)

    if _is_ipv6_bare(raw_hostname):
        raw_hostname = f"[{raw_hostname.strip('[]')}]"

    netloc = raw_hostname
    if parsed.port:
        netloc = f"{raw_hostname}:{parsed.port}"

    path = parsed.path.rstrip("/") or "/"
    path = _normalize_path(path)

    params = parsed.params
    query = _normalize_query(parsed.query)
    fragment = ""

    normalized = urlunparse((scheme, netloc, path, params, query, fragment))

    return normalized


def _looks_like_local_path(url: str) -> bool:
    if url.startswith("/") or url.startswith("./") or url.startswith("../"):
        return True
    if url.startswith("file://"):
        return True
    return bool(url.startswith("~"))


def _normalize_hostname(hostname: str) -> str:
    if hostname.startswith("xn--"):
        return hostname
    with contextlib.suppress(UnicodeError, ValueError):
        hostname = hostname.encode("idna").decode("ascii")
    return hostname


def _normalize_path(path: str) -> str:
    path = quote(unicodedata.normalize("NFC", path), safe="/:@!$&'()*+,;=-._~")
    return path


def _normalize_query(query: str) -> str:
    if not query:
        return ""
    params = parse_qs(query, keep_blank_values=True)
    sorted_params = sorted(
        (k, v[0] if len(v) == 1 else v) for k, v in params.items()
    )
    return urlencode(sorted_params, doseq=True)


def _is_ipv6_bare(hostname: str) -> bool:
    hostname = hostname.strip("[]")
    return ":" in hostname


def urls_are_equivalent(url_a: str, url_b: str) -> bool:
    try:
        norm_a = validate_and_normalize_url(url_a)
        norm_b = validate_and_normalize_url(url_b)
    except UrlNormalizationError:
        return url_a.strip().lower() == url_b.strip().lower()
    return norm_a == norm_b
