"""Micro Server port (master plan §154.1), shaped on the real ``/api/v1`` API.

Implementations perform network I/O; orchestration must run them off the GUI
thread. Roles, endpoints and error semantics follow the canonical server
repository (``michi-micro-server``) — never invented here.
"""

from __future__ import annotations

from typing import Protocol

from michi_ecosystem.domain.servers import (
    DiagnosticsSummary,
    ReceiverSummary,
    ServerHealth,
    ServerInfoResult,
)
from michi_ecosystem.domain.trust import PairingConfirmation, PairingStart


class MicroServerRequestError(RuntimeError):
    """An upstream request failed with a canonical error code."""

    def __init__(self, code: str, message: str, status: int = 0) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"HTTP {status} {code}: {message}")


class MicroServerPort(Protocol):
    """Consumer view of a Michi Micro Server."""

    def ready(self) -> bool:
        """``GET /health/ready`` — cheap liveness probe."""
        ...

    def server_info(self) -> ServerInfoResult:
        """``GET /api/v1/server/info`` with a contract-conformance verdict."""
        ...

    def health(self) -> ServerHealth:
        """``GET /api/v1/status``."""
        ...

    def diagnostics(self) -> DiagnosticsSummary:
        """``GET /api/v1/diagnostics`` (compact projection)."""
        ...

    def receivers(self) -> tuple[ReceiverSummary, ...]:
        """``GET /api/v1/receivers``."""
        ...

    def start_receiver_pairing(
        self,
        *,
        receiver_id: str | None = None,
        base_url: str | None = None,
        re_pair: bool = False,
    ) -> PairingStart:
        """``POST /api/v1/receivers/pair/start``."""
        ...

    def confirm_receiver_pairing(
        self,
        *,
        pin: str,
        pairing_id: str | None = None,
        receiver_id: str | None = None,
    ) -> PairingConfirmation:
        """``POST /api/v1/receivers/pair/confirm``."""
        ...
