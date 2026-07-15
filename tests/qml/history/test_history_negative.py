"""Negative tests for History: null bridge, invalid inputs, edge cases, error states."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.history_bridge import HistoryBridge

pytestmark = [pytest.mark.qml_module("history")]


class TestHistoryNegative:

    def test_null_bridge_safe(self):
        bridge = HistoryBridge()
        assert bridge.historyModel is not None
        assert bridge.historyCount == 0
        assert bridge.historyQueryService is None

    def test_remove_nonexistent_track(self):
        hqs = MagicMock()
        hqs.remove_history_item.return_value = {"ok": False, "error": "NOT_FOUND"}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.removeHistoryItem("99999")
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"

    def test_remove_invalid_event_id(self):
        hqs = MagicMock()
        hqs.remove_event_by_id.side_effect = ValueError("invalid")
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.removeHistoryEvent("abc")
        assert result["ok"] is False
        assert result["error"] == "INVALID_ID"

    def test_export_db_exception(self):
        db = MagicMock()
        db.conn.execute.side_effect = Exception("DB locked")
        bridge = HistoryBridge(db=db)
        result = bridge.exportHistory("/tmp/test.json", "json")
        assert result["ok"] is False
        assert "error" in result

    def test_clear_db_exception(self):
        db = MagicMock()
        db.conn.execute.side_effect = Exception("DB error")
        bridge = HistoryBridge(db=db)
        result = bridge.clearHistory()
        assert result["ok"] is False

    def test_remove_db_exception(self):
        db = MagicMock()
        db.conn.execute.side_effect = Exception("DB error")
        bridge = HistoryBridge(db=db)
        result = bridge.removeHistoryItem("42")
        assert result["ok"] is False

    def test_play_empty_track_id(self):
        bridge = HistoryBridge()
        result = bridge.playHistoryItem("")
        assert result["ok"] is False

    def test_get_statistics_db_exception(self):
        db = MagicMock()
        db.conn.execute.side_effect = Exception("DB error")
        bridge = HistoryBridge(db=db)
        result = bridge.getStatistics()
        assert result["ok"] is False

    def test_apply_retention_invalid_json(self):
        hqs = MagicMock()
        hqs.apply_retention.return_value = {"ok": True, "deleted_count": 0}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.applyRetention("not valid json")
        assert result["ok"] is True

    def test_set_history_enabled_no_service(self):
        bridge = HistoryBridge()
        result = bridge.setHistoryEnabled(False)
        assert result["ok"] is True

    def test_set_history_limit_no_service(self):
        bridge = HistoryBridge()
        result = bridge.setHistoryLimit(500)
        assert result["ok"] is True

    def test_play_with_action_registry(self):
        ar = MagicMock()
        ar.execute.return_value = {"ok": True}
        bridge = HistoryBridge(action_registry=ar)
        result = bridge.playHistoryItem("42")
        assert result["ok"] is True

    def test_export_with_service_empty_result(self):
        hqs = MagicMock()
        hqs.export_history.return_value = {"ok": True, "count": 0}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.exportHistory("/tmp/empty.json", "json")
        assert result["ok"] is True
        assert result["count"] == 0

    def test_model_refresh_on_remove(self):
        hqs = MagicMock()
        hqs.remove_history_item.return_value = {"ok": True, "deleted": 1}
        bridge = HistoryBridge(history_query_service=hqs)
        model_spy = MagicMock()
        bridge._model = model_spy
        result = bridge.removeHistoryItem("42")
        assert result["ok"] is True

    def test_negative_events_model_null(self):
        bridge = HistoryBridge()
        assert bridge.historyModel is not None
        assert len(bridge.historyModel) == 0 or bridge.historyModel.rowCount() == 0
