"""Firmware repository port (R6).

Product implementations consume only the official GitHub Releases channel;
``materialize`` requires an authenticity verifier — HTTPS alone is never
declared as firmware authenticity.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from michi_ecosystem.domain.firmware import (
    FirmwareProvenance,
    FirmwareRelease,
    ResolvedFirmware,
)


class FirmwareRepositoryPort(Protocol):
    def recommended(
        self, board: str, channel: str = "stable"
    ) -> FirmwareRelease | None: ...

    def materialize(
        self,
        release: FirmwareRelease,
        *,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> ResolvedFirmware: ...


class ManifestAuthenticityVerifierPort(Protocol):
    def verify(
        self, manifest_bytes: bytes, *, provenance: FirmwareProvenance
    ) -> bool: ...
