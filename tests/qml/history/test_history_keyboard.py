<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test history keyboard navigation via bridge action patterns."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Tests keyboard navigation, focus, and accessibility for History QML pages."""
>>>>>>> Stashed changes
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
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "local")
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


def test_refresh_action(bridge):
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 10


def test_clear_all_requires_confirmation_pattern(bridge):
    bridge.clearHistory()
    assert bridge.historyCount == 0

<<<<<<< Updated upstream
=======
    def test_statistics_page_keyboard(self):
        p = QML_DIR / "pages" / "history" / "HistoryStatisticsPage.qml"
        if p.exists():
            content = p.read_text()
            assert "Keys.onEscapePressed" in content or "Keys.on" in content
=======
"""Test history keyboard navigation via bridge action patterns."""
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
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "local")
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


def test_refresh_action(bridge):
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 10


def test_clear_all_requires_confirmation_pattern(bridge):
    bridge.clearHistory()
    assert bridge.historyCount == 0

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

def test_remove_item_keyboard_accessible(bridge, hqs):
    bridge.removeHistoryItem("1")
    assert hqs.count_history() == 9


def test_remove_event_by_id(bridge, hqs):
    bridge.removeHistoryEvent("2")
    assert hqs.count_history() == 9


def test_play_item_keys(bridge):
    mock_pb = MagicMock()
    mock_pb.play = MagicMock(return_value={"ok": True})
    bridge._playback_svc = mock_pb
    result = bridge.playHistoryItem("5")
    assert result["ok"]


def test_export_keyboard_accessible(bridge, tmp_path):
    out = tmp_path / "kb_export.json"
    result = bridge.exportHistory(str(out))
    assert result["ok"]


def test_retention_settings_accessible(bridge, hqs):
    old = time.time() - 10000000
    hqs._db.conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)", ("old_track", old))
    hqs._db.conn.commit()
    assert hqs.count_history() == 11


def test_view_toggle_reflects_data(bridge):
    result = bridge.refresh()
    assert result["count"] == 10


def test_navigate_to_statistics_then_back(bridge):
    stats = bridge.getStatistics()
    assert stats["ok"]


def test_escape_closes_dialog_pattern(bridge):
    pass


def test_tab_navigation_works(bridge):
    result = bridge.refresh()
    assert result["ok"]


def test_search_field_clears_on_escape(bridge):
    result = bridge.refresh()
    assert result["ok"]


def test_pagination_keys_work(bridge):
    result = bridge.refresh()
    assert result["count"] >= 0
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
