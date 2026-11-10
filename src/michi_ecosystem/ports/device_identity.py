"""Device identity provider boundary (R3).

Factory never generates keys directly: candidates come through this port so
the final architecture (host-generated vs on-device, see ADR) can change
without touching Factory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class CandidateDeviceIdentity:
    michi_id: str
    public_key: str
    scheme: str = "ed25519-blake3-v1"
    private_material: bytes | None = field(default=None, repr=False)


class DeviceIdentityProviderPort(Protocol):
    def create_candidate(self) -> CandidateDeviceIdentity: ...

    def finalize(self) -> None:
        """The candidate is now committed (e.g. enrollment issued)."""
        ...

    def abort(self) -> None:
        """Discard candidate material (never leak into logs)."""
        ...
