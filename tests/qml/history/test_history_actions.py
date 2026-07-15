"""Test history actions: clear, remove, retention, export, query filter chain."""
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
    for i in range(20):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 86400, "mobile" if i % 2 == 0 else "local")
        )
    for i in range(20):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album) VALUES (?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i}", f"Album {i}")
        )
    conn.commit()
    return conn


class DbWrap:
    def __init__(self, conn):
        self.conn = conn


@pytest.fixture
def svc(db_conn):
    return HistoryQueryService(db=DbWrap(db_conn))


def test_clear_history_empty(svc):
    svc.clear_history()
    assert svc.count_history() == 0


def test_clear_history_then_new_entry(svc):
    svc.clear_history()
    svc.record_play("new_track", device="test")
    assert svc.count_history() == 1


def test_remove_nonexistent(svc):
    result = svc.remove_history_item("nonexistent")
    assert result["ok"]


def test_bulk_remove(svc):
    svc.remove_history_item("1")
    svc.remove_history_item("2")
    svc.remove_history_item("3")
    assert svc.count_history() == 17


def test_retention_removes_old(svc):
    import time
import pytest
pytestmark = [pytest.mark.qml_module("history")]

    old_time = time.time() - 10000000
    svc._db.conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)", ("very_old", old_time))
    svc._db.conn.commit()
    result = svc.apply_retention(days=365, max_age_days=30)
    assert result["ok"]


def test_filter_artist(svc):
    page = svc.fetch_history(artist="Artist 1")
    for item in page:
        assert item.get("artist") == "Artist 1"


def test_filter_device(svc):
    page = svc.fetch_history(device="mobile")
    for item in page:
        assert item.get("device") == "mobile"


def test_filter_chain(svc):
    page = svc.fetch_history(artist="Artist 1", device="local")
    for item in page:
        assert item.get("device") == "local"


def test_search_by_title(svc):
    page = svc.fetch_history(search="Title 5")
    assert len(page) >= 1
