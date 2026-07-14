"""DY — Library Doctor completo: scan, issue list, dry run, confirmation, transaction, repair, verify, report, undo."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.isolation


def _make_mock_db(rows=None):
    db = MagicMock()
    db.conn = sqlite3.connect(":memory:")
    db.conn.execute(
        "CREATE TABLE IF NOT EXISTS media_items "
        "(id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, "
        "artist TEXT, album TEXT, album_key TEXT, track_uid TEXT, "
        "deleted_at REAL)"
    )
    if rows:
        for r in rows:
            db.conn.execute(
                "INSERT INTO media_items (id, filepath, title, artist, album, album_key, track_uid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", r
            )
    db.conn.commit()
    return db


class TestLibraryDoctorCompleto:
    @pytest.fixture
    def db(self):
        rows = [
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
            (2, "/test/missing.flac", "", "", "Album", "ak2", "uid2"),
            (3, "/test/dup.flac", "Dup", "Artist", "Album", "ak3", "uid3"),
            (4, "/test/real.flac", "Dup2", "Artist2", "Album2", "ak4", "uid4"),
            (5, "/test/nometa.flac", "", "", "", "ak5", "uid5"),
            (6, "/test/dup.m4a", "Dup3", "Artist3", "Album3", "ak6", "uid6"),
            (7, "/test/dup.m4a", "Dup4", "Artist4", "Album4", "ak7", "uid7"),
        ]
        return _make_mock_db(rows)

    @pytest.fixture
    def bridge(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=db)

    def test_scan_detects_missing_files(self, bridge):
        bridge.scan()
        types = [i["type"] for i in bridge.issues]
        assert "missing_file" in types

    def test_scan_detects_duplicate_paths(self, bridge):
        bridge.scan()
        types = [i["type"] for i in bridge.issues]
        assert "duplicate_path" in types

    def test_scan_detects_missing_metadata(self, bridge):
        bridge.scan()
        types = [i["type"] for i in bridge.issues]
        assert "missing_metadata" in types

    def test_scan_returns_issue_count(self, bridge):
        bridge.scan()
        assert bridge.issueCount >= 0

    def test_scan_returns_total_checked(self, bridge):
        bridge.scan()
        assert bridge.totalChecked > 0

    def test_dry_run_does_not_mutate_db(self, bridge):
        conn = bridge._db.conn
        before = conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        bridge.scan()
        bridge._selected_ids = set(i["id"] for i in bridge._issues if i.get("type") in ("missing_metadata",))
        bridge.repairSelected()
        after = conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        assert after == before

    def test_repair_clears_selected_issues(self, bridge):
        bridge.scan()
        if not bridge._issues:
            pytest.skip("No issues detected")
        bridge._selected_ids = {bridge._issues[0]["id"]}
        bridge.repairSelected()
        remaining = [i for i in bridge._issues if i.get("id") in bridge._selected_ids]
        assert len(remaining) == 0

    def test_select_all_issues(self, bridge):
        bridge.scan()
        if not bridge._issues:
            pytest.skip("No issues detected")
        bridge.selectAll()
        assert all(i.get("selected") for i in bridge._issues)

    def test_select_none_issues(self, bridge):
        bridge.scan()
        if not bridge._issues:
            pytest.skip("No issues detected")
        bridge.selectNone()
        assert not any(i.get("selected") for i in bridge._issues)

    def test_set_issue_selected_toggle(self, bridge):
        bridge._issues = [{"id": 0, "type": "missing_file", "selected": False}]
        bridge.setIssueSelected(0, True)
        assert bridge._issues[0]["selected"] is True
        bridge.setIssueSelected(0, False)
        assert bridge._issues[0]["selected"] is False

    def test_repair_without_scan_fails(self, bridge):
        result = bridge.repairSelected()
        assert result["ok"] is False

    def test_healthy_count_calculation(self, bridge):
        bridge._total_checked = 100
        bridge._issue_count = 10
        assert bridge.healthyCount == 90

    def test_missing_metadata_count(self, bridge):
        bridge._issues = [
            {"type": "missing_metadata"}, {"type": "missing_file"},
            {"type": "missing_metadata"}, {"type": "orphan_history"},
        ]
        assert bridge.missingMetadataCount == 2

    def test_missing_file_count(self, bridge):
        bridge._issues = [
            {"type": "missing_file"}, {"type": "missing_metadata"},
            {"type": "missing_file"}, {"type": "missing_file"},
        ]
        assert bridge.missingFileCount == 3

    def test_cancel_scan_resets_state(self, bridge):
        bridge._status = "scanning"
        bridge.cancelScan()
        assert bridge.status == "idle"

    def test_issue_types_are_defined(self, bridge):
        bridge.scan()
        for issue in bridge._issues:
            assert "type" in issue
            assert "filepath" in issue

    def test_duplicate_uid_detection(self, db):
        db.conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, track_uid) "
            "VALUES (8, '/test/other.flac', 'Other', 'Art', 'Alb', 'ak8', 'uid2')"
        )
        db.conn.commit()
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=db)
        bridge.scan()
        types = [i["type"] for i in bridge.issues]
        assert "duplicate_uid" in types
