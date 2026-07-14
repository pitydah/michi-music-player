"""Test HistoryListModel with real SQL pagination via HistoryQueryService."""
import pytest
import time
import sqlite3

from core.history_query_service import HistoryQueryService


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS media_items ("
                 "id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, "
                 "album TEXT, album_key TEXT, albumartist TEXT, duration REAL, "
                 "track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, "
                 "last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, "
                 "genre TEXT DEFAULT '')")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS play_history (
            track_id TEXT, played_at INTEGER, device TEXT
        )
    """)
    conn.commit()
    return conn


def _seed(db_conn, count: int):
    if count == 0:
        return
    now = int(time.time())
    for i in range(count):
        db_conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/to/track_{i}.flac", f"Track {i}", f"Artist {i % 50}",
             f"Album {i // 10}", f"album_key_{i // 10}")
        )
        db_conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 60, "desktop" if i % 2 == 0 else "mobile")
        )
    db_conn.commit()


class FakeDb:
    def __init__(self, conn):
        self.conn = conn


def test_empty_history():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history() == 0
    assert svc.fetch_history() == []


def test_single_entry():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    conn.execute("INSERT INTO media_items (id, filepath, title, artist, album) VALUES (1, '/t/1.flac', 'Song', 'Artist', 'Album')")
    now = int(time.time())
    conn.execute("INSERT INTO play_history (track_id, played_at, device) VALUES ('1', ?, 'desktop')", (now,))
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history() == 1
    rows = svc.fetch_history()
    assert len(rows) == 1
    assert rows[0]["title"] == "Song"


def test_1000_entries():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    db = FakeDb(conn)
    _seed(conn, 1000)
    svc = HistoryQueryService(db=db)
    assert svc.count_history() == 1000
    page = svc.fetch_history(offset=0, limit=100)
    assert len(page) == 100
    page2 = svc.fetch_history(offset=100, limit=100)
    assert len(page2) == 100
    assert page[0]["played_at"] != page2[0]["played_at"]  # different pages


def test_50000_entries():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_play_history_track_id ON play_history(track_id)")
    db = FakeDb(conn)
    now = int(time.time())
    for i in range(50000):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 60, "desktop" if i % 2 == 0 else "mobile")
        )
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (1, '1', 'Ref', 'A')")
    conn.commit()
    svc = HistoryQueryService(db=db)
    count = svc.count_history()
    assert count == 50000, f"Expected 50000, got {count}"
    page = svc.fetch_history(offset=0, limit=200)
    assert len(page) == 200
    page_mid = svc.fetch_history(offset=25000, limit=200)
    assert len(page_mid) == 200


def test_filter_artist():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    now = int(time.time())
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (1, '/t/1.flac', 'Song A', 'Artist A')")
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (2, '/t/2.flac', 'Song B', 'Artist B')")
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('1', ?)", (now,))
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('2', ?)", (now - 60,))
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history(artist="Artist A") == 1
    rows = svc.fetch_history(artist="Artist A")
    assert len(rows) == 1
    assert rows[0]["title"] == "Song A"


def test_filter_device():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    now = int(time.time())
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (1, '/t/1.flac', 'Track 1', 'Artist')")
    conn.execute("INSERT INTO play_history (track_id, played_at, device) VALUES ('1', ?, 'desktop')", (now,))
    conn.execute("INSERT INTO play_history (track_id, played_at, device) VALUES ('1', ?, 'mobile')", (now - 60,))
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history(device="desktop") == 1
    rows = svc.fetch_history(device="desktop")
    assert len(rows) == 1


def test_filter_search():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    now = int(time.time())
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (1, '/t/1.flac', 'Bohemian Rhapsody', 'Queen')")
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('1', ?)", (now,))
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history(search="Bohemian") == 1
    assert svc.count_history(search="Queen") == 1
    assert svc.count_history(search="Nonexistent") == 0


def test_retention_policy():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    old = int(time.time()) - 400 * 86400
    recent = int(time.time())
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (1, '/t/1.flac', 'Old', 'A')")
    conn.execute("INSERT INTO media_items (id, filepath, title, artist) VALUES (2, '/t/2.flac', 'New', 'B')")
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('1', ?)", (old,))
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('2', ?)", (recent,))
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history() == 2
    svc.apply_retention(max_age_days=365)
    assert svc.count_history() == 1


def test_clear_history():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    conn.execute("INSERT INTO media_items (id, filepath, title) VALUES (1, '/t/1.flac', 'T')")
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('1', 1000)")
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history() == 1
    svc.clear_history()
    assert svc.count_history() == 0


def test_delete_one():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    conn.execute("INSERT INTO media_items (id, filepath, title) VALUES (1, '/t/1.flac', 'T1')")
    conn.execute("INSERT INTO media_items (id, filepath, title) VALUES (2, '/t/2.flac', 'T2')")
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('1', 1000)")
    conn.execute("INSERT INTO play_history (track_id, played_at) VALUES ('2', 2000)")
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    assert svc.count_history() == 2
    svc.remove_history_item("1")
    assert svc.count_history() == 1


def test_no_db_returns_empty():
    svc = HistoryQueryService(db=None)
    assert svc.count_history() == 0
    assert svc.fetch_history() == []
    assert svc.remove_history_item("1") == {"ok": False, "error": "NO_DB"}
    assert svc.clear_history() == {"ok": False, "error": "NO_DB"}


def test_record_play():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE play_history (track_id TEXT, played_at INTEGER, device TEXT)")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, album_key TEXT, albumartist TEXT, duration REAL, track_uid TEXT, deleted_at TEXT, play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0, year INTEGER DEFAULT 0, genre TEXT DEFAULT '')")
    conn.execute("INSERT INTO media_items (id, filepath, title) VALUES (1, '/t/1.flac', 'T')")
    conn.commit()
    svc = HistoryQueryService(db=FakeDb(conn))
    svc.record_play("1", device="test_device")
    assert svc.count_history() == 1
    rows = svc.fetch_history()
    assert rows[0]["device"] == "test_device"
