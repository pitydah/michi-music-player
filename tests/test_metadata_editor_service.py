"""Tests for MetadataEditorService — preview, apply, rollback."""
from __future__ import annotations

import sqlite3

import pytest

from core.metadata_editor_service import MetadataEditorService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            genre TEXT, year INTEGER, deleted_at REAL
        )
    """)
    conn.execute("""
        INSERT INTO media_items (filepath, title, artist, album, genre, year)
        VALUES ('/music/test.flac', 'Old Title', 'Old Artist', 'Album', 'Rock', 2020)
    """)
    conn.commit()
    fdb = type("FakeDB", (), {"conn": conn})
    return fdb


class TestMetadataEditorService:
    def test_preview(self, db):
        svc = MetadataEditorService(db=db)
        changes = {"title": "New Title"}
        result = svc.preview("/music/test.flac", changes)
        assert result["ok"] is True
        assert result["changes"] == changes

    def test_apply_title(self, db):
        svc = MetadataEditorService(db=db)
        result = svc.apply("/music/test.flac", {"title": "New Title"})
        assert result["ok"] is True
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?", ("/music/test.flac",)
        ).fetchone()
        assert row[0] == "New Title"

    def test_apply_artist(self, db):
        svc = MetadataEditorService(db=db)
        result = svc.apply("/music/test.flac", {"artist": "New Artist"})
        assert result["ok"] is True

    def test_apply_genre(self, db):
        svc = MetadataEditorService(db=db)
        result = svc.apply("/music/test.flac", {"genre": "Jazz"})
        assert result["ok"] is True

    def test_apply_year(self, db):
        svc = MetadataEditorService(db=db)
        result = svc.apply("/music/test.flac", {"year": 2025})
        assert result["ok"] is True

    def test_apply_no_db(self):
        svc = MetadataEditorService(db=None)
        result = svc.apply("/music/test.flac", {"title": "X"})
        assert result["ok"] is False

    def test_rollback(self, db):
        svc = MetadataEditorService(db=db)
        svc.apply("/music/test.flac", {"title": "New Title"})
        result = svc.rollback("/music/test.flac", "title", "Old Title")
        assert result["ok"] is True
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?", ("/music/test.flac",)
        ).fetchone()
        assert row[0] == "Old Title"

    def test_rollback_no_db(self):
        svc = MetadataEditorService(db=None)
        result = svc.rollback("/music/test.flac", "title", "Old")
        assert result["ok"] is False

    def test_health(self, db):
        svc = MetadataEditorService(db=db)
        assert svc.health()["available"] is True
