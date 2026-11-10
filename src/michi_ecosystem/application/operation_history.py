"""Bounded safe audit trail; event codes only, no raw adapter or user content."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

_ALLOWED = re.compile(
    r"^(SPACE_(CREATED|RENAMED|REMOVED|ASSIGNED|UNASSIGNED)|DIAGNOSTICS_VIEWED|DEVICE_DETAIL_OPENED|SUPPORT_EXPORTED)$"
)


@dataclass(frozen=True)
class OperationEvent:
    timestamp: int
    code: str

    def projection(self) -> dict[str, object]:
        return {"timestamp": self.timestamp, "code": self.code}


class OperationHistory:
    def __init__(
        self, *, limit: int = 100, clock=None, state_dir: Path | None = None
    ) -> None:
        self._limit = max(1, min(int(limit), 500))
        self._events: deque[OperationEvent] = deque(maxlen=self._limit)
        self._clock = clock or time.time
        self._lock = threading.RLock()
        self._db: sqlite3.Connection | None = None
        if state_dir is not None:
            root = Path(state_dir)
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            root.chmod(0o700)
            db_path = root / "events.db"
            if db_path.is_symlink():
                raise ValueError("History database must not be a symlink")
            self._db = sqlite3.connect(db_path, check_same_thread=False)
            db_path.chmod(0o600)
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, "
                "timestamp INTEGER NOT NULL, code TEXT NOT NULL)"
            )
            self._db.commit()
            rows = self._db.execute(
                "SELECT timestamp,code FROM events ORDER BY id DESC LIMIT ?",
                (self._limit,),
            ).fetchall()
            for ts, code in reversed(rows):
                if _ALLOWED.fullmatch(code):
                    self._events.append(OperationEvent(ts, code))

    def record(self, code: str) -> None:
        if not isinstance(code, str) or not _ALLOWED.fullmatch(code):
            raise ValueError("Unknown operation event code")
        with self._lock:
            event = OperationEvent(int(self._clock()), code)
            if self._db is not None:
                with self._db:
                    self._db.execute(
                        "INSERT INTO events(timestamp,code) VALUES (?,?)",
                        (event.timestamp, event.code),
                    )
                    self._db.execute(
                        "DELETE FROM events WHERE id NOT IN "
                        "(SELECT id FROM events ORDER BY id DESC LIMIT ?)",
                        (self._limit,),
                    )
            self._events.append(event)

    def list(self) -> tuple[OperationEvent, ...]:
        with self._lock:
            return tuple(reversed(self._events))

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None

    def export_support_bundle(
        self, destination: Path, *, doctor: dict[str, object]
    ) -> None:
        """Host-selected destination only. No raw logs/identifiers/credentials."""
        safe = {
            "schema": "michi-ecosystem-support-v1",
            "issues": sorted(
                str(x.get("code", "")).split(":", 1)[0]
                for x in doctor.get("issues", ())
                if isinstance(x, dict) and str(x.get("code", "")).startswith("DOCTOR-")
            ),
            "events": [x.projection() for x in self.list()],
        }
        path = Path(destination)
        if path.is_symlink() or not path.parent.is_dir():
            raise ValueError(
                "Export destination must be an existing directory and not a symlink"
            )
        # Require a path chosen by the host; never overwrite files or follow symlinks.
        fd = os.open(
            path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(safe, stream, ensure_ascii=False, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
