"""Persistent Factory Recreate transactions (M14 + C0.4/C0.5/C0.7).

Crash-safety design (documented policy):

- **write-ahead record**: ``begin()`` persists the transaction FIRST and only
  then touches the roster; a crash can never leave a REPLACEMENT_PENDING
  entry without a persisted transaction to recover it.
- **idempotent reconciliation**: roster and transaction are separate sqlite
  connections over the same Home database, so the commit path reconciles
  forward if it crashed between the roster finalize and the state write
  (roster shows REPLACED/ACTIVE => transaction becomes COMMITTED).
- **FLASHING is never auto-resolved**: a crash while flashing leaves the
  hardware result unknown; recovery parks the transaction as
  RECOVERY_REQUIRED and only an explicit operator decision (success+failure
  evidence) resolves it. A crash during flashing is NOT assumed to be a
  clean failure.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from michi_ecosystem.domain.home import MichiHomeId

_SCHEMA = """
CREATE TABLE IF NOT EXISTS factory_recreate (
    tx_id TEXT PRIMARY KEY,
    home_id TEXT NOT NULL,
    old_device_id TEXT NOT NULL,
    candidate_michi_id TEXT NOT NULL,
    candidate_serial TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
"""


class RecreateState(StrEnum):
    CREATED = "created"
    REPLACEMENT_PENDING = "replacement_pending"
    FLASHING = "flashing"
    FLASH_VERIFIED = "flash_verified"
    COMMITTED = "committed"
    ABORTED = "aborted"
    FAILED = "failed"
    # Crash during FLASHING: hardware result unknown, needs explicit decision.
    RECOVERY_REQUIRED = "recovery_required"


TERMINAL_STATES = frozenset(
    {
        RecreateState.COMMITTED,
        RecreateState.ABORTED,
        RecreateState.FAILED,
    }
)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class RecreateTransaction:
    tx_id: str
    home_id: str
    old_device_id: str
    candidate_michi_id: str
    candidate_serial: str
    state: RecreateState
    detail: str = ""


class FactoryRecreateStore:
    def __init__(self, path: Path, home_id: MichiHomeId) -> None:
        self._home_id = home_id
        path.parent.mkdir(parents=True, exist_ok=True)
        # Shared Home database, accessed from the factory worker thread:
        # WAL + busy timeout; see roster.py for the threading rationale.
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def create(
        self,
        *,
        old_device_id: str,
        candidate_michi_id: str,
        candidate_serial: str,
    ) -> str:
        """Write-ahead: state starts at CREATED, before any roster effect."""
        tx_id = uuid.uuid4().hex
        now = _now_iso()
        with self._connection:
            self._connection.execute(
                "INSERT INTO factory_recreate VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    tx_id,
                    self._home_id.value,
                    old_device_id,
                    candidate_michi_id,
                    candidate_serial,
                    RecreateState.CREATED.value,
                    now,
                    now,
                    "",
                ),
            )
        return tx_id

    def get(self, tx_id: str) -> RecreateTransaction:
        row = self._connection.execute(
            "SELECT * FROM factory_recreate WHERE tx_id = ?", (tx_id,)
        ).fetchone()
        if row is None:
            raise KeyError(tx_id)
        return _from_row(row)

    def set_state(self, tx_id: str, state: RecreateState, detail: str = "") -> None:
        with self._connection:
            self._connection.execute(
                "UPDATE factory_recreate SET state = ?, detail = ?, "
                "updated_at = ? WHERE tx_id = ?",
                (state.value, detail, _now_iso(), tx_id),
            )

    def open_transactions(self) -> tuple[RecreateTransaction, ...]:
        rows = self._connection.execute(
            "SELECT * FROM factory_recreate WHERE state NOT IN (?, ?, ?)",
            tuple(state.value for state in TERMINAL_STATES),
        ).fetchall()
        return tuple(_from_row(row) for row in rows)


def _from_row(row: sqlite3.Row) -> RecreateTransaction:
    return RecreateTransaction(
        tx_id=str(row["tx_id"]),
        home_id=str(row["home_id"]),
        old_device_id=str(row["old_device_id"]),
        candidate_michi_id=str(row["candidate_michi_id"]),
        candidate_serial=str(row["candidate_serial"]),
        state=RecreateState(str(row["state"])),
        detail=str(row["detail"]),
    )
