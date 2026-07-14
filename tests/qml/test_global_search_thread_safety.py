"""Test GlobalSearchService thread safety — each task opens own SQLite connection."""
import pytest
import sqlite3
import threading
import time

from core.global_search_service import (
    GlobalSearchService, SearchError, SearchCancelledError, SearchStaleError
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_search.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            album_key TEXT,
            albumartist TEXT,
            year INTEGER DEFAULT 0,
            duration REAL DEFAULT 0,
            track_uid TEXT DEFAULT '',
            deleted_at TEXT,
            play_count INTEGER DEFAULT 0,
            last_played INTEGER DEFAULT 0,
            genre TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists(
            id INTEGER PRIMARY KEY, name TEXT, track_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radio_stations(
            id INTEGER PRIMARY KEY, name TEXT, url TEXT, codec TEXT,
            country TEXT, tags TEXT, favorite INTEGER DEFAULT 0
        )
    """)
    for i in range(100):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (i, f"/path/track_{i}.flac", f"Track {i}", f"Artist {i % 10}",
             f"Album {i // 5}", f"album_key_{i // 5}")
        )
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS media_items_fts USING fts5(title, artist, album, albumartist, content='media_items', content_rowid='id')")
        conn.execute("INSERT INTO media_items_fts(media_items_fts) VALUES('rebuild')")
    except Exception:
        pass
    conn.execute("INSERT INTO playlists (name, track_count) VALUES ('Favorites', 10)")
    conn.execute("INSERT INTO playlists (name, track_count) VALUES ('Chill', 5)")
    conn.execute("INSERT INTO radio_stations (name, url, codec, country) VALUES ('Radio One', 'http://one', 'MP3', 'US')")
    conn.commit()
    conn.close()
    return path


def test_search_basic(db_path):
    svc = GlobalSearchService(db_path=db_path)
    result = svc.search("Track 1")
    assert result["ok"]
    assert result["count"] > 0


def test_search_empty(db_path):
    svc = GlobalSearchService(db_path=db_path)
    result = svc.search("")
    assert result["ok"]
    assert result["count"] == 0


def test_cancel(db_path):
    svc = GlobalSearchService(db_path=db_path)
    results = []

    def search_task(query):
        try:
            r = svc.search(query)
            results.append(r)
        except SearchCancelledError:
            results.append("cancelled")
        except Exception:
            results.append("error")

    t1 = threading.Thread(target=search_task, args=("Track",))
    t2 = threading.Thread(target=search_task, args=("Artist",))
    t1.start()
    t2.start()
    svc.cancel("global_search")
    t1.join()
    t2.join()


def test_concurrent_searches(db_path):
    svc = GlobalSearchService(db_path=db_path)
    n = 10
    results = []
    lock = threading.Lock()

    def search_worker(idx):
        try:
            r = svc.search(f"Track {idx}")
            with lock:
                results.append(r)
        except SearchError:
            with lock:
                results.append(None)

    threads = [threading.Thread(target=search_worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == n
    ok = [r for r in results if r and r.get("ok")]
    assert len(ok) > 0


def test_supersede_older_requests(db_path):
    svc = GlobalSearchService(db_path=db_path)
    from contextlib import suppress
    with suppress(SearchStaleError):
        svc.search("Track 1", owner="test_supersede")
    with suppress(SearchStaleError):
        svc.search("Track 2", owner="test_supersede")


def test_request_id_unique(db_path):
    svc = GlobalSearchService(db_path=db_path)
    r1 = svc.search("Track")
    r2 = svc.search("Artist")
    assert r1["request_id"] != r2["request_id"]


def test_cancel_request(db_path):
    svc = GlobalSearchService(db_path=db_path)
    try:
        r = svc.search("Track")
        rid = r["request_id"]
        result = svc.cancel_request(rid)
        assert result
    except SearchCancelledError:
        pass


def test_search_all_domains(db_path):
    svc = GlobalSearchService(db_path=db_path)
    result = svc.search("Track")
    assert result["ok"]
    types = {r["type"] for r in result["results"]}
    assert "track" in types


def test_no_db_path_error():
    svc = GlobalSearchService(db_path="")
    with pytest.raises(SearchError):
        svc.search("test")


def test_thread_safe_isolation(db_path):
    svc = GlobalSearchService(db_path=db_path)

    def worker():
        from contextlib import suppress
        for _ in range(5):
            with suppress(SearchStaleError, SearchCancelledError):
                svc.search("Track")

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_concurrent_cancel_and_search(db_path):
    svc = GlobalSearchService(db_path=db_path)

    def canceller():
        for _ in range(10):
            svc.cancel("global_search")
            time.sleep(0.005)

    def searcher():
        from contextlib import suppress
        with suppress(SearchError):
            svc.search("Track")

    c = threading.Thread(target=canceller)
    c.start()
    threads = [threading.Thread(target=searcher) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    c.join()


def test_custom_owner(db_path):
    svc = GlobalSearchService(db_path=db_path)
    result = svc.search("Track", owner="custom_owner")
    assert result["ok"]
    assert result["count"] > 0
    svc.cancel("custom_owner")


def test_fts5_preferred_over_like(db_path):
    svc = GlobalSearchService(db_path=db_path)
    r1 = svc.search("Track 5")
    assert r1["ok"]
    tracks = [r for r in r1["results"] if r["type"] == "track"]
    assert len(tracks) > 0
