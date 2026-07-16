"""Tests for AlbumService — play, queue, album key navigation."""
from __future__ import annotations

import sqlite3

import pytest
from unittest.mock import MagicMock

from core.album_service import AlbumService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            year INTEGER, deleted_at REAL,
            album_key TEXT,
            track_number INTEGER
        )
    """)
    conn.execute("""
        INSERT INTO media_items (filepath, title, artist, album, year, album_key)
        VALUES
        ('/music/a1.flac', 'Track 1', 'Artist X', 'Album A', 2020, 'Artist X / Album A'),
        ('/music/a2.flac', 'Track 2', 'Artist X', 'Album A', 2020, 'Artist X / Album A'),
        ('/music/b1.flac', 'Track 1', 'Artist Y', 'Album B', 2021, 'Artist Y / Album B')
    """)
    conn.commit()
    fdb = type("FakeDB", (), {"conn": conn})
    return fdb


class TestAlbumService:
    def test_play_album(self, db):
        playback = MagicMock()
        svc = AlbumService(db=db, playback_service=playback)
        tracks = [{"filepath": "/music/a1.flac"}, {"filepath": "/music/a2.flac"}]
        result = svc.play_album(tracks)
        assert result["ok"] is True
        assert result["count"] == 2

    def test_play_album_no_tracks(self, db):
        svc = AlbumService(db=db)
        result = svc.play_album([])
        assert result["ok"] is False

    def test_queue_album(self, db):
        playback = MagicMock()
        svc = AlbumService(db=db, playback_service=playback)
        tracks = [{"filepath": "/music/a1.flac"}]
        result = svc.queue_album(tracks)
        assert result["ok"] is True

    def test_get_tracks_via_query(self, db):
        lq = MagicMock()
        lq.tracks_for_album.return_value = [{"filepath": "/music/a1.flac"}]
        svc = AlbumService(db=db, library_query_service=lq)
        result = svc.get_tracks("Artist X / Album A")
        assert len(result) == 1

    def test_navigate_to_album_by_title(self, db):
        svc = AlbumService(db=db)
        result = svc.navigate_to_album_by_title("Album A", "Artist X")
        assert result["ok"] is True
        assert "album_key" in result

    def test_navigate_to_album_not_found(self, db):
        svc = AlbumService(db=db)
        result = svc.navigate_to_album_by_title("Nonexistent")
        assert result["ok"] is False

    def test_create_playlist_from_tracks(self, db):
        from unittest.mock import MagicMock
        db.create_playlist = MagicMock(return_value=1)
        db.add_to_playlist = MagicMock(return_value=None)
        svc = AlbumService(db=db)
        tracks = [{"filepath": "/music/a1.flac"}]
        result = svc.create_playlist_from_tracks("Test", tracks)
        assert result["ok"] is True
        assert result["count"] == 1

    def test_health(self, db):
        svc = AlbumService(db=db)
        assert svc.health()["available"] is True
