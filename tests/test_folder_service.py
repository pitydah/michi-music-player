"""Tests for FolderService — scan, integrity_check."""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from core.folder_service import FolderService


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            title TEXT, deleted_at REAL
        )
    """)
    _c = conn
    class _FakeDB:
        conn = _c
        def add_file(self, fp):
            try:
                _c.execute("INSERT INTO media_items (filepath) VALUES (?)", (fp,))
                return True
            except Exception:
                return False
    return _FakeDB()


class TestFolderService:
    def test_scan_finds_audio_files(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            flac = os.path.join(tmpdir, "test.flac")
            mp3 = os.path.join(tmpdir, "test.mp3")
            txt = os.path.join(tmpdir, "note.txt")
            for p in [flac, mp3, txt]:
                open(p, "w").close()
            svc = FolderService(db=db)
            result = svc.scan(tmpdir)
            assert result["ok"] is True
            assert result["added"] == 2

    def test_scan_skips_hidden(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            hidden = os.path.join(tmpdir, ".hidden")
            os.mkdir(hidden)
            flac = os.path.join(hidden, "song.flac")
            open(flac, "w").close()
            svc = FolderService(db=db)
            result = svc.scan(tmpdir)
            assert result["ok"] is True
            assert result["added"] == 0

    def test_scan_invalid_path(self, db):
        svc = FolderService(db=db)
        result = svc.scan("/nonexistent_path_xyz")
        assert result["ok"] is False

    def test_scan_no_db(self):
        svc = FolderService(db=None)
        result = svc.scan("/tmp")
        assert result["ok"] is False

    def test_integrity_check(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            readable = os.path.join(tmpdir, "ok.flac")
            open(readable, "w").close()
            svc = FolderService(db=db)
            result = svc.integrity_check(tmpdir)
            assert result["ok"] is True
            assert result["count"] == 0

    def test_integrity_check_invalid_path(self, db):
        svc = FolderService(db=db)
        result = svc.integrity_check("")
        assert result["ok"] is False

    def test_health(self, db):
        svc = FolderService(db=db)
        assert svc.health()["available"] is True
