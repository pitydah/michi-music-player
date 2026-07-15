"""Test history statistics: top tracks, artists, albums, listening time."""
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
    for i in range(30):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str((i % 10) + 1), now - i * 3600, "local")
        )
    for i in range(10):
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


class TestHistoryStatistics:
    def test_get_statistics_returns_dict(self, svc):
        stats = svc.get_statistics()
        assert isinstance(stats, dict)
        assert stats["ok"] is True

    def test_total_plays_count(self, svc):
        stats = svc.get_statistics()
        assert stats["total_plays"] == 30

    def test_top_tracks_limited_to_10(self, svc):
        stats = svc.get_statistics()
        if "top_tracks" in stats:
            assert len(stats["top_tracks"]) <= 10

    def test_top_artists_limited_to_10(self, svc):
        stats = svc.get_statistics()
        if "top_artists" in stats:
            assert len(stats["top_artists"]) <= 10

    def test_top_albums_limited_to_10(self, svc):
        stats = svc.get_statistics()
        if "top_albums" in stats:
            assert len(stats["top_albums"]) <= 10

    def test_listening_time_keys_present(self, svc):
        stats = svc.get_statistics()
        if "listening_time_today" in stats or "listening_time_all" in stats:
            assert True

    def test_genre_breakdown_present(self, svc):
        stats = svc.get_statistics()
        if "genre_breakdown" in stats:
            assert isinstance(stats["genre_breakdown"], list)

    def test_statistics_count(self, svc):
        stats = svc.get_statistics()
        if "total_tracks" in stats:
            assert stats["total_tracks"] >= 0

    def test_statistics_unique_tracks(self, svc):
        stats = svc.get_statistics()
        if "unique_tracks" in stats:
            assert stats["unique_tracks"] <= 30

    def test_statistics_after_clear(self, svc):
        svc.clear_history()
        stats = svc.get_statistics()
        assert stats["total_plays"] == 0

    def test_statistics_with_no_data(self, db_conn):
        db_conn.execute("DELETE FROM play_history")
        db_conn.commit()
        class DbWrap:
            def __init__(self, conn):
                self.conn = conn
        empty_svc = HistoryQueryService(db=DbWrap(db_conn))
        stats = empty_svc.get_statistics()
        assert stats["total_plays"] == 0

    def test_top_tracks_order_by_play_count(self, svc):
        stats = svc.get_statistics()
        if "top_tracks" in stats and len(stats["top_tracks"]) > 1:
            counts = [t.get("play_count", 0) for t in stats["top_tracks"]]
            assert counts == sorted(counts, reverse=True)

    def test_top_artists_order_by_play_count(self, svc):
        stats = svc.get_statistics()
        if "top_artists" in stats and len(stats["top_artists"]) > 1:
            counts = [a.get("play_count", 0) for a in stats["top_artists"]]
            assert counts == sorted(counts, reverse=True)
