"""Tests for HistoryPage: bridge interactions, state transitions, filters, views."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.history_bridge import HistoryBridge

pytestmark = [pytest.mark.qml_module("history")]


class TestHistoryPage:

    def test_bridge_default_state(self):
        bridge = HistoryBridge()
        assert bridge.historyModel is not None
        assert bridge.historyCount == 0
        assert bridge.historyQueryService is None

    def test_bridge_refresh(self):
        bridge = HistoryBridge()
        result = bridge.refresh()
        assert result["ok"] is True

    def test_bridge_refresh_with_db(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = []
        bridge = HistoryBridge(db=db)
        result = bridge.refresh()
        assert result["ok"] is True

    def test_bridge_remove_item_no_db(self):
        bridge = HistoryBridge()
        result = bridge.removeHistoryItem("42")
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_bridge_remove_item_with_db(self):
        db = MagicMock()
        bridge = HistoryBridge(db=db)
        result = bridge.removeHistoryItem("42")
        assert result["ok"] is True

    def test_bridge_remove_event_no_service(self):
        bridge = HistoryBridge()
        result = bridge.removeHistoryEvent("42")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_bridge_remove_event_with_service(self):
        hqs = MagicMock()
        hqs.remove_event_by_id.return_value = {"ok": True}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.removeHistoryEvent("42")
        assert result["ok"] is True

    def test_bridge_clear_no_db(self):
        bridge = HistoryBridge()
        result = bridge.clearHistory()
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_bridge_clear_with_db(self):
        db = MagicMock()
        bridge = HistoryBridge(db=db)
        result = bridge.clearHistory()
        assert result["ok"] is True

    def test_bridge_play_no_playback(self):
        bridge = HistoryBridge()
        result = bridge.playHistoryItem("42")
        assert result["ok"] is False
        assert result["error"] == "NO_PLAYBACK"

    def test_bridge_play_with_playback(self):
        playback = MagicMock()
        playback.play.return_value = {"ok": True}
        bridge = HistoryBridge(playback_service=playback)
        result = bridge.playHistoryItem("42")
        assert result["ok"] is True

    def test_bridge_get_statistics_no_db(self):
        bridge = HistoryBridge()
        result = bridge.getStatistics()
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_bridge_get_statistics_with_db(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [42]
        bridge = HistoryBridge(db=db)
        result = bridge.getStatistics()
        assert result["ok"] is True
        assert result["total_plays"] == 42

    def test_bridge_export_no_db(self):
        bridge = HistoryBridge()
        result = bridge.exportHistory("/tmp/test.json", "json")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_PATH"

    def test_bridge_export_with_db(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = [
            (1, "file1.mp3", "2024-01-01", "pc", "Song", "Artist", "Album")
        ]
        bridge = HistoryBridge(db=db)
        result = bridge.exportHistory("/tmp/test.json", "json")
        assert result["ok"] is True
        assert result["count"] == 1

    def test_bridge_cancel_export(self):
        bridge = HistoryBridge()
        result = bridge.cancelExport("job1", "/tmp/test.json")
        assert result["ok"] is True
        assert result["cancelled"] is True

    def test_bridge_apply_retention_no_service(self):
        bridge = HistoryBridge()
        result = bridge.applyRetention('{"max_age_days": 90}')
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_bridge_apply_retention_with_service(self):
        hqs = MagicMock()
        hqs.apply_retention.return_value = {"ok": True, "deleted_count": 10}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.applyRetention('{"max_age_days": 90}')
        assert result["ok"] is True
        assert result["deleted_count"] == 10

    def test_bridge_apply_retention_empty_config(self):
        hqs = MagicMock()
        hqs.apply_retention.return_value = {"ok": True, "deleted_count": 5}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.applyRetention("")
        assert result["ok"] is True

    def test_bridge_set_history_enabled(self):
        hqs = MagicMock()
        hqs.set_history_enabled.return_value = {"ok": True}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.setHistoryEnabled(True)
        assert result["ok"] is True

    def test_bridge_set_history_limit(self):
        hqs = MagicMock()
        hqs.set_history_limit.return_value = {"ok": True}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.setHistoryLimit(5000)
        assert result["ok"] is True

    def test_bridge_playback_bridge_property(self):
        bridge = HistoryBridge()
        assert bridge.playbackBridge is None
        mock_pb = MagicMock()
        bridge.setPlaybackBridge(mock_pb)
        assert bridge.playbackBridge is mock_pb
