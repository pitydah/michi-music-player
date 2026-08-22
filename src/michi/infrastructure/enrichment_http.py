"""Enrichment HTTP transport + MusicBrainz rate limiter (M6.9B).

Security contract (M6.9):
- HTTPS ONLY (no http/file/ftp/localhost/SSRF surface);
- provider host allowlist validated BEFORE request AND after redirects;
- bounded JSON/body size (MAX_PROVIDER_BODY_BYTES);
- meaningful application User-Agent;
- MusicBrainz requests are serialized at <= 1 request/second via a
  single process-wide rate limiter with injectable clock/sleeper.

Standard library only: urllib.request/parse, json, time, threading.
"""

import importlib.metadata
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from michi.application.enrichment_ports import (
    EnrichmentHttpStatusError,
    EnrichmentProviderError,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)

# 8 MiB — a provider JSON body must never exceed this (M6.9 contract).
MAX_PROVIDER_BODY_BYTES = 8 * 1024 * 1024

DEFAULT_TIMEOUT_SECONDS = 10.0

# Host allowlist: exact hosts or ".suffix" entries (any subdomain).
_ALLOWED_HOSTS = (
    "musicbrainz.org",
    "www.wikidata.org",
    ".wikipedia.org",
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "coverartarchive.org",
    "archive.org",
    ".archive.org",
)

_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _app_version() -> str:
    try:
        return importlib.metadata.version("michi-music-player")
    except importlib.metadata.PackageNotFoundError:
        return "development"


USER_AGENT = (
    f"MichiMusicPlayer/{_app_version()} (https://github.com/pitydah/michi-music-player)"
)


def is_allowed_host(host: str) -> bool:
    """Provider hostname allowlist (lowercased; exact or subdomain)."""
    host = (host or "").lower().strip()
    if not host or host in _BLOCKED_HOSTS:
        return False
    for entry in _ALLOWED_HOSTS:
        if entry.startswith("."):
            if host.endswith(entry):
                return True
        elif host == entry:
            return True
    return False


def validate_provider_url(url: str) -> None:
    """Raise ValueError unless the URL is a safe provider URL:
    https scheme, allowed host, no credentials, no localhost."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise ValueError(f"provider URL must use https: {url!r}")
    if parts.username or parts.password:
        raise ValueError(f"provider URL must not carry credentials: {url!r}")
    host = parts.hostname
    if host is None:
        raise ValueError(f"provider URL has no hostname: {url!r}")
    if not is_allowed_host(host):
        raise ValueError(f"provider host not allowlisted: {host!r}")


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Rejects redirects that leave the https + allowlist contract."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            validate_provider_url(newurl)
        except ValueError as exc:
            raise EnrichmentProviderError(f"provider redirect rejected: {exc}") from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UrllibHttpTransport(HttpTransportPort):
    """HTTPS-only, host-allowlisted, body-bounded provider transport.

    ``opener`` is injectable for tests (urllib opener built from the
    validating redirect handler by default)."""

    def __init__(self, opener=None) -> None:
        if opener is None:
            opener = urllib.request.build_opener(_ValidatingRedirectHandler())
        self._opener = opener

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.method != "GET":
            raise ValueError(f"only GET is supported, got {request.method!r}")
        try:
            validate_provider_url(request.url)
        except ValueError as exc:
            raise EnrichmentProviderError(str(exc)) from exc
        headers = dict(request.headers)
        headers.setdefault("User-Agent", USER_AGENT)
        headers.setdefault("Accept", "application/json")
        req = urllib.request.Request(request.url, headers=headers, method="GET")
        try:
            response = self._opener.open(req, timeout=request.timeout_seconds)
        except urllib.error.HTTPError as exc:
            raise EnrichmentHttpStatusError(
                exc.code,
                {k.lower(): v for k, v in (exc.headers or {}).items()},
                f"provider HTTP {exc.code} for {request.url}",
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise EnrichmentProviderError(
                f"provider request failed for {request.url}: {exc}"
            ) from exc
        try:
            body = self._read_bounded(response)
        except EnrichmentProviderError:
            response.close()
            raise
        status = getattr(response, "status", None)
        if not isinstance(status, int):
            status = response.getcode()
        final_url = response.geturl()
        try:
            validate_provider_url(final_url)
        except ValueError as exc:
            response.close()
            raise EnrichmentProviderError(f"provider final URL invalid: {exc}") from exc
        response_headers = {k.lower(): v for k, v in response.headers.items()}
        response.close()
        return HttpResponse(
            status_code=int(status),
            headers=response_headers,
            body=body,
            final_url=final_url,
        )

    @staticmethod
    def _read_bounded(response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_PROVIDER_BODY_BYTES:
                raise EnrichmentProviderError(
                    "provider body exceeds the configured maximum"
                )
            chunks.append(chunk)
        return b"".join(chunks)


class MusicBrainzRateLimiter:
    """Process-wide MusicBrainz serializer: NEVER more than one
    MusicBrainz request per second (M6.9 absolute policy).

    ``clock`` and ``sleeper`` are injectable (tests use fake monotonic
    clock; production uses time.monotonic / time.sleep)."""

    def __init__(
        self,
        min_interval_seconds: float = 1.0,
        clock=time.monotonic,
        sleeper=time.sleep,
    ) -> None:
        self._min_interval = min_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._last_request: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until at least min_interval_seconds have elapsed since
        the previous MusicBrainz request (serialized via the lock)."""
        with self._lock:
            now = self._clock()
            if self._last_request is not None:
                remaining = self._min_interval - (now - self._last_request)
                if remaining > 0:
                    self._sleeper(remaining)
                    now = self._clock()
            self._last_request = now

    @property
    def min_interval_seconds(self) -> float:
        return self._min_interval
