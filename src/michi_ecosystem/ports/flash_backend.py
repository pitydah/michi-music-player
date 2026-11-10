"""Flash backend port (master plan §134, §142).

Implementations write/erase/verify/reset through esptool (or a simulator).
Wi-Fi credentials never travel through shell arguments; only opaque bounded
blobs are written, using secure temporary files. ``verify_segment`` reads the
flash back and compares the digest — ``VERIFYING_FLASH`` must verify real
content, never a decorative stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from michi_ecosystem.domain.flashing import PhysicalDeviceIdentity


class FlashBackendError(RuntimeError):
    """A backend operation failed (erase/write/reset/read)."""


class FlashVerificationError(FlashBackendError):
    """Read-back verification did not match the expected digest."""


class FlashResetError(FlashBackendError):
    """The board reset could not be executed; never report silent success."""


class FlashBackendPort(Protocol):
    def probe_chip(self, port: str) -> str | None: ...

    def read_device_identity(self, port: str) -> PhysicalDeviceIdentity | None: ...

    def erase_flash(self, port: str) -> None: ...

    def write_segment(self, port: str, offset: int, payload: bytes) -> None: ...

    def verify_segment(
        self, port: str, offset: int, size: int, expected_sha256: str
    ) -> bool: ...

    def hard_reset(self, port: str) -> None: ...
