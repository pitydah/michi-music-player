"""SQLite persistence for the local human account (E11.5-A).

Only an Argon2id PHC verifier is persisted. The PHC string contains the salt
and KDF parameters required for verification; plaintext passwords and session
state never reach this database.

The QML bridge performs expensive Argon2 work on worker threads. SQLite access
is therefore serialized here with an RLock and a connection explicitly allowed
to cross threads. The repository is still single-process and all transactions
remain atomic.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
from pathlib import Path

from michi_ecosystem.domain.account import LocalAccount, LocalAccountRole

ACCOUNT_DB = "account.db"


def default_account_dir(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    data_home = values.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home) / "michi" / "account"
    return Path.home() / ".local" / "share" / "michi" / "account"


class SqliteLocalAccountRepository:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with contextlib.suppress(OSError):
            self._root.chmod(0o700)
        self._db_path = self._root / ACCOUNT_DB
        self._lock = threading.RLock()
        self._closed = False
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS local_account (
                    account_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_verifier TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    role TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS home_owner (
                    michi_home_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    FOREIGN KEY(account_id) REFERENCES local_account(account_id)
                        ON DELETE CASCADE
                );
                """
            )
            self._conn.commit()
        with contextlib.suppress(OSError):
            self._db_path.chmod(0o600)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("local account repository is closed")

    def count_accounts(self) -> int:
        with self._lock:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT COUNT(*) AS count FROM local_account"
            ).fetchone()
            return int(row["count"] if row is not None else 0)

    def first_account(self) -> LocalAccount | None:
        with self._lock:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT * FROM local_account ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            return self._account(row)

    def create(self, account: LocalAccount) -> None:
        with self._lock, self._conn:
            self._ensure_open()
            cursor = self._conn.execute(
                """
                INSERT INTO local_account (
                    account_id, username, display_name, password_verifier,
                    created_at, updated_at, role
                )
                SELECT ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (SELECT 1 FROM local_account LIMIT 1)
                """,
                (
                    account.account_id,
                    account.username,
                    account.display_name,
                    account.password_verifier,
                    account.created_at,
                    account.updated_at,
                    account.role.value,
                ),
            )
            if cursor.rowcount != 1:
                # Invariant enforced in the persistence transaction, not only
                # by the service's racy count-then-insert preflight.
                raise sqlite3.IntegrityError("one OWNER per installation")

    @staticmethod
    def _account(row: sqlite3.Row | None) -> LocalAccount | None:
        if row is None:
            return None
        return LocalAccount(
            account_id=str(row["account_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            password_verifier=str(row["password_verifier"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            role=LocalAccountRole(str(row["role"])),
        )

    def get_by_id(self, account_id: str) -> LocalAccount | None:
        with self._lock:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT * FROM local_account WHERE account_id = ?", (account_id,)
            ).fetchone()
            return self._account(row)

    def get_by_username(self, username: str) -> LocalAccount | None:
        with self._lock:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT * FROM local_account WHERE username = ? COLLATE NOCASE",
                (username,),
            ).fetchone()
            return self._account(row)

    def update_verifier(
        self, account_id: str, password_verifier: str, updated_at: str
    ) -> None:
        with self._lock, self._conn:
            self._ensure_open()
            cursor = self._conn.execute(
                """
                UPDATE local_account
                SET password_verifier = ?, updated_at = ?
                WHERE account_id = ?
                """,
                (password_verifier, updated_at, account_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(account_id)

    def bind_home_owner(self, account_id: str, michi_home_id: str) -> None:
        with self._lock, self._conn:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT 1 FROM local_account WHERE account_id = ?", (account_id,)
            ).fetchone()
            if row is None:
                raise KeyError(account_id)
            # One OWNER account owns one current Michi Home. Rebinding is an
            # explicit replacement, never an accumulation of stale ownership.
            self._conn.execute(
                "DELETE FROM home_owner WHERE account_id = ? AND michi_home_id <> ?",
                (account_id, michi_home_id),
            )
            self._conn.execute(
                """
                INSERT INTO home_owner (michi_home_id, account_id)
                VALUES (?, ?)
                ON CONFLICT(michi_home_id) DO UPDATE SET
                    account_id = excluded.account_id
                """,
                (michi_home_id, account_id),
            )

    def owner_for_home(self, michi_home_id: str) -> str | None:
        with self._lock:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT account_id FROM home_owner WHERE michi_home_id = ?",
                (michi_home_id,),
            ).fetchone()
            return str(row["account_id"]) if row is not None else None

    def home_for_owner(self, account_id: str) -> str | None:
        with self._lock:
            self._ensure_open()
            row = self._conn.execute(
                "SELECT michi_home_id FROM home_owner WHERE account_id = ? LIMIT 1",
                (account_id,),
            ).fetchone()
            return str(row["michi_home_id"]) if row is not None else None

    @property
    def db_path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._conn.close()
            self._closed = True
