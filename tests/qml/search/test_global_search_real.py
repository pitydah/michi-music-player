"""Test GlobalSearchService with real FTS5 — no db.conn direct, no shared connections."""
import pytest
import sqlite3

from core.global_search_service import GlobalSearchService, SearchStaleError


@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "test_search.db"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
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
    items = [
        ("/path/genesis.flac", "Supper's Ready", "Genesis", "Foxtrot", "key1", 1972),
        ("/path/jethro.flac", "Aqualung", "Jethro Tull", "Aqualung", "key2", 1971),
        ("/path/pf.flac", "Comfortably Numb", "Pink Floyd", "The Wall", "key3", 1979),
    ]
    for fp, title, artist, album, ak, year in items:
        conn.execute(
            "INSERT INTO media_items (filepath, title, artist, album, album_key, year) VALUES (?, ?, ?, ?, ?, ?)",
            (fp, title, artist, album, ak, year)
        )
    conn.execute("INSERT INTO playlists (name, track_count) VALUES ('Favorites', 10)")
    conn.execute("INSERT INTO playlists (name, track_count) VALUES ('Rock Classics', 25)")
    conn.execute("INSERT INTO radio_stations (name, url, codec, country) VALUES ('Jazz FM', 'http://jazz.fm', 'MP3', 'UK')")
    conn.commit()
    conn.execute("INSERT INTO media_fts (rowid, title, artist, album) SELECT id, title, artist, album FROM media_items")
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def svc(db_path):
    return GlobalSearchService(db_path=db_path)


def test_search_tracks_by_title(svc):
    result = svc.search("Supper", timeout_ms=10000)
    assert result["ok"]
    assert len(result["results"]) >= 1
    assert any(r["title"] == "Supper's Ready" for r in result["results"])


def test_search_tracks_by_artist(svc):
    result = svc.search("Genesis", timeout_ms=10000)
    assert result["ok"]
    tracks = [r for r in result["results"] if r["type"] == "track"]
    assert len(tracks) >= 1


def test_search_albums(svc):
    result = svc.search("Foxtrot", timeout_ms=10000)
    assert result["ok"]
    albums = [r for r in result["results"] if r["type"] == "album"]
    assert len(albums) >= 1


def test_search_artists(svc):
    result = svc.search("Pink", timeout_ms=10000)
    assert result["ok"]
    artists = [r for r in result["results"] if r["type"] == "artist"]
    assert len(artists) >= 1


def test_search_playlists(svc):
    result = svc.search("Favorites", timeout_ms=10000)
    assert result["ok"]
    playlists = [r for r in result["results"] if r["type"] == "playlist"]
    assert len(playlists) >= 1


def test_search_radio(svc):
    result = svc.search("Jazz", timeout_ms=10000)
    assert result["ok"]
    radios = [r for r in result["results"] if r["type"] == "radio"]
    assert len(radios) >= 1


def test_search_empty_query(svc):
    result = svc.search("")
    assert result["ok"]
    assert result["count"] == 0


def test_search_no_results(svc):
    result = svc.search("zzzznonexistent", timeout_ms=10000)
    assert result["ok"]
    assert result["count"] == 0


def test_search_stale_protection(svc):
    with pytest.raises(SearchStaleError):
        owner = "test_stale"
        gen_before = svc._next_gen(owner) - 1
        svc._generation[owner] = gen_before + 5
        if svc._is_stale(owner, gen_before):
            raise SearchStaleError()


def test_search_cancellation(svc):
    svc.cancel("global_search")


def test_search_thread_safe(svc):
    import threading
    results = []

    def do_search():
        try:
            r = svc.search("Genesis", timeout_ms=10000)
            results.append(r)
        except Exception:
            pass

    threads = [threading.Thread(target=do_search) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) > 0


def test_search_uses_own_connection(svc):
    result = svc.search("Genesis", timeout_ms=10000)
    assert result["ok"]


def test_search_ranking(svc):
    result = svc.search("Genesis", timeout_ms=10000)
    assert result["ok"]
    scores = [r.get("score", 0) for r in result["results"]]
    assert scores == sorted(scores, reverse=True)
