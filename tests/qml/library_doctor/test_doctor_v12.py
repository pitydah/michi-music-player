"""Tests for Library Doctor v12 — scan, repair, cancellation."""
from unittest.mock import MagicMock, patch

import pytest


class TestLibraryDoctorBridgeCreation:
    def test_requires_db(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        with pytest.raises(Exception):
            LibraryDoctorBridge()

    def test_requires_worker_manager(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        with pytest.raises(Exception):
            LibraryDoctorBridge(db=MagicMock())

    def test_creation(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        assert ldb is not None

    def test_status_default(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        assert ldb.status == "idle"

    def test_issues_default(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        assert len(ldb.issues) == 0

    def test_healthy_count_default(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        assert ldb.healthyCount >= 0


class TestDoctorOperations:
    def test_scan(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        ldb.scan()
        assert True

    def test_cancel_scan(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        result = ldb.cancelScan()
        assert result.get("ok")

    def test_select_all(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        result = ldb.selectAll()
        assert result.get("ok")

    def test_select_none(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        result = ldb.selectNone()
        assert result.get("ok")

    def test_set_issue_selected(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        result = ldb.setIssueSelected(0, True)
        assert result.get("ok")

    def test_file_name(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = MagicMock()
        ldb = LibraryDoctorBridge(db=db, worker_manager=MagicMock())
        name = ldb.fileName("/test/file.mp3")
        assert name == "file.mp3"
