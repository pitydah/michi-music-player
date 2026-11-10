"""Micro Server application service (E3): snapshots, capabilities, pairing view.

Composes the port into dashboard-friendly projections. Never invents endpoints
and never replicates server logic (master plan §154); callers run the I/O off
the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi_ecosystem.domain.servers import (
    ReceiverSummary,
    ServerConformance,
    ServerHealth,
    ServerInfoResult,
)
from michi_ecosystem.ports.micro_server import MicroServerPort


@dataclass(frozen=True)
class MicroServerSnapshot:
    info: ServerInfoResult
    health: ServerHealth
    receivers: tuple[ReceiverSummary, ...]


class MicroServerService:
    def __init__(self, port: MicroServerPort) -> None:
        self._port = port

    def snapshot(self) -> MicroServerSnapshot:
        return MicroServerSnapshot(
            info=self._port.server_info(),
            health=self._port.health(),
            receivers=self._port.receivers(),
        )

    def capabilities(self) -> tuple[str, ...]:
        return self._port.server_info().info.capabilities()

    def conformance(self) -> ServerConformance:
        return self._port.server_info().conformance

    def pairing_pending(self) -> tuple[ReceiverSummary, ...]:
        """Receivers needing pairing or trust completion (recovery surface)."""
        return tuple(
            receiver for receiver in self._port.receivers() if receiver.pairing_pending
        )
