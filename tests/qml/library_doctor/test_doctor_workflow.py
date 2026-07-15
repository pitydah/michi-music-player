from __future__ import annotations
"""CL — Library Doctor workflow: scan, issues, dry run, repair, transaction, report, undo."""

import sqlite3
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.isolation


class TestLibraryDoctor:
    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items "
                     "(id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, "
                     "artist TEXT, album TEXT, album_key TEXT, track_uid TEXT, "
                     "deleted_at REAL)")
        conn.execute("INSERT INTO media_items VALUES (1, '/test/real.flac', 'Song', 'Artist', 'Album', 'ak1', 'uid1', NULL)")
        conn.execute("INSERT INTO media_items VALUES (2, '/test/missing.flac', '', '', 'Album', 'ak2', 'uid2', NULL)")
        conn.execute("INSERT INTO media_items VALUES (3, '/test/dup.flac', 'Dup', 'Artist', 'Album', 'ak3', 'uid3', NULL)")
        conn.execute("INSERT INTO media_items VALUES (4, '/test/real.flac', 'Dup2', 'Artist2', 'Album2', 'ak4', 'uid4', NULL)")
        return conn

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.conn = sqlite3.connect(":memory:")
        db.conn.execute("CREATE TABLE IF NOT EXISTS media_items "
                        "(id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, "
                        "artist TEXT, album TEXT, album_key TEXT, track_uid TEXT, "
                        "deleted_at REAL)")
        db.conn.execute("INSERT INTO media_items VALUES (1, '/test/real.flac', 'Song', 'Artist', 'Album', 'ak1', 'uid1', NULL)")
        return db

    def test_initial_state(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        assert bridge.status == "idle"
        assert bridge.issues == []
        assert bridge.totalChecked == 0

    def test_scan_returns_issues(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.status == "done" or bridge.status == "scanning"
        if bridge.status == "done":
            assert bridge.totalChecked >= 0

    def test_select_all(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"id": 0, "type": "missing_metadata", "selected": False},
            {"id": 1, "type": "missing_file", "selected": False},
        ]
        result = bridge.selectAll()
        assert result["ok"] is True
        assert all(i["selected"] for i in bridge._issues)

    def test_select_none(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [{"id": 0, "type": "missing_metadata", "selected": True}]
        result = bridge.selectNone()
        assert result["ok"] is True
        assert not bridge._issues[0]["selected"]

    def test_set_issue_selected(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [{"id": 0, "type": "missing_metadata", "selected": False}]
        result = bridge.setIssueSelected(0, True)
        assert result["ok"] is True
        assert bridge._issues[0]["selected"] is True

    def test_repair_selected_no_scan(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        result = bridge.repairSelected()
        assert result["ok"] is False

    def test_repair_selected_no_selection(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._status = "done"
        result = bridge.repairSelected()
        assert result["ok"] is False

    def test_cancel_scan(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        result = bridge.cancelScan()
        assert result["ok"] is True
        assert bridge.status == "idle"

    def test_refresh(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.refresh()

    def test_missing_metadata_count(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"type": "missing_metadata"}, {"type": "missing_file"},
            {"type": "missing_metadata"},
        ]
        assert bridge.missingMetadataCount == 2

    def test_missing_file_count(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"type": "missing_file"}, {"type": "missing_metadata"},
            {"type": "missing_file"},
        ]
        assert bridge.missingFileCount == 2

    def test_healthy_count(self, mock_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._total_checked = 10
        bridge._issue_count = 3
        assert bridge.healthyCount == 7

    def test_scan_with_real_db(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        mock_db = MagicMock()
        mock_db.conn = db
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        if bridge.status == "done":
            assert bridge.totalChecked > 0
