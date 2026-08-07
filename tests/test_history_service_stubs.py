"""History (debt D4): set_history_enabled/set_history_limit are REAL.

The setters persist state (QSettings keys ``history/enabled`` and
``history/limit``) and the service enforces it: recording is gated by the
enabled flag, fetch results are capped by the persisted limit, and old rows
are pruned when the limit shrinks. No nominal ``{"ok": True}`` without effect.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.history_query_service import HistoryQueryService
from core.settings_manager import SETTINGS

_HISTORY_ENABLED_KEY = "history/enabled"
_HISTORY_LIMIT_KEY = "history/limit"


@pytest.fixture(autouse=True)
def _clean_history_settings():
    yield
    SETTINGS.remove(_HISTORY_ENABLED_KEY)
    SETTINGS.remove(_HISTORY_LIMIT_KEY)


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE play_history (
            track_id TEXT NOT NULL,
            played_at REAL NOT NULL,
            device TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            albumartist TEXT
        )
    """)
    conn.commit()
    return conn


class _DbWrap:
    def __init__(self, conn):
        self.conn = conn


def _seed_history(conn, n: int, start: float = 1000.0) -> None:
    for i in range(n):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) "
            "VALUES (?, ?, ?)",
            (f"t{i}", start + i, "desktop"),
        )
    conn.commit()


class TestSetHistoryEnabled:
    def test_flag_persists_and_gates_recording(self) -> None:
        conn = _db()
        svc = HistoryQueryService(db=_DbWrap(conn))

        result = svc.set_history_enabled(False)
        assert result == {"ok": True, "enabled": False}

        recorded = svc.record_play("t1", device="desktop")
        assert recorded == {"ok": False, "error": "HISTORY_DISABLED"}
        assert svc.count_history() == 0

        assert svc.set_history_enabled(True) == {"ok": True, "enabled": True}
        assert svc.record_play("t1", device="desktop")["ok"] is True
        assert svc.count_history() == 1

    def test_flag_survives_service_restart(self) -> None:
        conn = _db()
        HistoryQueryService(db=_DbWrap(conn)).set_history_enabled(False)

        restarted = HistoryQueryService(db=_DbWrap(conn))
        assert restarted.record_play("t1") == {
            "ok": False, "error": "HISTORY_DISABLED",
        }

    def test_has_effect_after_re_enable(self) -> None:
        conn = _db()
        svc = HistoryQueryService(db=_DbWrap(conn))
        svc.set_history_enabled(False)
        svc.set_history_enabled(True)
        assert svc.record_play("t1")["ok"] is True
        assert svc.count_history() == 1


class TestSetHistoryLimit:
    def test_limit_persists_and_caps_fetch(self) -> None:
        conn = _db()
        _seed_history(conn, 10)
        svc = HistoryQueryService(db=_DbWrap(conn))

        result = svc.set_history_limit(3)
        assert result["ok"] is True
        assert result["limit"] == 3
        assert result["pruned"] == 7

        assert len(svc.fetch_history(offset=0, limit=100)) == 3
        assert len(svc.fetch_history(offset=0, limit=10)) == 3

    def test_limit_survives_service_restart(self) -> None:
        conn = _db()
        _seed_history(conn, 10)
        HistoryQueryService(db=_DbWrap(conn)).set_history_limit(4)

        restarted = HistoryQueryService(db=_DbWrap(conn))
        assert len(restarted.fetch_history(offset=0, limit=100)) == 4

    def test_limit_applied_on_record_play(self) -> None:
        conn = _db()
        _seed_history(conn, 2)
        svc = HistoryQueryService(db=_DbWrap(conn))
        assert svc.set_history_limit(2)["pruned"] == 0

        result = svc.record_play("t_new", device="desktop")
        assert result["ok"] is True
        assert result["pruned"] == 1
        assert svc.count_history() == 2

    def test_invalid_limits_rejected(self) -> None:
        conn = _db()
        svc = HistoryQueryService(db=_DbWrap(conn))
        assert svc.set_history_limit(-1) == {"ok": False, "error": "INVALID_LIMIT"}
        assert svc.set_history_limit("abc") == {"ok": False, "error": "INVALID_LIMIT"}

    def test_zero_limit_disables_cap_and_prune(self) -> None:
        conn = _db()
        _seed_history(conn, 5)
        svc = HistoryQueryService(db=_DbWrap(conn))
        assert svc.set_history_limit(0)["ok"] is True
        assert len(svc.fetch_history(offset=0, limit=100)) == 5
        assert svc.record_play("t_new")["ok"] is True
        assert svc.count_history() == 6


class TestNoNominalSuccess:
    def test_setters_are_not_nominal_without_db(self) -> None:
        svc = HistoryQueryService(db=None)
        enabled = svc.set_history_enabled(False)
        assert enabled["ok"] is True and enabled["enabled"] is False
        limit = svc.set_history_limit(5)
        assert limit["ok"] is True and limit["limit"] == 5 and limit["pruned"] == 0
        assert svc.record_play("t1") == {"ok": False, "error": "NO_DB"}
