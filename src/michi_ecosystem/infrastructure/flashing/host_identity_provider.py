"""Host-generated device identity provider (provisional, per ADR R3).

Keeps private material in memory only; final delivery mechanism (USB
provisioning vs device-generated keys) is decided by the ADR and firmware
contract (STREAM-REQ-007).
"""

from __future__ import annotations

import base64

import blake3
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from michi_ecosystem.ports.device_identity import CandidateDeviceIdentity


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class HostGeneratedDeviceIdentityProvider:
    # ADR target is device-generated identity (Option B, STREAM-REQ-007):
    # host-generated private material is dev/test/provisional ONLY and must
    # never be promoted to product design by accident.
    product_ready = False

    def __init__(self) -> None:
        self._candidate: CandidateDeviceIdentity | None = None

    def create_candidate(self) -> CandidateDeviceIdentity:
        private = Ed25519PrivateKey.generate()
        private_raw = private.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
        public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        candidate = CandidateDeviceIdentity(
            michi_id=_b64url(blake3.blake3(public_raw).digest()),
            public_key=_b64url(public_raw),
            private_material=private_raw,
        )
        self._candidate = candidate
        return candidate

    def finalize(self) -> None:
        self._candidate = None  # delivery performed by the caller

    def abort(self) -> None:
        self._candidate = None
