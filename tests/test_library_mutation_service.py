"""Tests for LibraryMutationService — update_metadata, batch_update."""
from __future__ import annotations

import sqlite3

import pytest

from core.library_mutation_service import LibraryMutationService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            genre TEXT, year INTEGER, track INTEGER, disc INTEGER,
            deleted_at REAL
        )
    """)
    conn.execute("""
        INSERT INTO media_items (id, filepath, title, artist, album, genre, year, track)
        VALUES
        (1, '/music/s1.flac', 'Track 1', 'Artist', 'Album', 'Rock', 2020, 1),
        (2, '/music/s2.flac', 'Track 2', 'Artist', 'Album', 'Rock', 2020, 2),
        (3, '/music/s3.flac', 'Track 3', 'Artist', 'Album', 'Jazz', 2021, 3)
    """)
    conn.commit()
    fdb = type("FakeDB", (), {"conn": conn})
    return fdb


class TestLibraryMutationService:
    def test_update_title(self, db):
        svc = LibraryMutationService(db=db, query_service=None)
        result = svc.update_metadata(1, {"title": "New Title"})
        assert result["ok"] is True
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE id=1"
        ).fetchone()
        assert row[0] == "New Title"

    def test_update_multiple_fields(self, db):
        svc = LibraryMutationService(db=db)
        result = svc.update_metadata(1, {"title": "T1", "artist": "A1", "genre": "Pop"})
        assert result["ok"] is True
        row = db.conn.execute(
            "SELECT title, artist, genre FROM media_items WHERE id=1"
        ).fetchone()
        assert row == ("T1", "A1", "Pop")

    def test_update_no_fields(self, db):
        svc = LibraryMutationService(db=db)
        result = svc.update_metadata(1, {})
        assert result["ok"] is False

    def test_update_no_db(self):
        svc = LibraryMutationService(db=None)
        result = svc.update_metadata(1, {"title": "X"})
        assert result["ok"] is False

    def test_batch_update_all_ok(self, db):
        svc = LibraryMutationService(db=db)
        updates = [
            {"track_id": 1, "data": {"title": "T1"}},
            {"track_id": 2, "data": {"artist": "A2"}},
        ]
        result = svc.batch_update(updates)
        assert result["ok"] is True
        assert result["updated"] == 2
        assert result["failed"] == 0

    def test_batch_update_partial_invalid(self, db):
        svc = LibraryMutationService(db=db)
        updates = [
            {"track_id": 1, "data": {"title": "T1"}},
            {"track_id": 2, "data": {}},
        ]
        result = svc.batch_update(updates)
        assert result["updated"] == 1
        assert result["failed"] == 1

    def test_rollback_not_implemented(self, db):
        svc = LibraryMutationService(db=db)
        svc.update_metadata(1, {"title": "New"})
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE id=1"
        ).fetchone()
        assert row[0] == "New"
