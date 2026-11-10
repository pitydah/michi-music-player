"""Discovery domain: presence records, mDNS hints and registry states.

Presence is never trust (master plan §19). ``DiscoveredNode`` couples the
functional announce projection (``NodePresence``) with the E2 verification
verdict; ``MdnsHint`` is the coarse TXT minimum set and never carries trust.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi_ecosystem.domain.nodes import NodePresence
from michi_ecosystem.domain.trust import AnnounceVerification, TrustLevel


@dataclass(frozen=True)
class DiscoveredNode:
    presence: NodePresence
    verification: AnnounceVerification
    last_seen_ms: int
    source_host: str | None = None

    @property
    def identity_verified(self) -> bool:
        """Cryptographic identity only — never paired trust (see TrustState)."""
        return self.verification.level is TrustLevel.VERIFIED


@dataclass(frozen=True)
class MdnsHint:
    """Coarse mDNS TXT hint (minimum set; never trust material)."""

    device_id: str
    service: str
    api_version: str
    roles: tuple[str, ...] = ()
    auth_strategy: str = ""
    michi_id: str = ""
