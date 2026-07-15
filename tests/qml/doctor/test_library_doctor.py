"""Tests for Library Doctor — scan types, progress, cancel, results, states."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge, ISSUE_TYPES

pytestmark = [pytest.mark.qml_module("library_doctor")]


@pytest.fixture
def db():
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


@pytest.fixture
def mock_db(db):
    m = MagicMock()
    m.conn = db
    return m


class TestScanTypes:
    def test_issue_types_defined(self):
        assert "missing_file" in ISSUE_TYPES
        assert "duplicate_uid" in ISSUE_TYPES
        assert "duplicate_path" in ISSUE_TYPES
        assert "missing_metadata" in ISSUE_TYPES
        assert "orphan_playlist_item" in ISSUE_TYPES
        assert "orphan_history" in ISSUE_TYPES
        assert "invalid_album_key" in ISSUE_TYPES
        assert "dead_source" in ISSUE_TYPES
        assert "cover_missing" in ISSUE_TYPES
        assert "db_integrity" in ISSUE_TYPES

    def test_scan_detects_missing_files(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/nonexistent/file.flac', 'Test', 'Artist')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types = [i["type"] for i in bridge._issues]
        assert "missing_file" in types

    def test_scan_detects_missing_metadata(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/test.flac', '', '')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types = [i["type"] for i in bridge._issues]
        assert "missing_metadata" in types

    def test_scan_detects_duplicate_path(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/dup.flac', 'A', 'B')"
        )
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/dup.flac', 'C', 'D')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types = [i["type"] for i in bridge._issues]
        assert "duplicate_path" in types

    def test_scan_detects_duplicate_uid(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist, track_uid) "
            "VALUES ('/a.flac', 'A', 'B', 'uid1')"
        )
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist, track_uid) "
            "VALUES ('/b.flac', 'C', 'D', 'uid1')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types = [i["type"] for i in bridge._issues]
        assert "duplicate_uid" in types

    def test_scan_detects_orphan_playlist(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO playlist_items (playlist_id, filepath) VALUES (1, '/orphan.flac')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types = [i["type"] for i in bridge._issues]
        assert "orphan_playlist_item" in types

    def test_scan_detects_orphan_history(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO play_history (filepath) VALUES ('/orphan.flac')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types = [i["type"] for i in bridge._issues]
        assert "orphan_history" in types


class TestScanProgress:
    def test_scanned_status_changes(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/test.flac', 'Song', 'Artist')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        assert bridge.status == "idle"
        bridge.scan()
        assert bridge.status in ("done", "no_data")

    def test_scan_updates_total_checked(self, mock_db):
        for i in range(5):
            mock_db.conn.execute(
                "INSERT INTO media_items (filepath, title, artist) "
                "VALUES (?, 'S', 'A')", (f"/test{i}.flac",)
            )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.totalChecked == 5

    def test_scan_issue_count(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/missing.flac', '', '')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.issueCount > 0


class TestCancelScan:
    def test_cancel_resets_state(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._status = "scanning"
        result = bridge.cancelScan()
        assert result["ok"]
        assert bridge.status == "idle"

    def test_cancel_during_repair(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._status = "repairing"
        result = bridge.cancelScan()
        assert result["ok"]
        assert bridge.status == "idle"

    def test_cancel_when_idle(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        result = bridge.cancelScan()
        assert result["ok"]
        assert bridge.status == "idle"


class TestStates:
    def test_initial_state(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        assert bridge.status == "idle"

    def test_scan_transitions_to_done(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/test.flac', 'S', 'A')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.status in ("done", "no_data")

    def test_no_db_no_crash(self):
        bridge = LibraryDoctorBridge(db=None)
        bridge.scan()
        assert bridge.status in ("no_data", "done", "error")

    def test_empty_db(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.status in ("no_data", "done")


class TestResultsSummary:
    def test_healthy_count(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/real.flac', 'S', 'A')"
        )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.healthyCount >= 0

    def test_missing_metadata_count(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"type": "missing_metadata"}, {"type": "missing_file"},
            {"type": "missing_metadata"},
        ]
        assert bridge.missingMetadataCount == 2

    def test_missing_file_count(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"type": "missing_file"}, {"type": "missing_metadata"},
            {"type": "missing_file"},
        ]
        assert bridge.missingFileCount == 2

    def test_issues_property_returns_copy(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [{"id": 1, "type": "test"}]
        issues = bridge.issues
        assert len(issues) == 1
        issues.append({"id": 2})
        assert len(bridge._issues) == 1

    def test_select_all_updates_all(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"id": 1, "type": "missing_file"},
            {"id": 2, "type": "missing_metadata"},
        ]
        bridge.selectAll()
        assert 1 in bridge._selected_ids
        assert 2 in bridge._selected_ids

    def test_select_none_clears(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [{"id": 1, "type": "missing_file"}]
        bridge.selectAll()
        bridge.selectNone()
        assert len(bridge._selected_ids) == 0
