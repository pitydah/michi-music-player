"""Workflow test: filter → play → export → remove via HistoryBridge."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.history_bridge import HistoryBridge

pytestmark = [pytest.mark.qml_module("history"), pytest.mark.qml_workflow("history")]


@pytest.fixture
def mock_db():
    db = MagicMock()
    rows = [
        (1, "file1.mp3", "2024-06-01 10:00", "pc", "Song A", "Artist X", "Album 1"),
        (2, "file2.mp3", "2024-06-02 11:00", "mobile", "Song B", "Artist Y", "Album 2"),
        (3, "file3.mp3", "2024-06-03 12:00", "pc", "Song C", "Artist X", "Album 1"),
        (4, "file4.mp3", "2024-06-04 13:00", "tablet", "Song D", "Artist Z", "Album 3"),
        (5, "file5.mp3", "2024-06-05 14:00", "pc", "Song E", "Artist X", "Album 1"),
    ]
    db.conn.execute.return_value.fetchall.return_value = rows
    db.conn.execute.return_value.fetchone.return_value = [5]
    return db


@pytest.fixture
def bridge(mock_db):
    playback = MagicMock()
    playback.play.return_value = {"ok": True}
    return HistoryBridge(db=mock_db, playback_service=playback)


class TestHistoryWorkflow:

    def test_wf_filter_then_play(self, bridge):
        bridge.refresh()
        assert bridge.historyCount == 5
        play_result = bridge.playHistoryItem("1")
        assert play_result["ok"] is True

    def test_wf_filter_then_remove_one(self, bridge):
        bridge.refresh()
        result = bridge.removeHistoryItem("1")
        assert result["ok"] is True

    def test_wf_filter_then_export_json(self, bridge):
        bridge.refresh()
        export_result = bridge.exportHistory("/tmp/history_export.json", "json")
        assert export_result["ok"] is True
        assert export_result["count"] == 5

    def test_wf_filter_then_export_csv(self, bridge):
        bridge.refresh()
        export_result = bridge.exportHistory("/tmp/history_export.csv", "csv")
        assert export_result["ok"] is True

    def test_wf_full_cycle(self, bridge):
        bridge.refresh()
        assert bridge.historyCount == 5
        play_result = bridge.playHistoryItem("3")
        assert play_result["ok"] is True
        result = bridge.removeHistoryItem("3")
        assert result["ok"] is True
        bridge.refresh()
        stats = bridge.getStatistics()
        assert stats["ok"] is True

    def test_wf_filter_then_clear(self, bridge):
        bridge.refresh()
        result = bridge.clearHistory()
        assert result["ok"] is True

    def test_wf_remove_then_play_then_export(self, bridge):
        bridge.refresh()
        bridge.removeHistoryItem("1")
        bridge.removeHistoryItem("2")
        bridge.playHistoryItem("3")
        export_result = bridge.exportHistory("/tmp/wf_export.json", "json")
        assert export_result["ok"] is True

    def test_wf_export_then_cancel(self, bridge):
        bridge.refresh()
        export_result = bridge.exportHistory("/tmp/cancel_test.json", "json")
        assert export_result["ok"] is True
        cancel_result = bridge.cancelExport("job_1", "/tmp/cancel_test.json")
        assert cancel_result["ok"] is True

    def test_wf_apply_retention_then_refresh(self, bridge):
        bridge.refresh()
        hqs = MagicMock()
        hqs.apply_retention.return_value = {"ok": True, "deleted_count": 3}
        bridge._hqs = hqs
        result = bridge.applyRetention('{"max_age_days": 30}')
        assert result["ok"] is True
        assert result["deleted_count"] == 3

    def test_wf_statistics_after_actions(self, bridge):
        bridge.refresh()
        bridge.removeHistoryItem("1")
        bridge.removeHistoryItem("5")
        stats = bridge.getStatistics()
        assert stats["ok"] is True
        assert stats["total_plays"] == 5
