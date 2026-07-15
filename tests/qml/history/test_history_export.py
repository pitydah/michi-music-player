"""Tests for HistoryExportDialog: export flows, cancellation, format selection, edge cases."""
import pytest
from unittest.mock import MagicMock, patch

from ui_qml_bridge.history_bridge import HistoryBridge

pytestmark = [pytest.mark.qml_module("history")]


class TestHistoryExport:

    def test_export_json_format(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = [
            (1, "f1.mp3", "2024-01-01", "pc", "S1", "A1", "Al1")
        ]
        bridge = HistoryBridge(db=db)
        result = bridge.exportHistory("/tmp/test.json", "json")
        assert result["ok"] is True
        assert result["format"] == "json"
        assert result["count"] == 1

    def test_export_csv_format(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = [
            (1, "f1.mp3", "2024-01-01", "pc", "S1", "A1", "Al1")
        ]
        bridge = HistoryBridge(db=db)
        result = bridge.exportHistory("/tmp/test.csv", "csv")
        assert result["ok"] is True

    def test_export_empty_history(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = []
        bridge = HistoryBridge(db=db)
        result = bridge.exportHistory("/tmp/empty.json", "json")
        assert result["ok"] is True
        assert result["count"] == 0

    def test_export_empty_path(self):
        bridge = HistoryBridge()
        result = bridge.exportHistory("", "json")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_PATH"

    def test_cancel_export_removes_file(self):
        bridge = HistoryBridge()
        with patch("os.path.exists", return_value=True), patch("os.remove") as mock_remove:
            result = bridge.cancelExport("job1", "/tmp/test.json")
            assert result["ok"] is True
            assert result["cancelled"] is True
            mock_remove.assert_called_once_with("/tmp/test.json")

    def test_cancel_export_no_file(self):
        bridge = HistoryBridge()
        with patch("os.path.exists", return_value=False):
            result = bridge.cancelExport("job1", "")
            assert result["ok"] is True

    def test_export_with_service(self):
        hqs = MagicMock()
        hqs.export_history.return_value = {"ok": True, "count": 5}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.exportHistory("/tmp/svc.json", "json")
        assert result["ok"] is True
        hqs.export_history.assert_called_once_with("/tmp/svc.json", "json")

    def test_export_service_error(self):
        hqs = MagicMock()
        hqs.export_history.return_value = {"ok": False, "error": "WRITE_FAILED"}
        bridge = HistoryBridge(history_query_service=hqs)
        result = bridge.exportHistory("/tmp/fail.json", "json")
        assert result["ok"] is False
        assert result["error"] == "WRITE_FAILED"

    def test_cancel_export_by_id(self):
        bridge = HistoryBridge()
        result = bridge.cancelExport("job_42", "")
        assert result["ok"] is True

    def test_export_none_db_error(self):
        bridge = HistoryBridge(db=None)
        result = bridge.exportHistory("/tmp/none.json", "json")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_PATH"

    def test_export_formats_case_sensitive(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = []
        bridge = HistoryBridge(db=db)
        result_json = bridge.exportHistory("/tmp/t.json", "JSON")
        assert result_json["ok"] is True
        result_csv = bridge.exportHistory("/tmp/t.csv", "CSV")
        assert result_csv["ok"] is True
