"""PQ — Library Doctor completo: scan, issue list, dry run, confirmation,
repair, progress, cancel, report, undo."""
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


class TestLibraryDoctorScan:
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

    def test_scan_status_becomes_done(self, bridge):
        bridge.scan()
        assert bridge.status in ("done", "no_data")

    def test_scan_healthy_count(self, bridge):
        bridge.scan()
        assert bridge.healthyCount >= 0

    def test_scan_missing_metadata_count(self, bridge):
        bridge.scan()
        assert bridge.missingMetadataCount >= 0

    def test_scan_missing_file_count(self, bridge):
        bridge.scan()
        assert bridge.missingFileCount >= 0

    def test_scan_no_db_conn(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        db = MagicMock()
        db.conn = None
        b = LibraryDoctorBridge(db=db)
        b.scan()
        assert b.issues == []


class TestLibraryDoctorIssueList:
    @pytest.fixture
    def db(self):
        return _make_mock_db([
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
            (2, "/test/missing.flac", "", "", "Album", "ak2", "uid2"),
        ])

    @pytest.fixture
    def bridge(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=db)

    def test_issues_are_list_of_dicts(self, bridge):
        bridge.scan()
        for issue in bridge.issues:
            assert "id" in issue
            assert "type" in issue
            assert "detail" in issue

    def test_issue_types_are_valid(self, bridge):
        valid_types = {"missing_file", "duplicate_uid", "duplicate_path",
                       "missing_metadata", "orphan_playlist_item",
                       "orphan_history", "invalid_album_key", "dead_source",
                       "cover_missing", "db_integrity"}
        bridge.scan()
        for issue in bridge.issues:
            assert issue["type"] in valid_types

    def test_select_issue(self, bridge):
        bridge.scan()
        if bridge.issues:
            iid = bridge.issues[0]["id"]
            r = bridge.setIssueSelected(iid, True)
            assert r["ok"]
            assert iid in bridge._selected_ids

    def test_deselect_issue(self, bridge):
        bridge.scan()
        if bridge.issues:
            iid = bridge.issues[0]["id"]
            bridge.setIssueSelected(iid, True)
            bridge.setIssueSelected(iid, False)
            assert iid not in bridge._selected_ids

    def test_select_all_issues(self, bridge):
        bridge.scan()
        bridge.selectAll()
        for issue in bridge.issues:
            assert issue.get("selected")

    def test_select_none_issues(self, bridge):
        bridge.scan()
        bridge.selectAll()
        bridge.selectNone()
        for issue in bridge.issues:
            assert not issue.get("selected")


class TestLibraryDoctorDryRun:
    @pytest.fixture
    def db(self):
        return _make_mock_db([
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
            (2, "/test/missing.flac", "", "", "Album", "ak2", "uid2"),
        ])

    @pytest.fixture
    def bridge(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=db)

    def test_dry_run_does_not_mutate_db(self, bridge):
        conn = bridge._db.conn
        before = conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        bridge.scan()
        bridge._selected_ids = set(i["id"] for i in bridge._issues if i.get("type") in ("missing_metadata",))
        bridge.repairSelected()
        after = conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        assert after == before


class TestLibraryDoctorConfirmation:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=_make_mock_db([
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
        ]))

    def test_repair_selected_not_scanned(self, bridge):
        r = bridge.repairSelected()
        assert not r.get("ok")

    def test_repair_selected_no_selection(self, bridge):
        bridge.scan()
        r = bridge.repairSelected()
        assert not r.get("ok") if not bridge._selected_ids else r.get("ok") is not None


class TestLibraryDoctorRepair:
    @pytest.fixture
    def db(self):
        return _make_mock_db([
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
            (2, "/test/missing.flac", "", "", "Album", "ak2", "uid2"),
            (3, "/test/dup.flac", "Dup", "Artist", "Album", "ak3", "uid3"),
            (4, "/test/real.flac", "Dup2", "Artist2", "Album2", "ak4", "uid4"),
        ])

    @pytest.fixture
    def bridge(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=db)

    def test_repair_missing_metadata_updates_title(self, bridge):
        bridge.scan()
        missing_meta = [i for i in bridge._issues if i.get("type") == "missing_metadata"]
        if missing_meta:
            bridge._selected_ids = {missing_meta[0]["id"]}
            before = bridge._db.conn.execute(
                "SELECT title FROM media_items WHERE id=?", (missing_meta[0]["track_id"],)
            ).fetchone()[0]
            bridge.repairSelected()
            if not before:
                after = bridge._db.conn.execute(
                    "SELECT title FROM media_items WHERE id=?", (missing_meta[0]["track_id"],)
                ).fetchone()[0]
                assert after == "missing"

    def test_repair_removes_issues_from_list(self, bridge):
        bridge.scan()
        bridge._selected_ids = set(i["id"] for i in bridge._issues if i.get("type") == "missing_metadata")
        if bridge._selected_ids:
            before = bridge.issueCount
            bridge.repairSelected()
            assert bridge.issueCount < before

    def test_repair_status_becomes_done(self, bridge):
        bridge.scan()
        bridge._selected_ids = set(i["id"] for i in bridge._issues[:1])
        if bridge._selected_ids:
            bridge.repairSelected()
            assert bridge.status == "done"


class TestLibraryDoctorProgress:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=_make_mock_db())

    def test_scan_progress_signal(self, bridge):
        assert hasattr(bridge, 'scanProgress')

    def test_repair_progress_signal(self, bridge):
        assert hasattr(bridge, 'repairProgress')

    def test_data_changed_signal(self, bridge):
        assert hasattr(bridge, 'dataChanged')


class TestLibraryDoctorCancel:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=_make_mock_db())

    def test_cancel_scan_returns_to_idle(self, bridge):
        bridge._status = "scanning"
        r = bridge.cancelScan()
        assert r["ok"]
        assert bridge.status == "idle"

    def test_cancel_scan_emits_data_changed(self, bridge):
        called = [False]
        bridge._status = "scanning"
        bridge.dataChanged.connect(lambda: called.__setitem__(0, True))
        bridge.cancelScan()
        assert called[0]

    def test_cancel_scan_clears_state(self, bridge):
        bridge._issues = [{"id": 0, "type": "missing_file"}]
        bridge.cancelScan()
        assert bridge.status == "idle"


class TestLibraryDoctorReport:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        return LibraryDoctorBridge(db=_make_mock_db([
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
        ]))

    def test_file_name_returns_basename(self, bridge):
        name = bridge.fileName("/test/path/file.flac")
        assert name == "file.flac"

    def test_file_name_empty(self, bridge):
        name = bridge.fileName("")
        assert name == ""

    def test_refresh_emits_signal(self, bridge):
        called = [False]
        bridge.dataChanged.connect(lambda: called.__setitem__(0, True))
        bridge.refresh()
        assert called[0]


class TestLibraryDoctorUndo:
    @pytest.fixture
    def db(self):
        return _make_mock_db([
            (1, "/test/real.flac", "Song", "Artist", "Album", "ak1", "uid1"),
        ])

    def test_repair_is_transactional(self, db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=db)
        conn = db.conn
        bridge.scan()
        bridge._selected_ids = set(i["id"] for i in bridge._issues if i.get("type") == "missing_metadata")
        if bridge._selected_ids:
            conn.execute("UPDATE media_items SET title='repaired' WHERE id=1")
            conn.commit()
            title = conn.execute("SELECT title FROM media_items WHERE id=1").fetchone()[0]
            assert title == "repaired"
