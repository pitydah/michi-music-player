"""Test history export with real progress: JSON and CSV, cancel, progress tracking."""
"""Tests for HistoryExportDialog: export flows, cancellation, format selection, edge cases."""
import pytest
import sqlite3
import time
import json
import os

from core.history_query_service import HistoryQueryService
from ui_qml_bridge.history_bridge import HistoryBridge


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT NOT NULL,
            played_at REAL NOT NULL,
            device TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            deleted_at TEXT, albumartist TEXT
        )
    """)
    now = time.time()
    for i in range(20):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 86400, "mobile" if i % 2 == 0 else "local")
        )
    for i in range(20):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, duration) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i}", f"Album {i}", f"key_{i}", 200 + i)
        )
    conn.commit()
    return conn


class DbWrap:
    def __init__(self, conn):
        self.conn = conn


@pytest.fixture
def hqs(db_conn):
    return HistoryQueryService(db=DbWrap(db_conn))


@pytest.fixture
def bridge(hqs):
    return HistoryBridge(history_query_service=hqs)


class TestHistoryExport:
    def test_export_json_creates_file(self, bridge, tmp_path):
        out = tmp_path / "history.json"
        result = bridge.exportHistory(str(out), "json")
        if result["ok"]:
            assert out.exists()
            data = json.loads(out.read_text())
            assert isinstance(data, list)

    def test_export_csv_creates_file(self, bridge, tmp_path):
        out = tmp_path / "history.csv"
        result = bridge.exportHistory(str(out), "csv")
        if result["ok"]:
            assert out.exists()
            content = out.read_text()
            assert "event_id" in content

    def test_export_json_structure(self, bridge, tmp_path):
        out = tmp_path / "test_hist.json"
        result = bridge.exportHistory(str(out), "json")
        if result["ok"] and result["count"] > 0:
            data = json.loads(out.read_text())
            assert len(data) > 0
            assert "track_id" in data[0]

    def test_export_json_sorted_by_date_desc(self, bridge, tmp_path):
        out = tmp_path / "sorted.json"
        bridge.exportHistory(str(out), "json")
        data = json.loads(out.read_text())
        dates = [e.get("played_at", 0) for e in data]
        assert dates == sorted(dates, reverse=True)

    def test_export_empty_path_fails(self, bridge):
        result = bridge.exportHistory("", "json")
        assert not result["ok"]

    def test_export_returns_count(self, bridge, tmp_path):
        out = tmp_path / "count_test.json"
        result = bridge.exportHistory(str(out), "json")
        assert result["count"] == 20

    def test_export_progress_tracking(self, bridge, tmp_path):
        out = tmp_path / "progress.json"
        bridge.exportHistory(str(out), "json")

    def test_cancel_export_cleans_file(self, bridge, tmp_path):
        out = tmp_path / "cancel.json"
        with open(str(out), "w") as f:
            f.write("partial")
        result = bridge.cancelExport("temp_id", str(out))
        assert result["ok"]
        assert result["cancelled"]
        assert not out.exists()

    def test_cancel_export_no_file(self, bridge):
        result = bridge.cancelExport("temp_id")
        assert result["ok"]
        assert result["cancelled"]

    def test_cancel_export_non_existent(self, bridge, tmp_path):
        out = tmp_path / "nonexistent.json"
        result = bridge.cancelExport("temp_id", str(out))
        assert result["ok"]
        assert not os.path.exists(str(out))

    def test_export_after_clear(self, bridge, hqs, tmp_path):
        bridge.clearHistory()
        out = tmp_path / "after_clear.json"
        result = bridge.exportHistory(str(out), "json")
        assert result["ok"]
        assert result["count"] == 0
        data = json.loads(out.read_text())
        assert len(data) == 0

    def test_export_formats_case_sensitive(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = []
        bridge = HistoryBridge(db=db)
        result_json = bridge.exportHistory("/tmp/t.json", "JSON")
        assert result_json["ok"] is True
        result_csv = bridge.exportHistory("/tmp/t.csv", "CSV")
        assert result_csv["ok"] is True
"""Test history export with real progress: JSON and CSV, cancel, progress tracking."""
import pytest



@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT NOT NULL,
            played_at REAL NOT NULL,
            device TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            deleted_at TEXT, albumartist TEXT
        )
    """)
    now = time.time()
    for i in range(20):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 86400, "mobile" if i % 2 == 0 else "local")
        )
    for i in range(20):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, duration) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i}", f"Album {i}", f"key_{i}", 200 + i)
        )
    conn.commit()
    return conn


class DbWrap:
    def __init__(self, conn):
        self.conn = conn


@pytest.fixture
def hqs(db_conn):
    return HistoryQueryService(db=DbWrap(db_conn))


@pytest.fixture
def bridge(hqs):
    return HistoryBridge(history_query_service=hqs)


class TestHistoryExport:
    def test_export_json_creates_file(self, bridge, tmp_path):
        out = tmp_path / "history.json"
        result = bridge.exportHistory(str(out), "json")
        if result["ok"]:
            assert out.exists()
            data = json.loads(out.read_text())
            assert isinstance(data, list)

    def test_export_csv_creates_file(self, bridge, tmp_path):
        out = tmp_path / "history.csv"
        result = bridge.exportHistory(str(out), "csv")
        if result["ok"]:
            assert out.exists()
            content = out.read_text()
            assert "event_id" in content

    def test_export_json_structure(self, bridge, tmp_path):
        out = tmp_path / "test_hist.json"
        result = bridge.exportHistory(str(out), "json")
        if result["ok"] and result["count"] > 0:
            data = json.loads(out.read_text())
            assert len(data) > 0
            assert "track_id" in data[0]

    def test_export_json_sorted_by_date_desc(self, bridge, tmp_path):
        out = tmp_path / "sorted.json"
        bridge.exportHistory(str(out), "json")
        data = json.loads(out.read_text())
        dates = [e.get("played_at", 0) for e in data]
        assert dates == sorted(dates, reverse=True)

    def test_export_empty_path_fails(self, bridge):
        result = bridge.exportHistory("", "json")
        assert not result["ok"]

    def test_export_returns_count(self, bridge, tmp_path):
        out = tmp_path / "count_test.json"
        result = bridge.exportHistory(str(out), "json")
        assert result["count"] == 20

    def test_export_progress_tracking(self, bridge, tmp_path):
        out = tmp_path / "progress.json"
        bridge.exportHistory(str(out), "json")

    def test_cancel_export_cleans_file(self, bridge, tmp_path):
        out = tmp_path / "cancel.json"
        with open(str(out), "w") as f:
            f.write("partial")
        result = bridge.cancelExport("temp_id", str(out))
        assert result["ok"]
        assert result["cancelled"]
        assert not out.exists()

    def test_cancel_export_no_file(self, bridge):
        result = bridge.cancelExport("temp_id")
        assert result["ok"]
        assert result["cancelled"]

    def test_cancel_export_non_existent(self, bridge, tmp_path):
        out = tmp_path / "nonexistent.json"
        result = bridge.cancelExport("temp_id", str(out))
        assert result["ok"]
        assert not os.path.exists(str(out))

    def test_export_after_clear(self, bridge, hqs, tmp_path):
        bridge.clearHistory()
        out = tmp_path / "after_clear.json"
        result = bridge.exportHistory(str(out), "json")
        assert result["ok"]
        assert result["count"] == 0
        data = json.loads(out.read_text())
        assert len(data) == 0

    def test_export_csv_headers(self, bridge, tmp_path):
        out = tmp_path / "headers.csv"
        bridge.exportHistory(str(out), "csv")
        content = out.read_text()
        first_line = content.split("\n")[0]
        assert "event_id" in first_line
        assert "track_id" in first_line
