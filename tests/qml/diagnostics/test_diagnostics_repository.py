from __future__ import annotations

import sqlite3

import pytest

from ui_qml_bridge.diagnostics_repository import DiagnosticsRepository
pytestmark = [pytest.mark.qml_module("diagnostics")]



@pytest.fixture
def empty_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, deleted_at REAL)")
    conn.execute("DROP TABLE IF EXISTS metadata")
    conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
    return conn


@pytest.fixture
def repo(empty_db):
    class FakeDB:
        conn = empty_db
        db_path = ":memory:"

    return DiagnosticsRepository(db=FakeDB())


class TestDiagnosticsRepository:
    def test_integrity_pass_on_empty_db(self, repo):
        result = repo.check_integrity()
        assert result["status"] == "PASS"
        assert result["value"] == 0
        assert "Integridad OK" in result["message"]

    def test_integrity_with_tracks(self, repo, empty_db):
        empty_db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/a.mp3', 'A', 'X')")
        empty_db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/b.mp3', 'B', 'Y')")
        result = repo.check_integrity()
        assert result["status"] == "PASS"
        assert result["value"] == 2

    def test_integrity_fail_no_db(self):
        repo = DiagnosticsRepository(db=None)
        result = repo.check_integrity()
        assert result["status"] == "FAIL"

    def test_library_status_empty(self, repo):
        result = repo.library_status()
        assert result["status"] == "WARN"
        assert result["value"] == 0

    def test_library_status_with_tracks(self, repo, empty_db):
        empty_db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/a.mp3', 'A', 'X')")
        result = repo.library_status()
        assert result["status"] == "PASS"
        assert result["value"] == 1

    def test_library_status_missing_metadata(self, repo, empty_db):
        empty_db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/a.mp3', NULL, 'X')")
        result = repo.library_status()
        assert result["status"] == "WARN"
        assert "metadatos incompletos" in result["message"]

    def test_library_status_fail_no_db(self):
        repo = DiagnosticsRepository(db=None)
        result = repo.library_status()
        assert result["status"] == "FAIL"

    def test_integrity_returns_dict(self, repo):
        result = repo.check_integrity()
        assert isinstance(result, dict)
        assert "status" in result
        assert "value" in result
        assert "message" in result

    def test_library_status_returns_dict(self, repo):
        result = repo.library_status()
        assert isinstance(result, dict)
        assert "status" in result
        assert "value" in result
        assert "message" in result
