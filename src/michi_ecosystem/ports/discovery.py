"""Discovery source port: raw announce observation (master plan §19).

Implementations own the sockets (UDP multicast / mDNS); the application
service owns verification, merging and trust. Poll-based and non-blocking so
orchestration can drive the cadence off the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RawAnnounce:
    payload: bytes
    source_host: str | None = None


class DiscoverySourcePort(Protocol):
    def start(self) -> None: ...

    def poll(self) -> tuple[RawAnnounce, ...]: ...

    def close(self) -> None: ...
