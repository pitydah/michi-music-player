"""Reference receiver-lite command adapter (I4).

Implements the Ecosystem side of the documented Michi Link receiver endpoints:

- ``GET  {base}/receiver-lite/diagnostics``  (Bearer; schema not frozen by ADR)
- ``POST {base}/receiver-lite/firmware``     (Bearer; firmware may answer 501)

No playback authority, no GUI-thread I/O: the host calls these methods from a
worker (the Factory/Stream bridges already do). Every failure is a typed
``StreamCommandError`` with a stable code; response bodies are sanitized
recursively before reaching UI/history. Network reprovisioning has no frozen
upstream endpoint and is reported as unsupported instead of invented.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, Protocol

DEFAULT_TIMEOUT_SECONDS = 5.0
_FORBIDDEN_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "private",
    "authorization",
    "access_token",
    "refresh_token",
    "credential",
)


class StreamCommandError(RuntimeError):
    """A receiver command failed with a stable, non-secret code."""

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        self.code = code
        self.status = status
        self.message = message
        super().__init__(f"{code}: {message}")


class HttpCommandTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]: ...


class UrllibCommandTransport:
    """Minimal stdlib transport (hosts may inject their own)."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        request = urllib.request.Request(
            url, data=body, headers=dict(headers), method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return int(response.status), response.read()
        except urllib.error.HTTPError as exc:
            return int(exc.code), exc.read()
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            # Normalized: exception text may contain network addresses.
            raise StreamCommandError(
                "TRANSPORT_ERROR", "no se pudo contactar al receptor"
            ) from exc


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not any(
                fragment in str(key).lower() for fragment in _FORBIDDEN_FRAGMENTS
            )
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _status_error(status: int) -> StreamCommandError:
    mapping = {
        400: ("INVALID_REQUEST", "el receptor rechazó la solicitud"),
        401: ("AUTH_REQUIRED", "se requiere una sesión autorizada del Home"),
        403: ("FORBIDDEN", "el Home no autoriza esta operación"),
        404: ("ENDPOINT_UNAVAILABLE", "el firmware no expone este endpoint"),
        409: ("CONFLICT", "el receptor está en un estado incompatible"),
        501: ("UNSUPPORTED_UPSTREAM", "el firmware no implementa esta operación"),
    }
    code, message = mapping.get(
        status, ("UPSTREAM_ERROR", f"el receptor respondió HTTP {status}")
    )
    return StreamCommandError(code, message, status=status)


class ReceiverLiteCommandAdapter:
    """`StreamManagementCommandPort` reference implementation (consumer side).

    ``endpoint_resolver(canonical_id)`` returns the receiver API base URL,
    e.g. ``http://192.168.1.50:8600/api/v1`` (as advertised by discovery).
    ``token_provider(canonical_id)`` returns the Home-authorized bearer token.
    """

    def __init__(
        self,
        endpoint_resolver: Callable[[str], str | None],
        *,
        token_provider: Callable[[str], str | None] | None = None,
        transport: HttpCommandTransport | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._endpoint_resolver = endpoint_resolver
        self._token_provider = token_provider
        self._transport = transport or UrllibCommandTransport()
        self._timeout = float(timeout)

    # ── StreamManagementCommandPort ─────────────────────────────────────

    def diagnostics(self, canonical_id: str) -> dict[str, Any]:
        payload = self._json("GET", canonical_id, "/receiver-lite/diagnostics")
        return _sanitize(payload)

    def request_firmware_update(self, canonical_id: str) -> None:
        self._request("POST", canonical_id, "/receiver-lite/firmware", body=b"{}")

    def reprovision_network(self, canonical_id: str) -> None:
        raise StreamCommandError(
            "UNSUPPORTED_UPSTREAM",
            "no existe un contrato congelado de reprovisión de red en el receptor",
        )

    # ── internals ───────────────────────────────────────────────────────

    def _base(self, canonical_id: str) -> str:
        try:
            base = self._endpoint_resolver(str(canonical_id))
        except Exception as exc:
            raise StreamCommandError(
                "DEVICE_ENDPOINT_UNKNOWN", "no se pudo resolver el receptor"
            ) from exc
        if not isinstance(base, str) or not base.strip():
            raise StreamCommandError(
                "DEVICE_ENDPOINT_UNKNOWN",
                "el receptor no tiene una dirección conocida",
            )
        return base.rstrip("/")

    def _token(self, canonical_id: str) -> str:
        if self._token_provider is None:
            raise StreamCommandError(
                "AUTH_REQUIRED", "el host no proporcionó una sesión del Home"
            )
        try:
            token = self._token_provider(str(canonical_id))
        except Exception as exc:
            raise StreamCommandError(
                "AUTH_REQUIRED", "no se pudo obtener la sesión del Home"
            ) from exc
        if not isinstance(token, str) or not token.strip():
            raise StreamCommandError(
                "AUTH_REQUIRED", "la sesión del Home no está disponible"
            )
        return token.strip()

    def _request(
        self,
        method: str,
        canonical_id: str,
        path: str,
        *,
        body: bytes | None = None,
    ) -> bytes:
        base = self._base(canonical_id)
        token = self._token(canonical_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            status, payload = self._transport.request(
                method,
                f"{base}{path}",
                headers=headers,
                body=body,
                timeout=self._timeout,
            )
        except StreamCommandError:
            raise
        except Exception as exc:
            raise StreamCommandError(
                "TRANSPORT_ERROR", "no se pudo contactar al receptor"
            ) from exc
        if status >= 300:
            raise _status_error(status)
        return payload

    def _json(self, method: str, canonical_id: str, path: str) -> dict[str, Any]:
        payload = self._request(method, canonical_id, path)
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise StreamCommandError(
                "INVALID_RESPONSE", "el receptor devolvió una respuesta inválida"
            ) from exc
        if not isinstance(decoded, dict):
            raise StreamCommandError(
                "INVALID_RESPONSE", "el receptor devolvió un objeto inesperado"
            )
        return decoded
