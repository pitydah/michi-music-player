"""Tests for History v12 — event ID, pagination, filters, export, cancel export."""
from unittest.mock import MagicMock

import pytest


class TestHistoryBridgeCreation:
    def test_requires_db(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        with pytest.raises(Exception):
            HistoryBridge()

    def test_creation_with_db(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock())
        assert hb is not None

    def test_has_model(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock())
        assert hb.historyModel is not None

    def test_history_count_default(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock())
        assert hb.historyCount >= 0


class TestHistoryOperations:
    def test_refresh(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock())
        result = hb.refresh()
        assert result.get("ok")

    def test_fetch_page(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock(), history_query_service=MagicMock())
        result = hb.fetchPage(0, 50)
        assert isinstance(result, dict)

    def test_clear_history(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hqs = MagicMock()
        hqs.clear_history.return_value = {"ok": True}
        hb = HistoryBridge(db=MagicMock(), history_query_service=hqs)
        result = hb.clearHistory()
        assert isinstance(result, dict)

    def test_remove_event(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hqs = MagicMock()
        hqs.remove_event_by_id.return_value = {"ok": True}
        hb = HistoryBridge(db=MagicMock(), history_query_service=hqs)
        result = hb.removeHistoryEvent("123")
        assert isinstance(result, dict)

    def test_export_history(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hqs = MagicMock()
        hqs.export_history.return_value = {"ok": True}
        hb = HistoryBridge(db=MagicMock(), history_query_service=hqs)
        result = hb.exportHistory("/test/history.json", "json")
        assert isinstance(result, dict)

    def test_cancel_export(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock())
        result = hb.cancelExport("export_123", "/test/history.json")
        assert result.get("ok")

    def test_apply_retention(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hqs = MagicMock()
        hqs.apply_retention.return_value = {"ok": True}
        hb = HistoryBridge(db=MagicMock(), history_query_service=hqs)
        result = hb.applyRetention('{"max_age_days": 90}')
        assert isinstance(result, dict)

    def test_get_statistics(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hqs = MagicMock()
        hqs.get_statistics.return_value = {"ok": True}
        hb = HistoryBridge(db=MagicMock(), history_query_service=hqs)
        result = hb.getStatistics()
        assert isinstance(result, dict)

    def test_score(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=MagicMock())
        score = hb.historyScore()
        assert isinstance(score, dict)
        assert "score" in score
