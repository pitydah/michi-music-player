"""Serial device port: enumeration of USB candidates (master plan §134–§135).

VID/PID and port names are signals, never identity; access-denied is distinct
from no-device (the UI copy differs, see docs/ux/error-copy.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SerialCandidate:
    port: str
    description: str = ""
    vid: int | None = None
    pid: int | None = None
    serial_number: str = ""
    access_denied: bool = False


class SerialDevicesPort(Protocol):
    def scan(self) -> tuple[SerialCandidate, ...]: ...

    def port_still_present(self, port: str) -> bool: ...
