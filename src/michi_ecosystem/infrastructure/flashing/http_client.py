"""HTTP client for the firmware pipeline (R6): bounded, HTTPS-only, honest.

Responses are size-capped; redirects must land on HTTPS; downloads stream to a
``*.partial`` file and are renamed atomically only after completion.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

DEFAULT_JSON_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_DOWNLOAD_MAX_BYTES = 128 * 1024 * 1024
_CHUNK = 64 * 1024
_USER_AGENT = "michi-ecosystem-factory/0.1"


class HttpError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class HttpClientPort(Protocol):
    def get_json(self, url: str, *, timeout: float = 10.0) -> object: ...

    def get_bytes(
        self,
        url: str,
        *,
        timeout: float = 15.0,
        max_bytes: int = DEFAULT_JSON_MAX_BYTES,
    ) -> bytes: ...

    def download(
        self,
        url: str,
        destination: Path,
        *,
        timeout: float = 60.0,
        max_bytes: int = DEFAULT_DOWNLOAD_MAX_BYTES,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> None: ...


def _request(url: str) -> urllib.request.Request:
    if not url.startswith("https://"):
        raise HttpError("HTTPS_REQUIRED", f"solo se permite HTTPS: {url}")
    return urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "*/*"},
    )


def _check_final_url(response) -> None:
    final = response.geturl()
    if not str(final).startswith("https://"):
        raise HttpError("HTTPS_REQUIRED", f"redirect fuera de HTTPS: {final}")


class UrllibHttpClient:
    """Default stdlib HTTP client (no third-party dependency)."""

    def get_json(self, url: str, *, timeout: float = 10.0) -> object:
        raw = self.get_bytes(url, timeout=timeout)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HttpError("HTTP_BAD_JSON", str(exc)) from exc

    def get_bytes(
        self,
        url: str,
        *,
        timeout: float = 15.0,
        max_bytes: int = DEFAULT_JSON_MAX_BYTES,
    ) -> bytes:
        try:
            with urllib.request.urlopen(_request(url), timeout=timeout) as response:
                _check_final_url(response)
                data = response.read(max_bytes + 1)
        except HttpError:
            raise
        except urllib.error.HTTPError as exc:
            raise HttpError("HTTP_STATUS", f"{exc.code} para {url}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise HttpError("HTTP_UNAVAILABLE", str(exc)) from exc
        if len(data) > max_bytes:
            raise HttpError("HTTP_TOO_LARGE", f"respuesta > {max_bytes} bytes")
        return data

    def download(
        self,
        url: str,
        destination: Path,
        *,
        timeout: float = 60.0,
        max_bytes: int = DEFAULT_DOWNLOAD_MAX_BYTES,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> None:
        partial = destination.with_name(destination.name + ".partial")
        destination.parent.mkdir(parents=True, exist_ok=True)
        received = 0
        try:
            with urllib.request.urlopen(_request(url), timeout=timeout) as response:
                _check_final_url(response)
                length_header = response.headers.get("Content-Length")
                total = (
                    int(length_header)
                    if length_header and length_header.isdigit()
                    else None
                )
                if total is not None and total > max_bytes:
                    raise HttpError("HTTP_TOO_LARGE", f"download > {max_bytes} bytes")
                with partial.open("wb") as handle:
                    while True:
                        chunk = response.read(_CHUNK)
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > max_bytes:
                            raise HttpError(
                                "HTTP_TOO_LARGE", f"download > {max_bytes} bytes"
                            )
                        handle.write(chunk)
                        if progress is not None:
                            progress(received, total)
                    handle.flush()
                    os.fsync(handle.fileno())
            os.replace(partial, destination)
        except HttpError:
            partial.unlink(missing_ok=True)
            raise
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            partial.unlink(missing_ok=True)
            raise HttpError("HTTP_UNAVAILABLE", str(exc)) from exc
