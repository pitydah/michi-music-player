"""Installation detection port (WP-3): is there already a Michi installation?

CREATE_NEW must never erase an existing Stream. Until the firmware publishes a
product/factory marker contract (STREAM-REQ-005), detection uses read-only
flash forensics; anything unknown fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class InstallationEvidence(StrEnum):
    BLANK = "blank"
    INSTALLED = "installed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InstallationReport:
    evidence: InstallationEvidence
    detail: str = ""
    product_evidence: str = ""  # future Michi marker (STREAM-REQ-005)


class FlashReaderPort(Protocol):
    def read_region(self, port: str, offset: int, size: int) -> bytes: ...


class InstallationDetectorPort(Protocol):
    def inspect(self, port: str) -> InstallationReport: ...
