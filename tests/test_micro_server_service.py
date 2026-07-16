"""Tests for MicroServerService — import tracks, albums, artists."""
from __future__ import annotations

import sqlite3

import pytest

from core.micro_server_service import MicroServerService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            album_key TEXT, deleted_at REAL
        )
    """)
    conn.execute("""
        INSERT INTO media_items (filepath, title, artist, album, album_key)
        VALUES
        ('/music/a1.flac', 'T1', 'Artist X', 'Album A', 'Artist X / Album A'),
        ('/music/a2.flac', 'T2', 'Artist X', 'Album A', 'Artist X / Album A'),
        ('/music/b1.flac', 'T1', 'Artist Y', 'Album B', 'Artist Y / Album B')
    """)
    conn.commit()
    fdb = type("_FDB", (), {"conn": conn})
    return fdb


class TestMicroServerService:
    def test_import_tracks(self, db):
        svc = MicroServerService(db=db)
        result = svc.import_tracks(["/music/a1.flac"], "http://server")
        assert result["ok"] is True
        assert result["imported"] == 1

    def test_import_album(self, db):
        svc = MicroServerService(db=db)
        result = svc.import_album("Artist X / Album A")
        assert result["ok"] is True
        assert result["imported"] == 2

    def test_import_artist(self, db):
        svc = MicroServerService(db=db)
        result = svc.import_artist("Artist X")
        assert result["ok"] is True
        assert result["imported"] == 2

    def test_import_artist_no_tracks(self, db):
        svc = MicroServerService(db=db)
        result = svc.import_artist("Nonexistent")
        assert result["ok"] is True
        assert result["imported"] == 0

    def test_check_compatibility(self, db):
        svc = MicroServerService(db=db)
        result = svc.check_compatibility()
        assert result["ok"] is True

    def test_health(self, db):
        svc = MicroServerService(db=db)
        assert svc.health()["available"] is True

    def test_shutdown(self, db):
        svc = MicroServerService(db=db)
        svc.shutdown()
