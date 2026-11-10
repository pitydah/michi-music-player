"""Home ports (R1) — interfaces only, wire-neutral.

Implementations arrive with R2 (keystore/authority) and later; the future
Michi Link v3 adapter plugs in behind ``HomeContractPort`` once the contract
is frozen (alpha.3 is work in progress; no schema is imported here).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from michi_ecosystem.domain.home import (
    DeviceRole,
    DeviceRosterEntry,
    HomeBackupMetadata,
    HomeMembership,
    MichiHomeId,
    MichiHomeProfile,
    RevocationRecord,
)


class HomeRepositoryPort(Protocol):
    def load_profile(self) -> MichiHomeProfile | None: ...

    def save_profile(self, profile: MichiHomeProfile) -> None: ...

    def delete_profile(self) -> None: ...


class HomeKeyStorePort(Protocol):
    """Encrypted-envelope storage (content is opaque to this interface)."""

    def exists(self) -> bool: ...

    def load_envelope(self) -> bytes | None: ...

    def save_envelope(self, envelope: bytes) -> None: ...

    def delete_envelope(self) -> None: ...


class MembershipIssuerPort(Protocol):
    def issue(
        self,
        *,
        home: MichiHomeProfile,
        device_michi_id: str,
        device_public_key: str,
        roles: tuple[DeviceRole, ...],
    ) -> HomeMembership: ...


class MembershipVerifierPort(Protocol):
    def verify(self, membership: HomeMembership, *, home: MichiHomeProfile) -> bool: ...


class DeviceRosterRepositoryPort(Protocol):
    def add(self, entry: DeviceRosterEntry) -> None: ...

    def get(self, device_michi_id: str) -> DeviceRosterEntry | None: ...

    def list_entries(self) -> tuple[DeviceRosterEntry, ...]: ...

    def mark_replacement_pending(
        self, device_michi_id: str, replacement_serial: str
    ) -> None: ...

    def replace(
        self, old_device_michi_id: str, new_entry: DeviceRosterEntry
    ) -> None: ...

    def revoke(self, device_michi_id: str, reason: str = "") -> None: ...

    def is_revoked(self, device_michi_id: str) -> bool: ...

    def replace_all(self, entries: tuple[DeviceRosterEntry, ...]) -> None: ...

    def activate(self, device_michi_id: str) -> None: ...

    def abort_pending(self, device_michi_id: str) -> None:
        """PENDING -> ABORTED (idempotent). Active/revoked entries are refused/no-op."""
        ...

    def rollback_replacement(self, device_michi_id: str) -> None: ...

    def finalize_replacement(
        self, old_device_michi_id: str, new_device_michi_id: str
    ) -> None: ...


class RevocationRepositoryPort(Protocol):
    def record(self, record: RevocationRecord) -> None: ...

    def is_revoked(self, home_id: MichiHomeId, device_michi_id: str) -> bool: ...

    def list_records(self) -> tuple[RevocationRecord, ...]: ...

    def replace_all(self, records: tuple[RevocationRecord, ...]) -> None: ...


class HomeBackupPort(Protocol):
    def create_backup(self, path: Path, password: str) -> HomeBackupMetadata: ...

    def inspect_backup(self, path: Path) -> HomeBackupMetadata: ...

    def verify_backup(self, path: Path, password: str) -> bool: ...

    def restore_backup(self, path: Path, password: str) -> None: ...


class HomeContractPort(Protocol):
    """Seam for the future Michi Link v3 Home/membership adapter."""

    def contract_version(self) -> str: ...

    def encode_membership(self, membership: HomeMembership) -> bytes: ...

    def decode_membership(
        self, payload: bytes, *, home: MichiHomeProfile
    ) -> HomeMembership: ...
