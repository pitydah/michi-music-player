"""Michi Home domain (R1) — wire-neutral foundation.

Strictly separated identities:

- ``michi_id``: per-device cryptographic identity (opaque here);
- ``michi_home_id``: shared identifier of the Home — public, never secret,
  never derived from username or password.

No serialization, no signatures and no Michi Link schemas live here: the
future v3 adapter sits behind ``ports.home.HomeContractPort``.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_SERIAL_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class DomainError(ValueError):
    """A Home domain invariant was violated."""


def _require_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise DomainError(f"{label} must match 8-64 [A-Za-z0-9_-]")
    return value


class DeviceRole(StrEnum):
    """Canonical ecosystem roles (bounded vocabulary)."""

    DESKTOP_PLAYER = "desktop_player"
    LIBRARY_MASTER = "library_master"
    SYNC_HOST = "sync_host"
    MUSIC_SERVER = "music_server"
    LIBRARY_HOST = "library_host"
    PLAYBACK_HOST = "playback_host"
    MOBILE_PLAYER = "mobile_player"
    REMOTE_CONTROLLER = "remote_controller"
    SYNC_CLIENT = "sync_client"
    AUDIO_RECEIVER = "audio_receiver"


class MembershipStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    REPLACEMENT_PENDING = "replacement_pending"
    REPLACED = "replaced"
    # Enrollment aborted before device confirmation: kept for audit,
    # never usable (a PENDING entry must never linger as a ghost).
    ABORTED = "aborted"
    EXPIRED = "expired"


@dataclass(frozen=True)
class MichiHomeId:
    """Public Home identifier (never a secret, never password-derived)."""

    value: str

    def __post_init__(self) -> None:
        _require_id(self.value, "michi_home_id")

    @classmethod
    def generate(cls) -> MichiHomeId:
        return cls(uuid.uuid4().hex)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class HomeRootPublicIdentity:
    public_key: str
    key_scheme: str = "ed25519"

    def __post_init__(self) -> None:
        if not isinstance(self.public_key, str) or not self.public_key:
            raise DomainError("home root public key must not be empty")


@dataclass(frozen=True)
class MichiHomeProfile:
    home_id: MichiHomeId
    name: str
    root: HomeRootPublicIdentity
    created_at: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise DomainError("home name must not be empty")


@dataclass(frozen=True)
class MembershipSerial:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _SERIAL_RE.match(self.value):
            raise DomainError("serial must match 8-64 [A-Za-z0-9-]")

    @classmethod
    def generate(cls) -> MembershipSerial:
        return cls(uuid.uuid4().hex)


@dataclass(frozen=True)
class HomeMembership:
    home_id: MichiHomeId
    device_michi_id: str
    device_public_key: str
    serial: MembershipSerial
    roles: tuple[DeviceRole, ...]
    status: MembershipStatus = MembershipStatus.PENDING
    issued_at: str = ""
    signature: str = ""

    def __post_init__(self) -> None:
        _require_id(self.device_michi_id, "device_michi_id")
        if not isinstance(self.device_public_key, str) or not self.device_public_key:
            raise DomainError("device public key must not be empty")
        if not self.roles:
            raise DomainError("membership must declare at least one role")
        if len(set(self.roles)) != len(self.roles):
            raise DomainError("membership roles must be unique")
        if self.device_michi_id == self.home_id.value:
            raise DomainError("device identity must be distinct from the Home identity")

    def belongs_to(self, home_id: MichiHomeId) -> bool:
        return self.home_id == home_id

    def is_active(self) -> bool:
        return self.status is MembershipStatus.ACTIVE


@dataclass(frozen=True)
class DeviceRosterEntry:
    device_michi_id: str
    device_name: str
    roles: tuple[DeviceRole, ...]
    status: MembershipStatus = MembershipStatus.PENDING
    membership_serial: str = ""

    def __post_init__(self) -> None:
        _require_id(self.device_michi_id, "device_michi_id")
        if not isinstance(self.device_name, str) or not self.device_name.strip():
            raise DomainError("device name must not be empty")
        if not self.roles:
            raise DomainError("roster entry must declare at least one role")


@dataclass(frozen=True)
class RevocationRecord:
    home_id: MichiHomeId
    device_michi_id: str
    reason: str = ""
    revoked_at: str = ""
    replacement_serial: str = ""

    def __post_init__(self) -> None:
        _require_id(self.device_michi_id, "device_michi_id")


@dataclass(frozen=True)
class HomeBackupMetadata:
    format_version: int
    home_id: MichiHomeId
    created_at: str = ""
    kdf: str = ""
    includes_roster: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.format_version, int) or self.format_version < 1:
            raise DomainError("backup format_version must be >= 1")


def validate_membership_against_home(
    membership: HomeMembership, home: MichiHomeProfile
) -> None:
    """Fail closed when the membership does not belong to this Home."""
    if not membership.belongs_to(home.home_id):
        raise DomainError("membership does not belong to this Home")


def effective_membership_status(
    membership: HomeMembership, revocations: tuple[RevocationRecord, ...]
) -> MembershipStatus:
    """A revoked device is never reported as active.

    Revocation wins over any stored status, including REPLACEMENT_PENDING.
    """
    for record in revocations:
        if (
            record.home_id == membership.home_id
            and record.device_michi_id == membership.device_michi_id
        ):
            return MembershipStatus.REVOKED
    return membership.status
