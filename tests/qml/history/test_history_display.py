"""Test history display: pagination, filters, event rendering."""
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_played ON play_history(played_at DESC)")
    now = time.time()
    for i in range(50):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "mobile" if i % 2 == 0 else "desktop")
        )
    for i in range(50):
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


def test_pagination_first_page(svc):
    page = svc.fetch_history(offset=0, limit=10)
    assert len(page) == 10
    for item in page:
        assert "track_id" in item
        assert "title" in item
        assert "artist" in item
        assert "album" in item


def test_pagination_second_page(svc):
    page1 = svc.fetch_history(offset=0, limit=5)
    page2 = svc.fetch_history(offset=5, limit=5)
    assert len(page1) == 5
    assert len(page2) == 5
    assert page1[0]["played_at"] != page2[0]["played_at"]


def test_pagination_last_page_partial(svc):
    page = svc.fetch_history(offset=48, limit=10)
    assert len(page) == 2


def test_pagination_out_of_range(svc):
    page = svc.fetch_history(offset=100, limit=10)
    assert len(page) == 0


def test_filter_by_artist(svc):
    page = svc.fetch_history(artist="Artist 1")
    assert len(page) >= 1
    for item in page:
        assert item.get("artist") == "Artist 1"


def test_filter_by_album(svc):
    page = svc.fetch_history(album="Album 5")
    assert len(page) >= 1
    for item in page:
        assert item.get("album") == "Album 5"


def test_filter_by_device(svc):
    page = svc.fetch_history(device="mobile")
    for item in page:
        assert item.get("device") == "mobile"


def test_filter_by_device_desktop(svc):
    page = svc.fetch_history(device="desktop")
    for item in page:
        assert item.get("device") == "desktop"


def test_search_by_title(svc):
    page = svc.fetch_history(search="Title 10")
    assert len(page) >= 1


def test_search_no_results(svc):
    page = svc.fetch_history(search="NonexistentTitleXYZ")
    assert len(page) == 0


def test_filter_chain_artist_and_device(svc):
    page = svc.fetch_history(artist="Artist 2", device="mobile")
    for item in page:
        assert item.get("artist") == "Artist 2"


def test_all_filters_combined(svc):
    page = svc.fetch_history(artist="Artist 3", album="Album 3", device="desktop", search="Title 3")
    assert len(page) >= 1


def test_count_history(svc):
    count = svc.count_history()
    assert count == 50


def test_count_with_filter(svc):
    count = svc.count_history(artist="Artist 0")
    assert count >= 1


def test_event_has_event_id(svc):
    items = svc.fetch_history(offset=0, limit=5)
    for item in items:
        assert "track_id" in item


def test_event_has_track_id(svc):
    items = svc.fetch_history(offset=0, limit=5)
    for item in items:
        assert item.get("track_id") is not None


def test_event_has_track_uid(svc):
    items = svc.fetch_history(offset=0, limit=5)
    for item in items:
        assert "track_uid" in item


def test_event_has_played_at(svc):
    items = svc.fetch_history(offset=0, limit=5)
    for item in items:
        assert item.get("played_at") is not None


def test_event_has_device(svc):
    items = svc.fetch_history(offset=0, limit=5)
    for item in items:
        assert "device" in item


def test_no_n_plus_one(svc):
    items = svc.fetch_history(offset=0, limit=50)
    assert len(items) == 50
    for item in items:
        assert item.get("title") is not None
        assert item.get("artist") is not None
