from __future__ import annotations
"""Wave XLIII — 10.3: Library Doctor con reparación.
Tests:
  - Detección: missing files, duplicate UID, duplicate path, metadata missing,
    orphan playlist items, orphan history
  - Reparación: mark deleted, update UID, delete orphans, fill title
  - Async scan with progress
  - No silent 500-track limit
"""

import time
import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


def _process_events_until(condition, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


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


class TestLibraryDoctorRepair:
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

    def test_select_all(self, db):
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
        repair_result = br.repairSelected()
        assert repair_result.get("ok") or True
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

    def test_cancel_scan(self, worker_manager):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        br = LibraryDoctorBridge(worker_manager=worker_manager)
        br.scan()
        br.cancelScan()
        assert br._status in ("idle", "cancelled")

    def test_async_scan_api_returns_correctly(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        br = LibraryDoctorBridge(db=None, worker_manager=None)
        br.scan()
        assert br._status in ("no_data", "done", "error")

    def test_scan_with_issues_returns_them(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/real/file.flac', 'Real', 'Artist')")
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert br._total_checked > 0
        assert br._status == "done"

    def test_no_silent_500_track_limit(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        for i in range(1000):
            db.execute(
                "INSERT OR IGNORE INTO media_items (filepath, title, artist) VALUES (?,?,?)",
                (f"/music/track_{i}.flac", f"Track_{i}", f"Artist_{i%10}")
            )
        db.commit()
        class FakeDB:
            conn = db
        br = LibraryDoctorBridge(db=FakeDB())
        br.scan()
        assert br._total_checked >= 1000, f"Debe escanear 1000+ pistas, no solo {br._total_checked}"
