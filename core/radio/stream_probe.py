from __future__ import annotations

import contextlib
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Callable

from core.radio.icy_parser import parse_icy_headers, parse_icy_metaint
from core.radio.models import (
    ProbeStatus, StreamProbeResult, StreamCapabilities, StreamMetadata,
)
from core.radio.url_utils import validate_and_normalize_url

_CONNECT_TIMEOUT_S = 10
_READ_TIMEOUT_S = 15
_MAX_REDIRECTS = 5
_MAX_READ_BYTES = 65536
_ACCEPTED_CONTENT_PREFIXES = (
    "audio/", "application/ogg", "application/x-mpegurl",
    "application/vnd.apple.mpegurl", "audio/x-mpegurl",
    "audio/x-scpls", "audio/x-ms-wax",
)
_STREAM_CODEC_MAP = {
    "audio/mpeg": "MP3",
    "audio/aac": "AAC",
    "audio/aacp": "AAC",
    "audio/ogg": "Ogg",
    "audio/opus": "Opus",
    "audio/flac": "FLAC",
    "audio/wav": "WAV",
    "audio/x-wav": "WAV",
    "audio/x-ms-wma": "WMA",
    "audio/x-ape": "APE",
    "audio/x-musepack": "MPC",
}


class StreamProbeService:
    def __init__(self, http_client: Callable | None = None):
        self._http_client = http_client

    def probe(self, url: str, generation: int = 0, cancel_token: Callable[[], bool] | None = None) -> StreamProbeResult:
        result = StreamProbeResult(requested_url=url)
        result.status = ProbeStatus.ERROR

        try:
            url = validate_and_normalize_url(url)
        except ValueError as e:
            result.status = ProbeStatus.INVALID
            result.error = str(e)
            return result

        result.final_url = url
        start = time.monotonic()

        try:
            if self._http_client:
                return self._probe_via_client(url, result, generation, cancel_token)
            return self._probe_via_urllib(url, result, start, cancel_token)
        except Exception as e:
            result.status = ProbeStatus.ERROR
            result.error = str(e)
            result.latency_ms = (time.monotonic() - start) * 1000
            return result

    def _probe_via_urllib(self, url: str, result: StreamProbeResult,
                          start: float, cancel_token: Callable[[], bool] | None = None) -> StreamProbeResult:
        if cancel_token and cancel_token():
            result.status = ProbeStatus.CANCELLED
            result.error = "Cancelled"
            return result

        req = urllib.request.Request(url, method="GET", headers={
            "Icy-MetaData": "1",
            "User-Agent": "MichiMusicPlayer/1.0",
            "Accept": "*/*",
        })

        try:
            resp = urllib.request.urlopen(
                req, timeout=_CONNECT_TIMEOUT_S,
                cafile=None, capath=None,
            )
        except urllib.error.HTTPError as e:
            result.http_status = e.code
            result.latency_ms = (time.monotonic() - start) * 1000
            if e.code == 404:
                result.status = ProbeStatus.INVALID
                result.error = f"HTTP {e.code}"
                result.http_status = e.code
            elif 500 <= e.code < 600:
                result.status = ProbeStatus.INVALID
                result.error = f"Server error HTTP {e.code}"
            else:
                result.status = ProbeStatus.INVALID
                result.error = f"HTTP {e.code}"
            return result
        except urllib.error.URLError as e:
            result.latency_ms = (time.monotonic() - start) * 1000
            if isinstance(e.reason, socket.timeout):
                result.status = ProbeStatus.TIMEOUT
                result.error = "Connection timed out"
            elif isinstance(e.reason, ssl.SSLError):
                result.status = ProbeStatus.ERROR
                result.error = f"TLS error: {e.reason}"
            else:
                result.status = ProbeStatus.ERROR
                result.error = str(e.reason)
            return result
        except socket.timeout:
            result.latency_ms = (time.monotonic() - start) * 1000
            result.status = ProbeStatus.TIMEOUT
            result.error = "Connection timed out"
            return result

        result.http_status = resp.status
        headers = dict(resp.headers)

        content_type = (headers.get("Content-Type", "") or "").split(";")[0].strip()
        result.content_type = content_type
        result.codec = _STREAM_CODEC_MAP.get(content_type, "")
        result.final_url = resp.url

        raw_headers = b"\r\n".join(
            f"{k}: {v}".encode("utf-8") for k, v in resp.headers.items()
        )
        icymeta = parse_icy_headers(raw_headers)
        result.icy_name = icymeta.icy_name
        result.icy_genre = icymeta.icy_genre
        result.icy_url = icymeta.icy_url
        result.icy_metaint = parse_icy_metaint(raw_headers)

        if icymeta.icy_br:
            with contextlib.suppress(ValueError, TypeError):
                result.bitrate = int(icymeta.icy_br)

        redirect_count = 0
        if hasattr(resp, "url") and resp.url != url:
            redirect_count += 1
            result.redirect_count = redirect_count

        if cancel_token and cancel_token():
            resp.close()
            result.status = ProbeStatus.CANCELLED
            result.error = "Cancelled"
            return result

        try:
            resp.read(_MAX_READ_BYTES)
        except Exception:
            pass
        finally:
            resp.close()

        result.supports_metadata = result.icy_metaint > 0 or bool(icymeta.icy_name)
        result.latency_ms = (time.monotonic() - start) * 1000

        if content_type and content_type.startswith(_ACCEPTED_CONTENT_PREFIXES) or content_type in ("", "text/html") and redirect_count > 0 or content_type in ("", "application/octet-stream"):
            result.status = ProbeStatus.VALID
        else:
            result.status = ProbeStatus.UNSUPPORTED
            result.error = f"Unsupported content type: {content_type}"

        result.capabilities = StreamCapabilities(
            supports_icy=result.icy_metaint > 0,
            supports_playlist=content_type in (
                "audio/x-mpegurl", "application/x-mpegurl",
                "application/vnd.apple.mpegurl", "audio/x-scpls",
            ),
            codec=result.codec,
            bitrate=result.bitrate,
        )

        result.metadata = StreamMetadata(
            icy_name=icymeta.icy_name,
            icy_genre=icymeta.icy_genre,
            icy_url=icymeta.icy_url,
            icy_br=icymeta.icy_br,
        )

        return result

    def _probe_via_client(self, url: str, result: StreamProbeResult,
                          generation: int, cancel_token: Callable[[], bool] | None) -> StreamProbeResult:
        start = time.monotonic()
        try:
            status_code, body, headers = self._http_client(
                "GET", url,
                headers={"Icy-MetaData": "1", "User-Agent": "MichiMusicPlayer/1.0"},
                timeout_ms=_CONNECT_TIMEOUT_S * 1000,
                follow_redirects=True, max_redirects=_MAX_REDIRECTS,
            )
        except Exception as e:
            result.status = ProbeStatus.ERROR
            result.error = str(e)
            result.latency_ms = (time.monotonic() - start) * 1000
            return result

        result.http_status = status_code
        result.latency_ms = (time.monotonic() - start) * 1000
        ct = (headers.get("content-type", "") or "").split(";")[0].strip()
        result.content_type = ct
        result.codec = _STREAM_CODEC_MAP.get(ct, "")

        raw_headers = "\r\n".join(f"{k}: {v}" for k, v in headers.items()).encode("utf-8")
        icymeta = parse_icy_headers(raw_headers)
        result.icy_name = icymeta.icy_name
        result.icy_genre = icymeta.icy_genre
        result.icy_url = icymeta.icy_url
        result.icy_metaint = parse_icy_metaint(raw_headers)

        if icymeta.icy_br:
            with contextlib.suppress(ValueError, TypeError):
                result.bitrate = int(icymeta.icy_br)

        result.supports_metadata = result.icy_metaint > 0
        result.capabilities = StreamCapabilities(
            supports_icy=result.icy_metaint > 0,
            codec=result.codec, bitrate=result.bitrate,
        )

        if status_code == 200 and ct and ct.startswith(_ACCEPTED_CONTENT_PREFIXES):
            result.status = ProbeStatus.VALID
        elif status_code == 404:
            result.status = ProbeStatus.INVALID
            result.error = "HTTP 404"
        elif 500 <= status_code < 600:
            result.status = ProbeStatus.INVALID
            result.error = f"Server error HTTP {status_code}"
        elif status_code == 200:
            result.status = ProbeStatus.VALID if ct in ("", "application/octet-stream") else ProbeStatus.UNSUPPORTED
            if result.status == ProbeStatus.UNSUPPORTED:
                result.error = f"Unsupported content type: {ct}"
        else:
            result.status = ProbeStatus.INVALID
            result.error = f"HTTP {status_code}"

        return result
