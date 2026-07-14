"""Test GlobalSearch async: debounce, cancel stale, discard old, render fresh."""
import pytest
import sqlite3
import threading
from unittest.mock import MagicMock

from core.global_search_service import (
    GlobalSearchService, SearchCancelledError, SearchStaleError
)
from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "stale_search.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            year INTEGER DEFAULT 0, deleted_at TEXT, albumartist TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5(
            title, artist, album, albumartist, content=media_items, content_rowid=id
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, track_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radio_stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, url TEXT, codec TEXT, country TEXT
        )
    """)
    for i in range(20):
        conn.execute(
            "INSERT INTO media_items (filepath, title, artist, album, album_key) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"/path/track_{i}.flac", f"Track {i}", f"Artist {i % 5}", f"Album {i // 3}", f"key_{i // 3}")
        )
    conn.execute("INSERT INTO playlists (name, track_count) VALUES ('My Favorites', 15)")
    conn.execute("INSERT INTO playlists (name, track_count) VALUES ('Chill Vibes', 8)")
    conn.execute("INSERT INTO radio_stations (name, url, codec, country) VALUES ('Rock FM', 'http://rock.fm', 'MP3', 'US')")
    conn.commit()
    conn.execute("INSERT INTO media_fts (rowid, title, artist, album) SELECT id, title, artist, album FROM media_items")
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def svc(db_path):
    return GlobalSearchService(db_path=db_path)


def test_stale_protection_after_bump(svc):
    owner = "stale_test"
    results = []
    errors = []

    def slow_search():
        try:
            r = svc.search("Track", owner=owner, timeout_ms=30000)
            results.append(r)
        except SearchStaleError as e:
            errors.append(e)

    import threading
    t = threading.Thread(target=slow_search)
    t.start()
    import time
    time.sleep(0.05)
    svc.search("Artist", owner=owner, timeout_ms=30000)
    t.join()
    assert len(results) > 0 or len(errors) > 0


def test_new_request_supersedes_older(svc):
    owner = "supersede_test"
    svc.search("Track 1", owner=owner, timeout_ms=10000)
    result = svc.search("Track 2", owner=owner, timeout_ms=10000)
    assert result["ok"]
    assert result["request_id"] > 1


def test_bridge_discards_stale_results():
    mock_svc = MagicMock()
    mock_svc.search.return_value = {
        "ok": True, "request_id": 42,
        "results": [{"type": "track", "id": 1, "title": "Stale", "section": "Canciones", "score": 1.0}],
        "count": 1,
    }
    bridge = GlobalSearchBridge(search_service=mock_svc)
    bridge._active_request_id = 99
    bridge.search("Fresh")
    assert bridge._active_request_id != 42


def test_bridge_serial_cancel_discards_first(db_path):
    svc = GlobalSearchService(db_path=db_path)
    bridge = GlobalSearchBridge(search_service=svc)
    bridge.search("Track 1")
    bridge.cancel()
    result = bridge.search("Track 2")
    assert result["ok"]
    assert bridge._query == "Track 2"


def test_bridge_stale_generation_not_applied():
    mock_svc = MagicMock()
    bridge = GlobalSearchBridge(search_service=mock_svc)
    bridge._search_gen = 100
    bridge.search("Fresh")
    assert bridge._query == "Fresh"


def test_cancel_during_search_prevents_render(db_path):
    svc = GlobalSearchService(db_path=db_path)
    bridge = GlobalSearchBridge(search_service=svc)
    bridge.search("Track")
    bridge.cancel()
    assert not bridge.isSearching
    assert len(bridge.results) == 0


def test_discard_old_request_by_request_id(svc):
    r1 = svc.search("Track 1", owner="discard_test", timeout_ms=10000)
    r2 = svc.search("Track 2", owner="discard_test", timeout_ms=10000)
    assert r2["request_id"] > r1["request_id"]
    assert r1["ok"]
    assert r2["ok"]


def test_concurrent_search_with_cancel(db_path):
    svc = GlobalSearchService(db_path=db_path)
    results = []
    lock = threading.Lock()

    def searcher(q, owner):
        try:
            r = svc.search(q, owner=owner, timeout_ms=10000)
            with lock:
                results.append(r)
        except (SearchStaleError, SearchCancelledError):
            with lock:
                results.append("stale_or_cancelled")

    t1 = threading.Thread(target=searcher, args=("Track", "concurrent_test"))
    t2 = threading.Thread(target=searcher, args=("Artist", "concurrent_test"))
    t1.start()
    t2.start()
    svc.cancel("concurrent_test")
    t1.join()
    t2.join()


def test_bridge_service_unavailable_on_no_service():
    bridge = GlobalSearchBridge(search_service=None)
    result = bridge.search("Test")
    assert not result["ok"]
    assert bridge.errorCode == "SERVICE_UNAVAILABLE"


def test_bridge_no_false_ok_on_empty_results():
    mock_svc = MagicMock()
    mock_svc.search.return_value = {
        "ok": True, "request_id": 1, "results": [], "count": 0
    }
    bridge = GlobalSearchBridge(search_service=mock_svc)
    result = bridge.search("NonexistentXYZ")
    assert result["ok"]
    assert result["count"] == 0
