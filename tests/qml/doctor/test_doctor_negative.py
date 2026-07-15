from __future__ import annotations
"""Negative and edge-case tests for Library Doctor."""

import pytest

from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge

pytestmark = [pytest.mark.qml_module("library_doctor"), pytest.mark.qml_dimension("negative")]


class TestDoctorNegative:
    def test_null_db_no_crash(self):
        bridge = LibraryDoctorBridge(db=None)
        bridge.scan()
        assert bridge.status in ("no_data", "done", "error")

    def test_scan_when_already_scanning_noop(self):
        bridge = LibraryDoctorBridge()
        bridge._status = "scanning"
        bridge.scan()
        assert bridge._issues == []

    def test_repair_without_scan_fails(self):
        bridge = LibraryDoctorBridge()
        result = bridge.repairSelected()
        assert result["ok"] is False
        assert "NOT_SCANNED" in result.get("error", "")

    def test_repair_with_no_selection(self):
        bridge = LibraryDoctorBridge()
        bridge._status = "done"
        result = bridge.repairSelected()
        assert result["ok"] is False
        assert "NO_SELECTION" in result.get("error", "")

    def test_repair_with_empty_selection(self):
        bridge = LibraryDoctorBridge()
        bridge._status = "done"
        bridge._issues = [{"id": 1, "type": "missing_file"}]
        bridge._selected_ids.clear()
        result = bridge.repairSelected()
        assert result["ok"] is False

    def test_set_issue_selected_nonexistent_id(self):
        bridge = LibraryDoctorBridge()
        bridge._issues = [{"id": 1, "type": "missing_file", "selected": False}]
        result = bridge.setIssueSelected(999, True)
        assert result["ok"]

    def test_healthy_count_no_issues(self):
        bridge = LibraryDoctorBridge()
        bridge._total_checked = 50
        bridge._issue_count = 0
        assert bridge.healthyCount == 50

    def test_invalid_type_issue_ignored_during_repair(self):
        bridge = LibraryDoctorBridge()
        bridge._status = "done"
        bridge._issues = [{"id": 1, "type": "nonexistent_type"}]
        bridge._selected_ids = {1}
        result = bridge.repairSelected()
        assert result["ok"] is True or result.get("sync")

    def test_missing_metadata_count_zero(self):
        bridge = LibraryDoctorBridge()
        assert bridge.missingMetadataCount == 0

    def test_missing_file_count_zero(self):
        bridge = LibraryDoctorBridge()
        assert bridge.missingFileCount == 0

    def test_cancel_twice(self):
        bridge = LibraryDoctorBridge()
        bridge.cancelScan()
        bridge.cancelScan()
        assert bridge.status == "idle"

    def test_refresh_does_not_crash(self):
        bridge = LibraryDoctorBridge()
        bridge.refresh()

    def test_issues_empty_when_not_scanned(self):
        bridge = LibraryDoctorBridge()
        assert bridge.issues == []

    def test_empty_db_scan(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, "
            "title TEXT, artist TEXT, album TEXT, album_key TEXT, track_uid TEXT)"
        )
        conn.commit()
        class FakeDB:
            conn = conn
        bridge = LibraryDoctorBridge(db=FakeDB())
        bridge.scan()
        assert bridge.status in ("no_data", "done")
        assert bridge.totalChecked >= 0

    def test_zero_rows_scan(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, "
            "title TEXT, artist TEXT, album TEXT, album_key TEXT, track_uid TEXT, "
            "deleted_at REAL)"
        )
        conn.commit()
        class FakeDB:
            conn = conn
        bridge = LibraryDoctorBridge(db=FakeDB())
        bridge.scan()
        assert bridge.totalChecked == 0

    def test_repair_track_id_none_skipped(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, "
            "title TEXT, artist TEXT, album TEXT, album_key TEXT, track_uid TEXT, "
            "deleted_at REAL)"
        )
        conn.commit()
        class FakeDB:
            conn = conn
        bridge = LibraryDoctorBridge(db=FakeDB())
        bridge._status = "done"
        bridge._issues = [{"id": 1, "type": "missing_file", "track_id": None}]
        bridge._selected_ids = {1}
        result = bridge.repairSelected()
        assert result["ok"] is True or result.get("sync")

    def test_select_all_when_no_issues(self):
        bridge = LibraryDoctorBridge()
        result = bridge.selectAll()
        assert result["ok"]
        assert bridge._selected_ids == set()

    def test_select_none_when_empty(self):
        bridge = LibraryDoctorBridge()
        result = bridge.selectNone()
        assert result["ok"]
        assert bridge._selected_ids == set()

    def test_scan_sync_with_no_db(self):
        bridge = LibraryDoctorBridge(db=None)
        bridge._run_scan_sync()
        assert bridge.status in ("no_data", "done", "error")
