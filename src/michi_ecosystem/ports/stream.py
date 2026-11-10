"""Ports for management of already-created Michi Music Streams."""

from __future__ import annotations

from typing import Any, Protocol


class StreamManagementCommandPort(Protocol):
    def diagnostics(self, canonical_id: str) -> dict[str, Any]: ...

    def request_firmware_update(self, canonical_id: str) -> None: ...

    def reprovision_network(self, canonical_id: str) -> None: ...
