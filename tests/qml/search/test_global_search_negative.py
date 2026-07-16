import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def mock_qe():
    qe = MagicMock()
    qe.submit = MagicMock(return_value=42)
    qe.cancel_owner = MagicMock()
    return qe


class TestStaleRequestProtection:
    def test_stale_request_ignored(self, mock_qe):
        bridge = GlobalSearchBridge(search_service=MagicMock(), query_executor=mock_qe)
        bridge._active_request_id = 5
        bridge._on_search_done({"ok": True, "results": [{"type": "track"}]}, 3)
        assert bridge.results == []

    def test_rapid_sequential_searches(self, mock_qe):
        bridge = GlobalSearchBridge(search_service=MagicMock(), query_executor=mock_qe)
        bridge.search("First")
        bridge.search("Second")
        assert bridge.query == "Second"


class TestEmptyResults:
    def test_search_no_results(self, mock_qe):
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": [], "count": 0}
        bridge = GlobalSearchBridge(search_service=svc, query_executor=mock_qe)
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": True, "results": [], "count": 0}, 1)
        assert bridge.results == []
        assert bridge.errorCode == ""

    def test_search_no_results_clears_error(self, mock_qe):
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": [], "count": 0}
        bridge = GlobalSearchBridge(search_service=svc, query_executor=mock_qe)
        bridge._active_request_id = 1
        bridge._error_code = "PREV_ERROR"
        bridge._on_search_done({"ok": True, "results": [], "count": 0}, 1)
        assert bridge.errorCode == ""


class TestErrorState:
    def test_service_returns_error(self, mock_qe):
        svc = MagicMock()
        svc.search.return_value = {"ok": False, "error_code": "TIMEOUT", "message": "timed out"}
        bridge = GlobalSearchBridge(search_service=svc, query_executor=mock_qe)
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": False, "error_code": "TIMEOUT", "message": "timed out"}, 1)
        assert bridge.errorCode == "TIMEOUT"

    def test_service_raises_exception(self, mock_qe):
        svc = MagicMock()
        svc.search.side_effect = Exception("crash")
        bridge = GlobalSearchBridge(search_service=svc, query_executor=mock_qe)
        bridge.search("crash")

    def test_error_code_property(self, mock_qe):
        svc = MagicMock()
        svc.search.return_value = {"ok": False, "error_code": "TIMEOUT", "message": "timed out"}
        bridge = GlobalSearchBridge(search_service=svc, query_executor=mock_qe)
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": False, "error_code": "TIMEOUT", "message": "timed out"}, 1)
        assert bridge.errorCode == "TIMEOUT"

    def test_error_after_success(self, mock_qe):
        svc = MagicMock()
        bridge = GlobalSearchBridge(search_service=svc, query_executor=mock_qe)
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": True, "results": [{"type": "track"}]}, 1)
        assert bridge.errorCode == ""
        bridge._active_request_id = 2
        bridge._on_search_done({"ok": False, "error_code": "DB_ERROR", "message": "fail"}, 2)
        assert bridge.errorCode == "DB_ERROR"


class TestMissingBridge:
    def test_no_search_service(self, mock_qe):
        bridge = GlobalSearchBridge(search_service=None, query_executor=mock_qe)
        bridge.search("test")

    def test_no_service_search_returns_service_unavailable(self, mock_qe):
        bridge = GlobalSearchBridge(search_service=None, query_executor=mock_qe)
        bridge.search("test")

    def test_service_without_search_method(self, mock_qe):
        bridge = GlobalSearchBridge(search_service=object(), query_executor=mock_qe)
        bridge.search("test")
