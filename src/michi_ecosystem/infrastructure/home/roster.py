"""SQLite roster + revocation repositories (R4) — transactional Home state.

One database per Home (WAL, single-file transactions). Invariants:

- a revoked identity can never (re)become active;
- replacement commits atomically (old → REPLACED, new → ACTIVE);
- revocation status changes and its revocation record commit together.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from michi_ecosystem.domain.home import (
    DeviceRole,
    DeviceRosterEntry,
    DomainError,
    MembershipStatus,
    MichiHomeId,
    RevocationRecord,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS roster (
    device_michi_id TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    roles TEXT NOT NULL,
    status TEXT NOT NULL,
    membership_serial TEXT NOT NULL DEFAULT '',
    replacement_serial TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS revocations (
    home_id TEXT NOT NULL,
    device_michi_id TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    revoked_at TEXT NOT NULL DEFAULT '',
    replacement_serial TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (home_id, device_michi_id)
);
"""


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _roles_to_text(roles: tuple[DeviceRole, ...]) -> str:
    return ",".join(role.value for role in roles)


def _roles_from_text(text: str) -> tuple[DeviceRole, ...]:
    return tuple(DeviceRole(part) for part in text.split(",") if part)


def _entry_from_row(row: sqlite3.Row) -> DeviceRosterEntry:
    return DeviceRosterEntry(
        device_michi_id=str(row["device_michi_id"]),
        device_name=str(row["device_name"]),
        roles=_roles_from_text(str(row["roles"])),
        status=MembershipStatus(str(row["status"])),
        membership_serial=str(row["membership_serial"]),
    )


class _Base:
    def __init__(self, path: Path, home_id: MichiHomeId) -> None:
        self._home_id = home_id
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # The factory worker accesses Home state off the GUI thread; SQLite
        # serializes with WAL + a busy timeout and the coordinator runs one
        # operation at a time. See stream_factory_orchestrator (C0.3).
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


class SqliteDeviceRosterRepository(_Base):
    """Implements DeviceRosterRepositoryPort."""

    def is_revoked(self, device_michi_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM revocations WHERE home_id = ? AND device_michi_id = ?",
            (self._home_id.value, device_michi_id),
        ).fetchone()
        return row is not None

    def add(self, entry: DeviceRosterEntry) -> None:
        if self.is_revoked(entry.device_michi_id):
            raise DomainError("a revoked identity can never be re-added to the roster")
        with self._connection:
            self._connection.execute(
                "INSERT INTO roster VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry.device_michi_id,
                    entry.device_name,
                    _roles_to_text(entry.roles),
                    entry.status.value,
                    entry.membership_serial,
                    "",
                ),
            )

    def get(self, device_michi_id: str) -> DeviceRosterEntry | None:
        row = self._connection.execute(
            "SELECT * FROM roster WHERE device_michi_id = ?",
            (device_michi_id,),
        ).fetchone()
        return _entry_from_row(row) if row is not None else None

    def list_entries(self) -> tuple[DeviceRosterEntry, ...]:
        rows = self._connection.execute(
            "SELECT * FROM roster ORDER BY device_name"
        ).fetchall()
        return tuple(_entry_from_row(row) for row in rows)

    def mark_replacement_pending(
        self, device_michi_id: str, replacement_serial: str
    ) -> None:
        """Strict ACTIVE -> REPLACEMENT_PENDING (C0.6). Explicit errors."""
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE roster SET status = ?, replacement_serial = ? "
                "WHERE device_michi_id = ? AND status = ?",
                (
                    MembershipStatus.REPLACEMENT_PENDING.value,
                    replacement_serial,
                    device_michi_id,
                    MembershipStatus.ACTIVE.value,
                ),
            )
        if cursor.rowcount == 0:
            entry = self.get(device_michi_id)
            if entry is None:
                raise DomainError("replacement requires a roster entry (not found)")
            if self.is_revoked(device_michi_id):
                raise DomainError("a revoked device cannot enter replacement_pending")
            raise DomainError(
                f"replacement requires an ACTIVE device (status={entry.status.value})"
            )

    def replace(self, old_device_michi_id: str, new_entry: DeviceRosterEntry) -> None:
        if self.is_revoked(old_device_michi_id):
            raise DomainError("a revoked device cannot be replaced")
        if self.is_revoked(new_entry.device_michi_id):
            raise DomainError("a revoked identity cannot become active")
        with self._connection:  # atomic: both statements or none
            cursor = self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ?",
                (MembershipStatus.REPLACED.value, old_device_michi_id),
            )
            if cursor.rowcount == 0:
                raise DomainError("old device not found in roster")
            self._connection.execute(
                "INSERT INTO roster VALUES (?, ?, ?, ?, ?, ?)",
                (
                    new_entry.device_michi_id,
                    new_entry.device_name,
                    _roles_to_text(new_entry.roles),
                    MembershipStatus.ACTIVE.value,
                    new_entry.membership_serial,
                    "",
                ),
            )

    def revoke(self, device_michi_id: str, reason: str = "") -> None:
        with self._connection:  # status + record commit together
            self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ?",
                (MembershipStatus.REVOKED.value, device_michi_id),
            )
            self._connection.execute(
                "INSERT OR REPLACE INTO revocations VALUES (?, ?, ?, ?, ?)",
                (
                    self._home_id.value,
                    device_michi_id,
                    reason,
                    _now_iso(),
                    "",
                ),
            )

    def activate(self, device_michi_id: str) -> None:
        """PENDING -> ACTIVE, never for revoked identities."""
        if self.is_revoked(device_michi_id):
            raise DomainError("a revoked identity can never become active")
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ? AND status = ?",
                (
                    MembershipStatus.ACTIVE.value,
                    device_michi_id,
                    MembershipStatus.PENDING.value,
                ),
            )
        if cursor.rowcount == 0:
            raise DomainError("device is not pending activation")

    def abort_pending(self, device_michi_id: str) -> None:
        """PENDING -> ABORTED (idempotent); refuses active enrollments.

        Aborted entries are kept for audit and can never become active.
        """
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ? AND status = ?",
                (
                    MembershipStatus.ABORTED.value,
                    device_michi_id,
                    MembershipStatus.PENDING.value,
                ),
            )
        if cursor.rowcount > 0:
            return
        entry = self.get(device_michi_id)
        if entry is None or entry.status in (
            MembershipStatus.ABORTED,
            MembershipStatus.REVOKED,
        ):
            return  # nothing to resolve / already resolved
        if entry.status is MembershipStatus.ACTIVE:
            raise DomainError(
                "an active enrollment cannot be aborted; revoke it explicitly"
            )
        raise DomainError(f"cannot abort enrollment from status={entry.status.value}")

    def rollback_replacement(self, device_michi_id: str) -> None:
        """REPLACEMENT_PENDING -> ACTIVE (abort a recreate transaction)."""
        with self._connection:
            self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ? AND status = ?",
                (
                    MembershipStatus.ACTIVE.value,
                    device_michi_id,
                    MembershipStatus.REPLACEMENT_PENDING.value,
                ),
            )

    def finalize_replacement(
        self, old_device_michi_id: str, new_device_michi_id: str
    ) -> None:
        """Commit a recreate: old -> REPLACED, candidate -> ACTIVE atomically."""
        if self.is_revoked(new_device_michi_id):
            raise DomainError("a revoked identity can never become active")
        with self._connection:
            old_cursor = self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ? AND status = ?",
                (
                    MembershipStatus.REPLACED.value,
                    old_device_michi_id,
                    MembershipStatus.REPLACEMENT_PENDING.value,
                ),
            )
            if old_cursor.rowcount == 0:
                raise DomainError("old device is not in replacement_pending")
            new_cursor = self._connection.execute(
                "UPDATE roster SET status = ? WHERE device_michi_id = ? AND status = ?",
                (
                    MembershipStatus.ACTIVE.value,
                    new_device_michi_id,
                    MembershipStatus.PENDING.value,
                ),
            )
            if new_cursor.rowcount == 0:
                raise DomainError("candidate is not pending activation")

    def replace_all(self, entries: tuple[DeviceRosterEntry, ...]) -> None:
        """Transactional import (R5 restore)."""
        with self._connection:
            self._connection.execute("DELETE FROM roster")
            for entry in entries:
                self._connection.execute(
                    "INSERT INTO roster VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entry.device_michi_id,
                        entry.device_name,
                        _roles_to_text(entry.roles),
                        entry.status.value,
                        entry.membership_serial,
                        "",
                    ),
                )


class SqliteRevocationRepository(_Base):
    """Implements RevocationRepositoryPort (same database file)."""

    def is_revoked(self, home_id: MichiHomeId, device_michi_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM revocations WHERE home_id = ? AND device_michi_id = ?",
            (home_id.value, device_michi_id),
        ).fetchone()
        return row is not None

    def record(self, record: RevocationRecord) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO revocations VALUES (?, ?, ?, ?, ?)",
                (
                    record.home_id.value,
                    record.device_michi_id,
                    record.reason,
                    record.revoked_at or _now_iso(),
                    record.replacement_serial,
                ),
            )

    def list_records(self) -> tuple[RevocationRecord, ...]:
        rows = self._connection.execute(
            "SELECT * FROM revocations ORDER BY revoked_at"
        ).fetchall()
        return tuple(
            RevocationRecord(
                home_id=MichiHomeId(str(row["home_id"])),
                device_michi_id=str(row["device_michi_id"]),
                reason=str(row["reason"]),
                revoked_at=str(row["revoked_at"]),
                replacement_serial=str(row["replacement_serial"]),
            )
            for row in rows
        )

    def replace_all(self, records: tuple[RevocationRecord, ...]) -> None:
        """Transactional import (R5 restore)."""
        with self._connection:
            self._connection.execute("DELETE FROM revocations")
            for record in records:
                self._connection.execute(
                    "INSERT INTO revocations VALUES (?, ?, ?, ?, ?)",
                    (
                        record.home_id.value,
                        record.device_michi_id,
                        record.reason,
                        record.revoked_at,
                        record.replacement_serial,
                    ),
                )
