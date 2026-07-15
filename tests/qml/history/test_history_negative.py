"""Test history negative paths: missing service, empty history, export cancellation."""
"""Negative tests for History: null bridge, invalid inputs, edge cases, error states."""
import pytest

from ui_qml_bridge.history_bridge import HistoryBridge


def test_bridge_without_db_or_service():
    bridge = HistoryBridge(db=None, history_query_service=None)
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 0


def test_remove_history_item_no_db(bridge_no_db):
    result = bridge_no_db.removeHistoryItem("1")
    assert not result["ok"]


def test_remove_history_event_no_service(bridge_no_db):
    result = bridge_no_db.removeHistoryEvent("1")
    assert not result["ok"]


def test_clear_history_no_db(bridge_no_db):
    result = bridge_no_db.clearHistory()
    assert not result["ok"]


def test_export_no_db_no_service(bridge_no_db, tmp_path):
    out = tmp_path / "fail.json"
    result = bridge_no_db.exportHistory(str(out))
    assert not result["ok"]
    assert result["error"] == "NO_DB"


def test_play_item_no_backend(bridge_no_db):
    result = bridge_no_db.playHistoryItem("1")
    assert not result["ok"]


def test_statistics_no_db(bridge_no_db):
    result = bridge_no_db.getStatistics()
    assert not result["ok"]


def test_export_empty_path_no_bridge(bridge_no_db):
    result = bridge_no_db.exportHistory("")
    assert not result["ok"]


def test_apply_retention_no_service(bridge_no_db):
    result = bridge_no_db.applyRetention('{"max_age_days": 30}')
    assert not result["ok"]

    def test_negative_events_model_null(self):
        bridge = HistoryBridge()
        assert bridge.historyModel is not None
        assert len(bridge.historyModel) == 0 or bridge.historyModel.rowCount() == 0
"""Test history negative paths: missing service, empty history, export cancellation."""



def test_bridge_without_db_or_service():
    bridge = HistoryBridge(db=None, history_query_service=None)
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 0


def test_remove_history_item_no_db(bridge_no_db):
    result = bridge_no_db.removeHistoryItem("1")
    assert not result["ok"]


def test_remove_history_event_no_service(bridge_no_db):
    result = bridge_no_db.removeHistoryEvent("1")
    assert not result["ok"]


def test_clear_history_no_db(bridge_no_db):
    result = bridge_no_db.clearHistory()
    assert not result["ok"]


def test_export_no_db_no_service(bridge_no_db, tmp_path):
    out = tmp_path / "fail.json"
    result = bridge_no_db.exportHistory(str(out))
    assert not result["ok"]
    assert result["error"] == "NO_DB"


def test_play_item_no_backend(bridge_no_db):
    result = bridge_no_db.playHistoryItem("1")
    assert not result["ok"]


def test_statistics_no_db(bridge_no_db):
    result = bridge_no_db.getStatistics()
    assert not result["ok"]


def test_export_empty_path_no_bridge(bridge_no_db):
    result = bridge_no_db.exportHistory("")
    assert not result["ok"]


def test_apply_retention_no_service(bridge_no_db):
    result = bridge_no_db.applyRetention('{"max_age_days": 30}')
    assert not result["ok"]


def test_empty_history_display(bridge_empty):
    result = bridge_empty.refresh()
    assert result["ok"]
    assert result["count"] == 0


def test_remove_from_empty_history(bridge_empty):
    result = bridge_empty.removeHistoryItem("1")
    assert not result["ok"]


def test_clear_empty_history(bridge_empty):
    result = bridge_empty.clearHistory()
    assert not result["ok"]
    assert result["error"] == "NO_DB"


def test_export_empty_history_fails(bridge_empty, tmp_path):
    out = tmp_path / "empty_export.json"
    result = bridge_empty.exportHistory(str(out))
    assert not result["ok"]


def test_export_cancel_partial_file(bridge_empty, tmp_path):
    out = tmp_path / "partial.json"
    with open(str(out), "w") as f:
        f.write("partial data")
    result = bridge_empty.cancelExport("test", str(out))
    assert result["ok"]
    assert result["cancelled"]
    assert not out.exists()


def test_export_cancel_no_file(bridge_empty):
    result = bridge_empty.cancelExport("test")
    assert result["ok"]
    assert result["cancelled"]


def test_set_history_enabled_no_service(bridge_no_db):
    result = bridge_no_db.setHistoryEnabled(False)
    assert result["ok"]


def test_set_history_limit_no_service(bridge_no_db):
    result = bridge_no_db.setHistoryLimit(100)
    assert result["ok"]


def test_bridge_refresh_called_multiple_times(bridge_no_db):
    for _ in range(5):
        result = bridge_no_db.refresh()
        assert result["ok"]


@pytest.fixture
def bridge_no_db():
    return HistoryBridge(db=None, history_query_service=None)


@pytest.fixture
def bridge_empty():
    return HistoryBridge(db=None, history_query_service=None)
