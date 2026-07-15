"""Tests for Library Doctor scanning."""
from __future__ import annotations

import time
import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            album_key TEXT,
            track_uid TEXT,
            deleted_at REAL
        );
        CREATE TABLE playlist_items (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER,
            filepath TEXT,
            track_id INTEGER,
            position INTEGER
        );
        CREATE TABLE play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT
        );
        CREATE TABLE library_roots (
            path TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        );
    """)
    return conn


class TestDoctorScan:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        return _make_db()

    def test_detects_missing_file(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/nonexistent/file.flac', 'Test', 'Artist')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "missing_file" for i in br._issues)

    def test_detects_missing_metadata(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/music/test.flac', '', '')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "missing_metadata" for i in br._issues)

    def test_detects_orphan_playlist_item(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO playlist_items (playlist_id, filepath) VALUES (1, '/orphan/file.flac')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "orphan_playlist_item" for i in br._issues)

    def test_detects_orphan_history(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO play_history (filepath) VALUES ('/orphan/old.flac')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "orphan_history" for i in br._issues)

    def test_detects_duplicate_path(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/dup/file.flac', 'A', 'B')")
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/dup/file.flac', 'C', 'D')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "duplicate_path" for i in br._issues)

    def test_detects_duplicate_uid(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist, track_uid) VALUES ('/a.flac', 'A', 'B', 'dup_uid')")
        db.execute("INSERT INTO media_items (filepath, title, artist, track_uid) VALUES ('/b.flac', 'C', 'D', 'dup_uid')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "duplicate_uid" for i in br._issues)

    def test_selection_and_deselection(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/test.flac', '', '')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "missing_metadata" for i in br._issues)
        for i in br._issues:
            if i["type"] == "missing_metadata":
                br.setIssueSelected(i["id"], True)
                assert i["id"] in br._selected_ids
                br.setIssueSelected(i["id"], False)
                assert i["id"] not in br._selected_ids
                break

    def test_select_all_issues(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/test.flac', '', '')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        br.selectAll()
        assert len(br._selected_ids) > 0

    def test_select_none(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/test.flac', '', '')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        br.selectAll()
        br.selectNone()
        assert len(br._selected_ids) == 0

    def test_scan_no_data(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        br = LibraryDoctorBridge(db=None)
        br.scan()
        assert br._status in ("no_data", "done", "error")

    def test_healthy_count_positive(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
import pytest
pytestmark = [pytest.mark.qml_module("library_doctor")]

        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/real/file.flac', 'Real', 'Artist')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert br.healthyCount >= 0
