"""Full workflow: filter -> play event -> remove event -> export.

Tests the complete history lifecycle across bridges:
1. Filter history by artist
2. Play an event from the filtered results
3. Remove an event
4. Export remaining history
"""
from __future__ import annotations

import sqlite3
import time
import json
from unittest.mock import MagicMock

import pytest

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
    for i in range(10):
        conn.execute(
            "INSERT INTO play_history (id, track_id, played_at, device) VALUES (?, ?, ?, ?)",
            (i + 1, str(i + 1), now - i * 3600, "mobile" if i % 2 == 0 else "desktop")
        )
    for i in range(10):
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


class TestHistoryWorkflow:
    def test_full_workflow_filter_play_remove_export(self, bridge, hqs, tmp_path):
        # 1. Initial state
        assert hqs.count_history() == 10

        # 2. Filter by artist
        filtered = hqs.fetch_history(artist="Artist 0")
        assert len(filtered) >= 1

        # 3. Play an event
        mock_pb = MagicMock()
        mock_pb.play = MagicMock(return_value={"ok": True})
        bridge._playback_svc = mock_pb
        play_result = bridge.playHistoryItem("1")
        assert play_result["ok"]

        # 4. Remove an event
        remove_result = bridge.removeHistoryEvent("1")
        assert remove_result["ok"]
        assert hqs.count_history() == 9

        # 5. Export remaining
        out = tmp_path / "workflow_export.json"
        export_result = bridge.exportHistory(str(out))
        assert export_result["ok"]
        assert export_result["count"] == 9
        assert out.exists()
        data = json.loads(out.read_text())
        assert len(data) == 9
        assert all("track_id" in e for e in data)

    def test_workflow_filter_by_device_and_remove(self, bridge, hqs):
        filtered = hqs.fetch_history(device="mobile")
        track_ids = [e.get("track_id") for e in filtered if e.get("track_id")]
        for tid in track_ids[:2]:
            bridge.removeHistoryItem(str(tid))
        remaining = hqs.count_history()
        assert remaining < 10

    def test_workflow_clear_after_filter(self, bridge, hqs):
        bridge.clearHistory()
        assert hqs.count_history() == 0
        stats = hqs.get_statistics()
        assert stats["total_plays"] == 0

    def test_workflow_play_after_remove(self, bridge, hqs):
        bridge.removeHistoryItem("2")
        mock_pb = MagicMock()
        mock_pb.play = MagicMock(return_value={"ok": True})
        bridge._playback_svc = mock_pb
        result = bridge.playHistoryItem("3")
        assert result["ok"]

    def test_workflow_export_after_clear(self, bridge, hqs, tmp_path):
        bridge.clearHistory()
        out = tmp_path / "after_clear.json"
        result = bridge.exportHistory(str(out))
        assert result["ok"]
        assert result["count"] == 0

    def test_workflow_filter_search_and_play(self, bridge, hqs):
        hqs.fetch_history(search="Title 5")
        mock_pb = MagicMock()
        mock_pb.play = MagicMock(return_value={"ok": True})
        bridge._playback_svc = mock_pb
        result = bridge.playHistoryItem("5")
        assert result["ok"]

    def test_workflow_remove_nonexistent_then_export(self, bridge, hqs, tmp_path):
        bridge.removeHistoryEvent("999")
        out = tmp_path / "no_change.json"
        result = bridge.exportHistory(str(out))
        assert result["ok"]
        assert result["count"] == 10

    def test_workflow_full_cycle(self, bridge, hqs, tmp_path):
        bridge.clearHistory()
        assert hqs.count_history() == 0
        for i in range(3):
            hqs.record_play(f"new_{i}", device="test")
        assert hqs.count_history() == 3
        out = tmp_path / "cycle.json"
        result = bridge.exportHistory(str(out))
        assert result["ok"]
        assert result["count"] == 3
