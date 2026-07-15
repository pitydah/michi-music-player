"""Library Doctor workflow: scan → issue list → select → dry run → repair → report."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge

pytestmark = [pytest.mark.qml_module("library_doctor"), pytest.mark.qml_workflow("library_doctor")]


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
    conn.execute(
        "INSERT INTO media_items (filepath, title, artist) VALUES ('/real.flac', 'S1', 'A1')"
    )
    conn.execute(
        "INSERT INTO media_items (filepath, title, artist) VALUES ('/missing.flac', '', '')"
    )
    conn.execute(
        "INSERT INTO media_items (filepath, title, artist) VALUES ('/dup.flac', 'S3', 'A3')"
    )
    conn.execute(
        "INSERT INTO media_items (filepath, title, artist) VALUES ('/dup.flac', 'S4', 'A4')"
    )
    conn.commit()
    return conn


@pytest.fixture
def mock_db(db):
    m = MagicMock()
    m.conn = db
    return m


class TestLibraryDoctorWorkflow:
    def test_full_workflow_scan_to_report(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)

        assert bridge.status == "idle"
        assert bridge.issues == []

        bridge.scan()
        assert bridge.status in ("done", "no_data")
        assert len(bridge._issues) > 0

        bridge.selectAll()
        assert len(bridge._selected_ids) == len(bridge._issues)

        bridge.selectNone()
        assert len(bridge._selected_ids) == 0

        first_id = bridge._issues[0]["id"]
        bridge.setIssueSelected(first_id, True)
        assert first_id in bridge._selected_ids

        result = bridge.repairSelected()
        assert result["ok"] is True or result.get("sync") is True

        assert first_id not in bridge._selected_ids

    def test_scan_with_all_issue_types(self, mock_db):
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist, track_uid) "
            "VALUES ('/a.flac', 'T1', 'A1', 'uid1')"
        )
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist, track_uid) "
            "VALUES ('/b.flac', 'T2', 'A2', 'uid1')"
        )
        mock_db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist) "
            "VALUES ('/c.flac', '', '')"
        )
        mock_db.conn.execute(
            "INSERT INTO playlist_items (playlist_id, filepath) VALUES (1, '/orphan_p.flac')"
        )
        mock_db.conn.execute(
            "INSERT INTO play_history (filepath) VALUES ('/orphan_h.flac')"
        )
        mock_db.conn.commit()

        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        types_found = set(i["type"] for i in bridge._issues)
        assert "missing_file" in types_found
        assert "duplicate_uid" in types_found
        assert "missing_metadata" in types_found
        assert "orphan_playlist_item" in types_found
        assert "orphan_history" in types_found

    def test_select_and_deselect_individual(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge._issues = [
            {"id": 1, "type": "missing_file", "selected": False},
            {"id": 2, "type": "missing_metadata", "selected": False},
            {"id": 3, "type": "duplicate_path", "selected": False},
        ]
        bridge._selected_ids = set()

        bridge.setIssueSelected(1, True)
        assert bridge._issues[0]["selected"] is True
        assert 1 in bridge._selected_ids

        bridge.setIssueSelected(1, False)
        assert bridge._issues[0]["selected"] is False
        assert 1 not in bridge._selected_ids

    def test_progress_during_scan(self, mock_db):
        for i in range(100):
            mock_db.conn.execute(
                "INSERT INTO media_items (filepath, title, artist) "
                "VALUES (?, 'S', 'A')", (f"/t{i}.flac",)
            )
        mock_db.conn.commit()
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        assert bridge.totalChecked >= 100

    def test_report_counts_match(self, mock_db):
        bridge = LibraryDoctorBridge(db=mock_db)
        bridge.scan()
        total = bridge.totalChecked
        issues = bridge.issueCount
        healthy = bridge.healthyCount
        assert healthy == max(0, total - issues)
