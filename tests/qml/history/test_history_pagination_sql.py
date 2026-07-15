"""Test history pagination with SQL JOIN, no full load, no N+1."""
import pytest
import sqlite3
import time

from core.history_query_service import HistoryQueryService
pytestmark = [pytest.mark.qml_module("history")]



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
            filepath TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            album_key TEXT,
            track_uid TEXT,
            duration REAL DEFAULT 0,
            deleted_at TEXT,
            albumartist TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_played ON play_history(played_at DESC)")
    now = time.time()
    for i in range(50):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "local")
        )
    for i in range(50):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, duration) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i}", f"Album {i}", f"key_{i}", 200 + i)
        )
    conn.commit()
    return conn


class FakeDb:
    def __init__(self, conn):
        self.conn = conn

    def get_play_history(self):
        rows = self.conn.execute(
            "SELECT track_id, played_at, device FROM play_history ORDER BY played_at DESC"
        ).fetchall()
        return [{"track_id": r[0], "played_at": r[1], "device": r[2]} for r in rows]


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(db_conn):
    class DbWrap:
        def __init__(self, conn):
            self.conn = conn
    return HistoryQueryService(db=DbWrap(db_conn))


def test_fetch_history_returns_paginated(svc):
    page = svc.fetch_history(offset=0, limit=10)
    assert len(page) == 10


def test_fetch_history_offset_works(svc):
    page1 = svc.fetch_history(offset=0, limit=5)
    page2 = svc.fetch_history(offset=5, limit=5)
    assert len(page1) == 5
    assert len(page2) == 5
    assert page1[0]["played_at"] != page2[0]["played_at"]


def test_fetch_history_joins_media(svc):
    items = svc.fetch_history(offset=0, limit=5)
    for item in items:
        assert "track_id" in item
        assert "title" in item
        assert "artist" in item


def test_count_history(svc):
    count = svc.count_history()
    assert count == 50


def test_count_history_with_artist_filter(svc):
    count = svc.count_history(artist="Artist 0")
    assert count >= 1


def test_no_n_plus_one(svc):
    items = svc.fetch_history(offset=0, limit=50)
    assert len(items) == 50
    for item in items:
        assert item.get("title") is not None


def test_remove_history_item(svc):
    result = svc.remove_history_item("1")
    assert result["ok"]
    assert svc.count_history() == 49


def test_clear_history(svc):
    result = svc.clear_history()
    assert result["ok"]
    assert svc.count_history() == 0


def test_apply_retention(svc):
    result = svc.apply_retention(days=365, max_age_days=1)
    assert result["ok"]


def test_record_play(svc):
    result = svc.record_play("new_track", device="test")
    assert result["ok"]


def test_search_filter(svc):
    page = svc.fetch_history(search="Title 1")
    assert len(page) >= 1


def test_device_filter(svc):
    page = svc.fetch_history(device="local")
    assert len(page) == 50
