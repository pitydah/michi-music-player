"""Post-flash device confirmation (I3): cryptographic proof, not a boolean.

A device becomes eligible for Home roster activation only when the host can
show ALL of the following, bound to the flashed candidate identity:

- the same ``michi_id`` observed after the flash (never IP/MAC/hostname/SSID);
- a public key whose BLAKE3 derivation equals that ``michi_id``;
- an Ed25519 signature over a fresh challenge with that key;
- the flash reference (manifest digest / provisioning fingerprint) it belongs to.

The object is evidence only: it carries no private key and never grants trust
by itself.
"""

from __future__ import annotations

from dataclasses import dataclass


class DeviceConfirmationError(ValueError):
    """A confirmation cannot prove possession of the prepared identity."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class DeviceConfirmation:
    device_michi_id: str
    public_key: str
    challenge: str
    challenge_signature: str
    observed_michi_id: str
    flash_reference: str
    observed_at_ms: int | None = None
