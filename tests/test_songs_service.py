"""Tests for SongsService — track listing, toggle_favorite."""
from __future__ import annotations

import sqlite3

import pytest

from core.songs_service import SongsService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            year INTEGER, genre TEXT, duration REAL,
            deleted_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("""
        INSERT INTO media_items (filepath, title, artist, album, year, genre, duration)
        VALUES
        ('/music/song1.flac', 'Song One', 'Artist A', 'Album X', 2020, 'Rock', 180),
        ('/music/song2.mp3', 'Song Two', 'Artist B', 'Album Y', 2021, 'Jazz', 240),
        ('/music/song3.flac', 'Song Three', 'Artist A', 'Album X', 2020, 'Rock', 200)
    """)
    conn.commit()

    fdb = type("FakeDB", (), {"conn": conn})
    return fdb


class TestSongsService:
    def test_load_all(self, db):
        svc = SongsService(db=db)
        result = svc.load()
        assert result["ok"] is True
        assert result["count"] == 3
        assert len(result["items"]) == 3

    def test_load_filter_artist(self, db):
        svc = SongsService(db=db)
        result = svc.load({"artist": "Artist A"})
        assert result["ok"] is True
        assert result["count"] == 2

    def test_load_filter_genre(self, db):
        svc = SongsService(db=db)
        result = svc.load({"genre": "Jazz"})
        assert result["ok"] is True
        assert result["count"] == 1

    def test_load_filter_search(self, db):
        svc = SongsService(db=db)
        result = svc.load({"search": "Two"})
        assert result["ok"] is True
        assert result["count"] == 1

    def test_load_no_db(self):
        svc = SongsService(db=None)
        result = svc.load()
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_toggle_favorite_add(self, db):
        svc = SongsService(db=db)
        result = svc.toggle_favorite("/music/song1.flac")
        assert result["ok"] is True
        assert result["favorite"] is True

    def test_toggle_favorite_remove(self, db):
        svc = SongsService(db=db)
        svc.toggle_favorite("/music/song1.flac")
        result = svc.toggle_favorite("/music/song1.flac")
        assert result["ok"] is True
        assert result["favorite"] is False

    def test_toggle_favorite_nonexistent_adds(self, db):
        svc = SongsService(db=db)
        result = svc.toggle_favorite("/nonexistent.flac")
        assert result["ok"] is True
        assert result["favorite"] is True

    def test_toggle_favorite_no_db(self):
        svc = SongsService(db=None)
        result = svc.toggle_favorite("/music/song1.flac")
        assert result["ok"] is False

    def test_health(self, db):
        svc = SongsService(db=db)
        assert svc.health()["available"] is True
        svc2 = SongsService(db=None)
        assert svc2.health()["available"] is False

    def test_shutdown(self, db):
        svc = SongsService(db=db)
        svc.shutdown()
