"""Tests for GenresService — list, play, normalize."""
from __future__ import annotations

import sqlite3

import pytest
from unittest.mock import MagicMock

from core.genres_service import GenresService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            genre TEXT, deleted_at REAL
        )
    """)
    conn.execute("""
        INSERT INTO media_items (filepath, title, artist, genre)
        VALUES
        ('/music/r1.flac', 'Rock Song', 'A', 'Rock'),
        ('/music/r2.flac', 'Rock Two', 'B', 'Rock'),
        ('/music/j1.flac', 'Jazz Song', 'C', 'Jazz'),
        ('/music/j2.flac', 'Jazz Two', 'D', 'Jazz'),
        ('/music/null.flac', 'No Genre', 'E', NULL)
    """)
    conn.commit()
    fdb = type("FakeDB", (), {"conn": conn})
    return fdb


class TestGenresService:
    def test_list_genres(self, db):
        svc = GenresService(db=db)
        result = svc.list_genres()
        assert len(result) == 2
        genre_names = [g["name"] for g in result]
        assert "Rock" in genre_names
        assert "Jazz" in genre_names

    def test_list_genres_counts(self, db):
        svc = GenresService(db=db)
        result = svc.list_genres()
        counts = {g["name"]: g["count"] for g in result}
        assert counts["Rock"] == 2
        assert counts["Jazz"] == 2

    def test_play_genre(self, db):
        playback = MagicMock()
        svc = GenresService(db=db, playback_service=playback)
        result = svc.play_genre("Rock")
        assert result["ok"] is True
        assert result["count"] == 2
        playback.play.assert_called_once()

    def test_play_genre_no_tracks(self, db):
        playback = MagicMock()
        svc = GenresService(db=db, playback_service=playback)
        result = svc.play_genre("Nonexistent")
        assert result["ok"] is False

    def test_normalize_genre(self, db):
        svc = GenresService(db=db)
        result = svc.normalize_genre("Rock", "Hard Rock")
        assert result["ok"] is True
        genres = svc.list_genres()
        names = [g["name"] for g in genres]
        assert "Rock" not in names
        assert "Hard Rock" in names

    def test_list_no_db(self):
        svc = GenresService(db=None)
        assert svc.list_genres() == []

    def test_health(self, db):
        svc = GenresService(db=db)
        assert svc.health()["available"] is True
