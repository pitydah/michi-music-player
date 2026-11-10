"""Trust and pairing models grounded on the receiver-v1-lite contract.

Trust levels and the announce verification result follow ``docs/DISCOVERY.md``
(Verified / Untrusted / Invalid). Pairing strategies mirror the canonical
``auth_strategy`` enum of ``pair-start.schema.json`` and the pairing flow of
``docs/PAIRING.md``; the capability view is the master plan §149 contract
(UI reacts to requirements — never hardcoded to one firmware generation).

Phase: E2 (pairing abstraction + trust projection).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class TrustLevel(StrEnum):
    VERIFIED = "verified"
    UNTRUSTED = "untrusted"
    INVALID = "invalid"


@dataclass(frozen=True)
class AnnounceVerification:
    """Outcome of the signed-announce pipeline."""

    level: TrustLevel
    device_id: str = ""
    michi_id: str | None = None
    reason: str = ""


class PairingAuthStrategy(StrEnum):
    """Canonical pairing strategies (pair-start.schema.json)."""

    PLAYER_PASSWORD = "PLAYER_PASSWORD"
    SERVER_CODE = "SERVER_CODE"
    ED25519_CHALLENGE = "ED25519_CHALLENGE"
    RECEIVER_BUTTON = "RECEIVER_BUTTON"
    LEGACY = "LEGACY"


class PairingSessionStatus(StrEnum):
    """Canonical pairing session status (pair-status.schema.json)."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    LOCKED = "locked"


@dataclass(frozen=True)
class PairingRequirements:
    """Capability-driven pairing UX contract (master plan §149.1)."""

    requires_physical_authorization: bool = False
    requires_pin_confirmation: bool = False
    requires_local_display_confirmation: bool = False
    supports_app_initiated_pairing: bool = False
    supports_recovery: bool = False
    legacy: bool = False


_REQUIREMENTS: dict[PairingAuthStrategy, PairingRequirements] = {
    PairingAuthStrategy.PLAYER_PASSWORD: PairingRequirements(
        requires_pin_confirmation=True
    ),
    PairingAuthStrategy.SERVER_CODE: PairingRequirements(
        requires_pin_confirmation=True
    ),
    PairingAuthStrategy.ED25519_CHALLENGE: PairingRequirements(
        supports_app_initiated_pairing=True
    ),
    PairingAuthStrategy.RECEIVER_BUTTON: PairingRequirements(
        requires_physical_authorization=True
    ),
    PairingAuthStrategy.LEGACY: PairingRequirements(legacy=True),
}


def requirements_for(strategy: str) -> PairingRequirements:
    """Map a canonical auth strategy to its UX requirements (fail closed)."""
    try:
        parsed = PairingAuthStrategy(strategy)
    except ValueError as exc:
        raise ValueError(f"unknown pairing auth strategy: {strategy!r}") from exc
    return _REQUIREMENTS[parsed]


@dataclass(frozen=True)
class PairingStart:
    """Live pairing transaction opened by the Micro Server (receivers/pair/start)."""

    pairing_id: str
    receiver_base_url: str
    receiver_pair_session_id: str
    expires_at: str


@dataclass(frozen=True)
class PairingConfirmation:
    """Confirmation result; ``status`` values follow the upstream endpoint."""

    status: str
    receiver_id: str = ""
    payload: Mapping[str, object] = field(default_factory=dict)


class TrustState(StrEnum):
    """Authorization state — strictly separate from cryptographic identity.

    A valid signed announce proves *identity* (``AnnounceVerification``); it
    never proves trust. Trust is granted only through the pairing flow.
    """

    UNPAIRED = "unpaired"
    PAIRING = "pairing"
    TRUSTED = "trusted"
    REVOKED = "revoked"
    RECOVERY_REQUIRED = "recovery_required"


def trust_state_for(paired: bool, verified: bool) -> TrustState:
    """Map receiver pairing evidence to an explicit trust state (fail closed)."""
    if not paired:
        return TrustState.UNPAIRED
    if not verified:
        return TrustState.RECOVERY_REQUIRED
    return TrustState.TRUSTED


@dataclass(frozen=True)
class TargetAuthorization:
    """Explicit authorization evidence required before remote control.

    Remote playback is allowed ONLY with verified identity AND trusted pairing
    (master plan §156; a bare signed announce is never sufficient).
    """

    target_id: str
    identity_verified: bool
    trust_state: TrustState

    @property
    def allowed(self) -> bool:
        return self.identity_verified and self.trust_state is TrustState.TRUSTED
