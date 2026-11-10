"""HTTP client for the Michi Micro Server public API (E3+E7).

Grounded on the real API (``michi-micro-server`` route table in
``crates/michi-api/src/lib.rs`` and ``docs/API.md``): ``/api/v1/server/info``
(no auth), ``/api/v1/status``, ``/api/v1/diagnostics``, ``/api/v1/receivers``,
the receiver pairing endpoints and ``/health/live|ready``. Bearer-token auth;
v1 errors follow the canonical envelope ``{"error": {"code", "message"}}``.

The transport is injectable so orchestration can keep network I/O off the GUI
thread and tests can fake it without a live server (master plan §154.2).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from michi_ecosystem.domain.servers import (
    DiagnosticsSummary,
    ReceiverSummary,
    ServerHealth,
    ServerInfoResult,
)
from michi_ecosystem.domain.trust import PairingConfirmation, PairingStart
from michi_ecosystem.infrastructure.michi_link.contracts import ContractBundle
from michi_ecosystem.infrastructure.micro_server import projection
from michi_ecosystem.ports.micro_server import MicroServerRequestError

DEFAULT_TIMEOUT_SECONDS = 5.0


class MicroServerError(MicroServerRequestError):
    """A Micro Server request failed (transport, HTTP or payload level)."""

    def __init__(self, path: str, status: int, code: str, message: str) -> None:
        self.path = path
        super().__init__(code, message, status)
        self.args = (f"{path}: HTTP {status} {code}: {message}",)


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class HttpTransport(Protocol):
    def get(
        self, url: str, headers: Mapping[str, str], timeout: float
    ) -> HttpResponse: ...

    def post(
        self, url: str, headers: Mapping[str, str], body: bytes, timeout: float
    ) -> HttpResponse: ...


class UrllibTransport:
    """Default stdlib transport (no third-party dependency)."""

    def get(self, url: str, headers: Mapping[str, str], timeout: float) -> HttpResponse:
        return self._request(url, headers, timeout, data=None)

    def post(
        self, url: str, headers: Mapping[str, str], body: bytes, timeout: float
    ) -> HttpResponse:
        return self._request(url, headers, timeout, data=body)

    def _request(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
        *,
        data: bytes | None,
    ) -> HttpResponse:
        request = urllib.request.Request(
            url, headers=dict(headers), data=data, method="POST" if data else "GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return HttpResponse(status=int(response.status), body=response.read())
        except urllib.error.HTTPError as exc:
            return HttpResponse(status=int(exc.code), body=exc.read())


class MicroServerClient:
    """Typed consumer of the Micro Server public API."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        transport: HttpTransport | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        contracts: ContractBundle | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._transport = transport or UrllibTransport()
        self._timeout = timeout
        self._contracts = contracts

    @property
    def base_url(self) -> str:
        return self._base_url

    def ready(self) -> bool:
        """Cheap unauthenticated liveness probe."""
        try:
            response = self._transport.get(
                f"{self._base_url}/health/ready", self._headers(), self._timeout
            )
        except OSError:
            return False
        return response.status == 200

    def server_info(self) -> ServerInfoResult:
        return projection.project_server_info(
            self._get_json("/api/v1/server/info"), self._contracts
        )

    def health(self) -> ServerHealth:
        return projection.project_health(self._get_json("/api/v1/status"))

    def diagnostics(self) -> DiagnosticsSummary:
        return projection.project_diagnostics(self._get_json("/api/v1/diagnostics"))

    def receivers(self) -> tuple[ReceiverSummary, ...]:
        return projection.project_receivers(self._get_json("/api/v1/receivers"))

    def playback_state(self) -> Mapping[str, Any]:
        """``GET /api/v1/playback/state`` (raw payload for the E9 substrate)."""
        return self._get_json("/api/v1/playback/state")

    def playback_control(self, body: Mapping[str, Any]) -> Mapping[str, Any]:
        """``POST /api/v1/playback/control`` with a canonical command body."""
        return self._post_json("/api/v1/playback/control", body)

    def start_receiver_pairing(
        self,
        *,
        receiver_id: str | None = None,
        base_url: str | None = None,
        re_pair: bool = False,
    ) -> PairingStart:
        body: dict[str, Any] = {}
        if receiver_id:
            body["receiver_id"] = receiver_id
        if base_url:
            body["base_url"] = base_url
        if re_pair:
            body["re_pair"] = True
        response = self._post_json("/api/v1/receivers/pair/start", body)
        try:
            return PairingStart(
                pairing_id=str(response["pairing_id"]),
                receiver_base_url=str(response["receiver_base_url"]),
                receiver_pair_session_id=str(response["receiver_pair_session_id"]),
                expires_at=str(response["expires_at"]),
            )
        except KeyError as exc:
            raise MicroServerError(
                "/api/v1/receivers/pair/start",
                200,
                "invalid_payload",
                f"pairing start response is missing {exc}",
            ) from exc

    def confirm_receiver_pairing(
        self,
        *,
        pin: str,
        pairing_id: str | None = None,
        receiver_id: str | None = None,
    ) -> PairingConfirmation:
        body: dict[str, Any] = {"pin": pin}
        if pairing_id:
            body["pairing_id"] = pairing_id
        if receiver_id:
            body["receiver_id"] = receiver_id
        response = self._post_json("/api/v1/receivers/pair/confirm", body)
        receiver = response.get("receiver_id", response.get("device_id", ""))
        return PairingConfirmation(
            status=str(response.get("status", "")),
            receiver_id=str(receiver or ""),
            payload=dict(response),
        )

    # ── plumbing ────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _get_json(self, path: str) -> Mapping[str, Any]:
        return self._request_json("GET", path)

    def _post_json(self, path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request_json("POST", path, body)

    def _request_json(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        url = f"{self._base_url}{path}"
        headers = self._headers()
        try:
            if method == "POST":
                headers["Content-Type"] = "application/json"
                payload = json.dumps(body or {}).encode("utf-8")
                response = self._transport.post(url, headers, payload, self._timeout)
            else:
                response = self._transport.get(url, headers, self._timeout)
        except OSError as exc:
            raise MicroServerError(path, 0, "transport_error", str(exc)) from exc

        if response.status != 200:
            code, message = _error_envelope(response.body)
            raise MicroServerError(path, response.status, code, message)

        try:
            data = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MicroServerError(
                path, response.status, "invalid_json", str(exc)
            ) from exc
        if not isinstance(data, Mapping):
            raise MicroServerError(
                path, response.status, "invalid_payload", "expected a JSON object"
            )
        return data


def _error_envelope(body: bytes) -> tuple[str, str]:
    """Parse the canonical v1 error envelope (falls back to the raw body)."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ("http_error", body.decode("utf-8", "replace")[:200])
    if isinstance(payload, Mapping):
        error = payload.get("error")
        if isinstance(error, Mapping):
            return (
                str(error.get("code", "http_error")),
                str(error.get("message", "")),
            )
        if "message" in payload:
            return ("http_error", str(payload.get("message", "")))
    return ("http_error", "")
