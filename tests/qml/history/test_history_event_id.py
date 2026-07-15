"""Test HistoryQueryService: event ID for mutations, NOT track ID only."""
import pytest
import sqlite3
import time

from core.history_query_service import HistoryQueryService


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT NOT NULL,
            played_at REAL NOT NULL,
            device TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            deleted_at TEXT, albumartist TEXT
        )
    """)
    now = time.time()
    for i in range(5):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "local")
        )
    for i in range(5):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, duration) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i}", f"Album {i}", f"key_{i}", 200 + i)
        )
    conn.commit()
    return conn


class DbWrap:
    def __init__(self, conn):
        self.conn = conn


@pytest.fixture
def svc(db_conn):
    return HistoryQueryService(db=DbWrap(db_conn))


def test_fetch_history_returns_event_id(svc):
    items = svc.fetch_history_with_event_ids(offset=0, limit=10)
    assert len(items) > 0
    for item in items:
        assert "event_id" in item
        assert isinstance(item["event_id"], int)
        assert item["event_id"] > 0


def test_event_id_unique_per_row(svc):
    items = svc.fetch_history_with_event_ids(offset=0, limit=10)
    ids = [item["event_id"] for item in items]
    assert len(ids) == len(set(ids))


def test_remove_event_by_id_removes_correct_event(svc):
    items = svc.fetch_history_with_event_ids(offset=0, limit=10)
    target = items[0]
    eid = target["event_id"]
    result = svc.remove_event_by_id(eid)
    assert result["ok"]
    remaining = svc.fetch_history_with_event_ids(offset=0, limit=10)
    assert all(item["event_id"] != eid for item in remaining)


def test_remove_event_by_id_keeps_other_events(svc):
    items = svc.fetch_history_with_event_ids(offset=0, limit=10)
    count_before = len(items)
    svc.remove_event_by_id(items[0]["event_id"])
    remaining = svc.fetch_history_with_event_ids(offset=0, limit=10)
    assert len(remaining) == count_before - 1


def test_remove_event_by_id_invalid_returns_ok_noop(svc):
    result = svc.remove_event_by_id(99999)
    assert result["ok"]


def test_remove_event_by_id_no_db():
    svc = HistoryQueryService(db=None)
    result = svc.remove_event_by_id(1)
    assert not result["ok"]
    assert result["error"] == "NO_DB"


def test_fetch_history_default_does_not_have_event_id(svc):
    items = svc.fetch_history(offset=0, limit=10)
    assert all("event_id" not in item for item in items)


def test_event_id_removal_via_history_bridge(db_conn):
    from ui_qml_bridge.history_bridge import HistoryBridge
    bridge = HistoryBridge(history_query_service=HistoryQueryService(db=DbWrap(db_conn)))
    items = bridge._hqs.fetch_history_with_event_ids(offset=0, limit=10)
    assert len(items) > 0
    eid = items[0]["event_id"]
    result = bridge.removeHistoryEvent(str(eid))
    assert result["ok"]
    remaining = bridge._hqs.fetch_history_with_event_ids(offset=0, limit=10)
    assert all(item["event_id"] != eid for item in remaining)


def test_event_id_in_export_json(svc, tmp_path):
    out = tmp_path / "history_event.json"
    svc.export_history(str(out))
    import json
    data = json.loads(out.read_text())
    assert len(data) > 0
    items = svc.fetch_history_with_event_ids(offset=0, limit=10)
    assert len(items) > 0
    assert all("event_id" in item for item in items)


def test_event_id_in_export_csv(svc, tmp_path):
    out = tmp_path / "history_event.csv"
    svc.export_history(str(out), fmt="csv")
    import csv
import pytest
pytestmark = [pytest.mark.qml_module("history")]

    with open(out, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    assert "event_id" in rows[0]


def test_remove_event_does_not_affect_count_wrong_id(svc):
    count_before = svc.count_history()
    svc.remove_event_by_id(-1)
    assert svc.count_history() == count_before


def test_multiple_event_removals(svc):
    items = svc.fetch_history_with_event_ids(offset=0, limit=10)
    ids = [item["event_id"] for item in items[:3]]
    for eid in ids:
        svc.remove_event_by_id(eid)
    remaining = svc.fetch_history_with_event_ids(offset=0, limit=10)
    remaining_ids = {item["event_id"] for item in remaining}
    for eid in ids:
        assert eid not in remaining_ids
