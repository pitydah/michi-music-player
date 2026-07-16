"""Tests for LibraryService — load, refresh, counts."""
from __future__ import annotations

import sqlite3

import pytest

from core.library_service import LibraryService


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
        INSERT INTO media_items (filepath, title, artist, album, year, genre)
        VALUES
        ('/music/s1.flac', 'S1', 'A1', 'Album1', 2020, 'Rock'),
        ('/music/s2.mp3', 'S2', 'A2', 'Album2', 2021, 'Jazz'),
        ('/music/s3.flac', 'S3', 'A1', 'Album1', 2020, 'Rock'),
        ('/music/s4.flac', 'S4', 'A3', 'Album2', 2022, 'Classical'),
        ('/music/s5.flac', 'S5', 'A2', 'Album3', 2021, 'Jazz')
    """)
    conn.commit()

    fdb = type("FakeDB", (), {"conn": conn})
    return fdb


class TestLibraryService:
    def test_load(self, db):
        svc = LibraryService(db=db)
        result = svc.load()
        assert result["ok"] is True
        assert result["track_count"] == 5
        assert result["album_count"] == 3
        assert result["artist_count"] == 3
        assert result["genre_count"] == 3

    def test_load_no_db(self):
        svc = LibraryService(db=None)
        result = svc.load()
        assert result["ok"] is False

    def test_reload_after_change(self, db):
        svc = LibraryService(db=db)
        assert svc.reload_after_change("test")["ok"] is True

    def test_refresh_tab(self, db):
        svc = LibraryService(db=db)
        assert svc.refresh_tab("songs")["ok"] is True

    def test_refresh_songs(self, db):
        svc = LibraryService(db=db)
        result = svc.refresh_songs()
        assert result["ok"] is True
        assert result["count"] == 5

    def test_refresh_albums(self, db):
        svc = LibraryService(db=db)
        result = svc.refresh_albums()
        assert result["ok"] is True
        assert result["count"] >= 3

    def test_refresh_artists(self, db):
        svc = LibraryService(db=db)
        result = svc.refresh_artists()
        assert result["ok"] is True
        assert result["count"] == 3

    def test_apply_filters(self, db):
        svc = LibraryService(db=db)
        result = svc.apply_filters()
        assert result["ok"] is True
        assert result["count"] == 5

    def test_health(self, db):
        svc = LibraryService(db=db)
        assert svc.health()["available"] is True
        svc2 = LibraryService(db=None)
        assert svc2.health()["available"] is False

    def test_shutdown(self, db):
        svc = LibraryService(db=db)
        svc.shutdown()

    def test_empty_library(self):
        c = sqlite3.connect(":memory:")
        c.execute("""
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                title TEXT, artist TEXT, album TEXT,
                genre TEXT, year INTEGER, duration REAL,
                deleted_at REAL
            )
        """)
        class _FDB:
            conn = c
        svc = LibraryService(db=_FDB())
        result = svc.load()
        assert result["ok"] is True
        assert result["track_count"] == 0
