"""Test history actions: play event, remove event, clear filtered/all."""
import pytest
import sqlite3
import time
from unittest.mock import MagicMock

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
            (i + 1, str(i + 1), now - i * 3600, "local")
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


@pytest.fixture
def mock_playback():
    pb = MagicMock()
    pb.play = MagicMock(return_value=None)
    return pb


def test_play_event_bridge(bridge, mock_playback):
    bridge._playback_svc = mock_playback
    mock_playback.play.return_value = {"ok": True}
    result = bridge.playHistoryItem("1")
    assert result["ok"]


def test_play_event_no_service_returns_error(bridge):
    result = bridge.playHistoryItem("1")
    assert not result["ok"]


def test_remove_event_by_id(bridge, hqs):
    result = bridge.removeHistoryEvent("1")
    assert result["ok"]
    assert hqs.count_history() == 9


def test_remove_event_by_id_second_event(bridge, hqs):
    bridge.removeHistoryEvent("3")
    assert hqs.count_history() == 9


def test_remove_nonexistent_event(bridge):
    result = bridge.removeHistoryEvent("999")
    assert result["ok"]


def test_remove_invalid_event_id(bridge):
    result = bridge.removeHistoryEvent("invalid")
    assert not result["ok"]


def test_remove_history_item(bridge, hqs):
    result = bridge.removeHistoryItem("5")
    assert result["ok"]
    assert hqs.count_history() == 9


def test_remove_history_item_then_refresh(bridge, hqs):
    bridge.removeHistoryItem("1")
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 9


def test_clear_all_history(bridge, hqs):
    result = bridge.clearHistory()
    assert result["ok"]
    assert hqs.count_history() == 0


def test_clear_history_then_refresh_empty(bridge, hqs):
    bridge.clearHistory()
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 0


def test_clear_history_then_new_entry_possible(bridge, hqs):
    bridge.clearHistory()
    hqs.record_play("new_track", device="test")
    assert hqs.count_history() == 1


def test_clear_filtered_no_filters(bridge, hqs):
    if hasattr(hqs, 'clear_filtered_history'):
        result = hqs.clear_filtered_history({})
        assert result["ok"]
        assert hqs.count_history() == 0


def test_remove_multiple_events_sequentially(bridge, hqs):
    for eid in ["1", "2", "3"]:
        bridge.removeHistoryEvent(eid)
    assert hqs.count_history() == 7


def test_bridge_reflects_changes_after_clear(bridge, hqs):
    bridge.clearHistory()
    assert bridge.historyCount == 0
