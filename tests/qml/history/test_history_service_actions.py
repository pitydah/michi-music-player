"""Test HistoryBridge actions: export, play, remove eventId, clear, retention, injection."""
import pytest
import sqlite3
import time
import json
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
    for i in range(5):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "local")
        )
    for i in range(5):
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


@pytest.fixture
def mock_action_registry():
    reg = MagicMock()
    reg.execute = MagicMock(return_value={"ok": True})
    return reg


def test_export_history_creates_file(bridge, tmp_path):
    out = tmp_path / "history.json"
    result = bridge.exportHistory(str(out))
    assert result["ok"]
    assert result["count"] == 5
    assert out.exists()
    data = json.loads(out.read_text())
    assert len(data) == 5
    assert "event_id" in data[0]
    assert data[0]["title"] == "Title 0"


def test_export_history_empty_path_fails(bridge):
    result = bridge.exportHistory("")
    assert not result["ok"]


def test_play_history_item_with_playback_service(bridge, hqs, mock_playback):
    bridge._playback_svc = mock_playback
    result = bridge.playHistoryItem("1")
    assert result["ok"]


def test_play_history_item_no_service_returns_error(bridge):
    result = bridge.playHistoryItem("1")
    assert not result["ok"]


def test_play_history_item_with_action_registry(bridge, mock_action_registry):
    bridge._action_registry = mock_action_registry
    bridge._playback_svc = None
    result = bridge.playHistoryItem("1")
    assert result["ok"]
    mock_action_registry.execute.assert_called_with("track_play_now")


def test_remove_history_event_by_id(bridge, hqs):
    result = bridge.removeHistoryEvent("1")
    assert result["ok"]
    assert hqs.count_history() == 4


def test_remove_nonexistent_event(bridge):
    result = bridge.removeHistoryEvent("999")
    assert result["ok"]


def test_clear_history(bridge, hqs):
    result = bridge.clearHistory()
    assert result["ok"]
    assert hqs.count_history() == 0


def test_clear_history_then_refresh_empty(bridge, hqs):
    bridge.clearHistory()
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 0


def test_apply_retention_policy(bridge, hqs):
    old_time = time.time() - 10000000
    hqs._db.conn.execute("INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
                         ("old_track", old_time, "local"))
    hqs._db.conn.commit()
    result = bridge.applyRetention(json.dumps({"max_age_days": 1}))
    assert result["ok"]
    assert hqs.count_history() == 5
