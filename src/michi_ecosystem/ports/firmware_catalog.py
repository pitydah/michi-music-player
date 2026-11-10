"""Firmware catalog port: published artifacts and channels (§134, §165).

Ecosystem consumes artifacts produced and verified by michi-music-stream
tooling; it never builds firmware inside the user flow.
"""

from __future__ import annotations

from typing import Protocol

from michi_ecosystem.domain.flashing import FirmwareManifest


class FirmwareCatalogPort(Protocol):
    def recommended(
        self, board: str, channel: str = "stable"
    ) -> FirmwareManifest | None: ...

    def load(self, reference: str) -> FirmwareManifest: ...
