"""SQLite spaces storage, scoped by Home and separate from authority databases."""

from __future__ import annotations

import sqlite3
import threading
import unicodedata
from pathlib import Path

from michi_ecosystem.application.spaces_service import Space, SpaceError


def _name_key(name: str) -> str:
    """Use a Unicode-aware comparison key for a human-facing Space name."""
    return unicodedata.normalize("NFKC", name).casefold()


class SqliteSpacesStore:
    def __init__(self, root: Path) -> None:
        root = Path(root)
        # Database paths are host-owned private state, never a symlink to an
        # unrelated path. This prevents accidental redirection of Home data.
        if root.is_symlink():
            raise ValueError("Spaces state directory must not be a symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        database = root / "spaces.db"
        if database.is_symlink() or (database.exists() and not database.is_file()):
            raise ValueError("Spaces database must be a regular file")
        if database.exists():
            database.chmod(0o600)
        self._connection = sqlite3.connect(database, check_same_thread=False)
        database.chmod(0o600)
        self._lock = threading.RLock()
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS spaces (
                home_id TEXT NOT NULL,
                id TEXT NOT NULL,
                name TEXT NOT NULL COLLATE NOCASE,
                PRIMARY KEY (home_id, id), UNIQUE (home_id, name)
            );
            CREATE TABLE IF NOT EXISTS assignments (
                home_id TEXT NOT NULL, space_id TEXT NOT NULL, device_id TEXT NOT NULL,
                PRIMARY KEY (home_id, device_id),
                FOREIGN KEY (home_id, space_id) REFERENCES spaces(home_id, id)
                    ON DELETE CASCADE
            );
            """)

    def list(self, home_id: str) -> tuple[Space, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id,name FROM spaces WHERE home_id=? "
                "ORDER BY name COLLATE NOCASE",
                (home_id,),
            ).fetchall()
            return tuple(
                Space(
                    r[0],
                    home_id,
                    r[1],
                    tuple(
                        x[0]
                        for x in self._connection.execute(
                            "SELECT device_id FROM assignments "
                            "WHERE home_id=? AND space_id=? ORDER BY device_id",
                            (home_id, r[0]),
                        )
                    ),
                )
                for r in rows
            )

    def add(self, space: Space) -> None:
        with self._lock, self._connection:
            # BEGIN IMMEDIATE serializes writers across independent SQLite
            # connections/processes. A service-level SELECT count alone races.
            self._connection.execute("BEGIN IMMEDIATE")
            count = self._connection.execute(
                "SELECT COUNT(*) FROM spaces WHERE home_id=?", (space.home_id,)
            ).fetchone()[0]
            if count >= 64:
                raise SpaceError("SPACE_LIMIT")
            # SQLite NOCASE only folds ASCII. With BEGIN IMMEDIATE, this check
            # serializes competing writers from other processes as well.
            existing = self._connection.execute(
                "SELECT name FROM spaces WHERE home_id=?", (space.home_id,)
            ).fetchall()
            if any(_name_key(name) == _name_key(space.name) for (name,) in existing):
                raise SpaceError("DUPLICATE_NAME")
            try:
                self._connection.execute(
                    "INSERT INTO spaces(home_id,id,name) VALUES (?,?,?)",
                    (space.home_id, space.space_id, space.name),
                )
            except sqlite3.IntegrityError as exc:
                raise SpaceError("DUPLICATE_NAME") from exc

    def rename(self, home_id: str, space_id: str, name: str) -> bool:
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            current = self._connection.execute(
                "SELECT id,name FROM spaces WHERE home_id=?", (home_id,)
            ).fetchall()
            if not any(identifier == space_id for identifier, _ in current):
                return False
            if any(
                identifier != space_id and _name_key(old_name) == _name_key(name)
                for identifier, old_name in current
            ):
                raise SpaceError("DUPLICATE_NAME")
            try:
                return (
                    self._connection.execute(
                        "UPDATE spaces SET name=? WHERE home_id=? AND id=?",
                        (name, home_id, space_id),
                    ).rowcount
                    > 0
                )
            except sqlite3.IntegrityError as exc:
                raise SpaceError("DUPLICATE_NAME") from exc

    def remove(self, home_id: str, space_id: str) -> bool:
        # One atomic SQL statement enforces emptiness even with *other*
        # connections/processes. UI-only validation and SELECT-then-DELETE are
        # insufficient under concurrent writers.
        with self._lock, self._connection:
            deleted = self._connection.execute(
                "DELETE FROM spaces WHERE home_id=? AND id=? "
                "AND NOT EXISTS (SELECT 1 FROM assignments "
                "WHERE home_id=? AND space_id=?)",
                (home_id, space_id, home_id, space_id),
            ).rowcount
            if deleted:
                return True
            if (
                self._connection.execute(
                    "SELECT 1 FROM spaces WHERE home_id=? AND id=?", (home_id, space_id)
                ).fetchone()
                is not None
            ):
                raise SpaceError("SPACE_NOT_EMPTY")
            return False

    def assign(self, home_id: str, space_id: str, device_id: str) -> bool:
        with self._lock, self._connection:
            found = self._connection.execute(
                "SELECT 1 FROM spaces WHERE home_id=? AND id=?", (home_id, space_id)
            ).fetchone()
            if not found:
                return False
            self._connection.execute(
                "INSERT INTO assignments(home_id,space_id,device_id) VALUES (?,?,?) "
                "ON CONFLICT(home_id,device_id) DO UPDATE "
                "SET space_id=excluded.space_id",
                (home_id, space_id, device_id),
            )
            return True

    def assignment_for(self, home_id: str, device_id: str) -> str | None:
        """Read the previously committed Space before moving a device."""
        with self._lock:
            row = self._connection.execute(
                "SELECT space_id FROM assignments WHERE home_id=? AND device_id=?",
                (home_id, device_id),
            ).fetchone()
            return row[0] if row is not None else None

    def rollback_move_if_current(
        self,
        home_id: str,
        device_id: str,
        target_space: str,
        previous_space: str | None,
    ) -> bool:
        """Undo only our own move; never clobber a newer concurrent reassignment.

        The revocation path deliberately passes ``None`` so no revoked device
        can regain an earlier Space association.
        """
        with self._lock, self._connection:
            if previous_space is None:
                changed = self._connection.execute(
                    "DELETE FROM assignments WHERE home_id=? "
                    "AND device_id=? AND space_id=?",
                    (home_id, device_id, target_space),
                )
                return changed.rowcount > 0
            try:
                changed = self._connection.execute(
                    "UPDATE assignments SET space_id=? "
                    "WHERE home_id=? AND device_id=? AND space_id=? "
                    "AND EXISTS (SELECT 1 FROM spaces WHERE home_id=? AND id=?)",
                    (
                        previous_space,
                        home_id,
                        device_id,
                        target_space,
                        home_id,
                        previous_space,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
            return changed.rowcount > 0

    def unassign(self, home_id: str, space_id: str, device_id: str) -> bool:
        with self._lock, self._connection:
            found = self._connection.execute(
                "SELECT 1 FROM spaces WHERE home_id=? AND id=?", (home_id, space_id)
            ).fetchone()
            if not found:
                return False
            self._connection.execute(
                "DELETE FROM assignments WHERE home_id=? "
                "AND space_id=? AND device_id=?",
                (home_id, space_id, device_id),
            )
            return True

    def close(self) -> None:
        with self._lock:
            self._connection.close()
