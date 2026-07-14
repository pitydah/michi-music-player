"""Tests for Library Doctor repair operations."""
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
    """)
    return conn


class TestDoctorRepair:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def worker_manager(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def db(self):
        return _make_db()

    def test_repair_missing_metadata_fills_title(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/music/test_track.flac', '', 'Artist')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        br.selectAll()
        br.repairSelected()
        row = db.execute("SELECT title FROM media_items WHERE filepath='/music/test_track.flac'").fetchone()
        assert row and row[0] == "test_track"

    def test_repair_orphan_playlist_deletes(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO playlist_items (playlist_id, filepath) VALUES (1, '/orphan.flac')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "orphan_playlist_item" for i in br._issues)
        br.selectAll()
        br.repairSelected()
        remaining = db.execute("SELECT COUNT(*) FROM playlist_items").fetchone()
        assert remaining[0] == 0

    def test_repair_orphan_history_deletes(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO play_history (filepath) VALUES ('/orphan.flac')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert any(i["type"] == "orphan_history" for i in br._issues)
        br.selectAll()
        br.repairSelected()
        remaining = db.execute("SELECT COUNT(*) FROM play_history").fetchone()
        assert remaining[0] == 0

    def test_repair_duplicate_path_marks_deleted(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/dup/file.flac', 'A', 'B')")
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/dup/file.flac', 'C', 'D')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        dup = [i for i in br._issues if i["type"] == "duplicate_path"]
        assert dup
        br._selected_ids = {d["id"] for d in dup}
        br.repairSelected()
        deleted = db.execute("SELECT COUNT(*) FROM media_items WHERE deleted_at IS NOT NULL").fetchone()
        assert deleted[0] > 0

    def test_repair_duplicate_uid_renames(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist, track_uid) VALUES ('/a.flac', 'A', 'B', 'dup_uid')")
        db.execute("INSERT INTO media_items (filepath, title, artist, track_uid) VALUES ('/b.flac', 'C', 'D', 'dup_uid')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        duids = [i for i in br._issues if i["type"] == "duplicate_uid"]
        assert duids
        br._selected_ids = {d["id"] for d in duids}
        br.repairSelected()
        uids = db.execute("SELECT track_uid FROM media_items").fetchall()
        assert len(set(u[0] for u in uids if u[0])) > 1

    def test_repair_selected_no_scan(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        result = br.repairSelected()
        assert not result.get("ok")

    def test_repair_selected_no_selection(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/test.flac', '', '')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        result = br.repairSelected()
        assert not result.get("ok")

    def test_cancel_scan_returns_ok(self, worker_manager):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        br = LibraryDoctorBridge(worker_manager=worker_manager)
        result = br.cancelScan()
        assert result.get("ok")

    def test_repair_with_worker_manager(self, db, worker_manager):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/music/test.flac', '', '')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB(), worker_manager=worker_manager)
        br.scan()
        br.selectAll()
        result = br.repairSelected()
        assert result.get("ok") is not None

    def test_properties_after_scan(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/real/file.flac', 'Real', 'Artist')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert br.totalChecked >= 0
        assert br.issueCount >= 0
        assert br.missingMetadataCount >= 0
        assert br.missingFileCount >= 0
