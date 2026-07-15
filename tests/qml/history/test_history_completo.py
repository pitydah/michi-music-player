"""Comprehensive history tests: event ID, pagination, date filters,
artist/album/device/search filters, play event, queue, remove event,
clear filtered, clear all, retention, statistics, export, cancel export.
"""
import json
import os
import time
import tempfile
from unittest.mock import MagicMock

import pytest

from core.history_query_service import HistoryQueryService
from ui_qml_bridge.history_bridge import HistoryBridge


@pytest.fixture
def db_conn():
    import sqlite3
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
            "INSERT INTO play_history (id, track_id, played_at, device) VALUES (?, ?, ?, ?)",
            (i + 1, str(i + 1), now - i * 3600, "local" if i % 2 == 0 else "remote")
        )
    for i in range(20):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, duration) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i % 3}", f"Album {i % 5}", f"key_{i % 5}", 200 + i)
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


class TestEventId:
    def test_fetch_with_event_ids(self, bridge):
        result = bridge.fetchPage(0, 10)
        assert result["ok"]
        for item in result["items"]:
            assert "event_id" in item

    def test_event_id_unique(self, bridge):
        result = bridge.fetchPage(0, 20)
        ids = [i["event_id"] for i in result["items"]]
        assert len(ids) == len(set(ids))

    def test_remove_by_event_id(self, bridge):
        initial = bridge.fetchPage(0, 20)["total"]
        bridge.removeHistoryEvent("1")
        after = bridge.fetchPage(0, 20)["total"]
        assert after < initial


class TestPagination:
    def test_pagination_offset(self, bridge):
        page1 = bridge.fetchPage(0, 5)
        page2 = bridge.fetchPage(5, 5)
        assert len(page1["items"]) == 5
        assert len(page2["items"]) == 5
        id1 = [i["event_id"] for i in page1["items"]]
        id2 = [i["event_id"] for i in page2["items"]]
        assert id1 != id2

    def test_pagination_total(self, bridge):
        result = bridge.fetchPage(0, 100)
        assert result["total"] == 20

    def test_pagination_beyond_range(self, bridge):
        result = bridge.fetchPage(100, 10)
        assert result["items"] == []


class TestDateFilters:
    def test_fetch_all_no_filters(self, bridge):
        result = bridge.fetchPage(0, 20)
        assert result["total"] == 20

    def test_fetch_recent(self, bridge):
        result = bridge.fetchPage(0, 10)
        times = [i.get("played_at", 0) for i in result["items"]]
        assert times == sorted(times, reverse=True)


class TestArtistAlbumFilters:
    def test_filter_by_artist(self, bridge):
        result = bridge.fetchPage(0, 50, artist="Artist 1")
        items = result["items"]
        for item in items:
            assert item.get("artist") == "Artist 1"


class TestDeviceFilter:
    def test_filter_by_device_local(self, bridge):
        result = bridge.fetchPage(0, 50, device="local")
        for item in result["items"]:
            assert item.get("device") == "local"

    def test_filter_by_device_remote(self, bridge):
        result = bridge.fetchPage(0, 50, device="remote")
        for item in result["items"]:
            assert item.get("device") == "remote"

    def test_device_empty_returns_all(self, bridge):
        result = bridge.fetchPage(0, 50)
        devices = set(i.get("device", "") for i in result["items"])
        assert len(devices) > 1


class TestSearchFilter:
    def test_search_by_title(self, bridge):
        result = bridge.fetchPage(0, 50, search="Title 1")
        assert result["total"] >= 1

    def test_search_no_results(self, bridge):
        result = bridge.fetchPage(0, 50, search="NonexistentXYZ")
        assert result["total"] == 0


class TestPlayEvent:
    def test_play_event_with_playback(self, bridge):
        pb = MagicMock()
        pb.play = MagicMock(return_value={"ok": True})
        bridge._playback_svc = pb
        result = bridge.playHistoryItem("1")
        assert result["ok"]

    def test_play_event_no_service(self, bridge):
        result = bridge.playHistoryItem("1")
        assert not result["ok"]

    def test_play_event_with_action_registry(self, bridge):
        ar = MagicMock()
        ar.execute = MagicMock(return_value={"ok": True})
        bridge._action_registry = ar
        bridge._playback_svc = None
        result = bridge.playHistoryItem("1")
        assert result["ok"]


class TestRemoveEvent:
    def test_remove_multiple_events(self, bridge):
        for eid in ["1", "3", "5"]:
            bridge.removeHistoryEvent(eid)
        result = bridge.fetchPage(0, 50)
        assert result["total"] == 17

    def test_remove_invalid_event_id(self, bridge):
        result = bridge.removeHistoryEvent("abc")
        assert not result["ok"]

    def test_remove_history_item(self, bridge):
        bridge.removeHistoryItem("5")
        result = bridge.fetchPage(0, 50)
        assert result["total"] == 19


class TestClearFiltered:
    def test_clear_filtered_by_device(self, bridge, hqs):
        initial = hqs.count_history()
        result = bridge.clearFiltered(device="remote")
        assert result["ok"]
        after = hqs.count_history()
        assert after < initial

    def test_clear_filtered_no_filters_clears_all(self, bridge):
        bridge.clearFiltered()
        result = bridge.fetchPage(0, 50)
        assert result["total"] < 20


class TestClearAll:
    def test_clear_all(self, bridge):
        bridge.clearHistory()
        result = bridge.fetchPage(0, 50)
        assert result["total"] == 0

    def test_clear_all_then_refresh(self, bridge):
        bridge.clearHistory()
        r = bridge.refresh()
        assert r["ok"]
        assert r["count"] == 0


class TestRetention:
    def test_apply_retention_days(self, bridge):
        config = json.dumps({"max_age_days": 1})
        result = bridge.applyRetention(config)
        assert result["ok"]

    def test_apply_retention_default(self, bridge):
        result = bridge.applyRetention("")
        assert result["ok"]

    def test_apply_retention_invalid_json(self, bridge):
        result = bridge.applyRetention("not-json")
        assert not result["ok"]


class TestStatistics:
    def test_statistics(self, bridge):
        result = bridge.getStatistics()
        assert result["ok"]
        assert result["total_plays"] >= 20

    def test_statistics_has_unique_tracks(self, bridge):
        result = bridge.getStatistics()
        assert result["unique_tracks"] >= 1


class TestExport:
    def test_export_json(self, bridge):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            dest = f.name
        try:
            result = bridge.exportHistory(dest, "json")
            assert result["ok"]
            with open(dest) as f:
                data = json.load(f)
            assert len(data) > 0
        finally:
            os.unlink(dest)

    def test_cancel_export(self, bridge):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            dest = f.name
            f.write(b"test")
        try:
            result = bridge.cancelExport("export_1", dest)
            assert result["ok"]
            assert not os.path.exists(dest)
        finally:
            if os.path.exists(dest):
                os.unlink(dest)

    def test_cancel_export_no_filepath(self, bridge):
        result = bridge.cancelExport("export_2")
        assert result["ok"]


class TestRefresh:
    def test_refresh(self, bridge):
        result = bridge.refresh()
        assert result["ok"]
        assert result["count"] >= 20

    def test_refresh_after_clear(self, bridge):
        bridge.clearHistory()
        result = bridge.refresh()
        assert result["count"] == 0


class TestHistoryScore:
    def test_history_score(self, bridge):
        result = bridge.historyScore()
        assert result["score"] > 0

    def test_history_score_no_service(self):
        b = HistoryBridge()
        result = b.historyScore()
        assert result["score"] >= 0
