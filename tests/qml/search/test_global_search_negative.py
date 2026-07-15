"""Test GlobalSearchBridge negative cases: stale requests, empty results, error, null bridge."""
import pytest
"""Test negative/error cases for global search to ensure robustness."""
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Song", "subtitle": "Artist",
             "section": "Canciones", "score": 1.0},
        ],
        "count": 1,
    }
    return svc


class TestStaleRequestProtection:
    def test_stale_request_ignored(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge._request_counter = 1
        bridge._active_request_id = 100
        result = bridge.search("Fresh")
        assert result["ok"]

    def test_stale_result_not_applied_to_results(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("First")
        bridge._active_request_id = 9999
        bridge.search("Second")
        assert bridge.query == "Second"

    def test_generation_increment_on_each_search(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        gen1 = bridge._search_gen
        bridge.search("A")
        gen2 = bridge._search_gen
        bridge.search("B")
        gen3 = bridge._search_gen
        assert gen3 > gen2 > gen1

    def test_rapid_sequential_searches(self, mock_service):
        mock_calls = []
        def side_effect(q, owner="", timeout_ms=5000):
            mock_calls.append(q)
            return {"ok": True, "results": [
                {"type": "track", "id": 1, "title": q, "section": "Canciones"}
            ], "count": 1}
        mock_service.search.side_effect = side_effect
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("A")
        bridge.search("B")
        bridge.search("C")
        assert mock_calls[-1] == "C"


class TestEmptyResults:
    def test_search_no_results(self, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [], "count": 0
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("zzzznonexistent")
        assert result["ok"]
        assert len(bridge.results) == 0

    def test_search_no_results_clears_error(self, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [], "count": 0
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("nothing")
        assert bridge.errorCode == ""
        assert bridge.errorMessage == ""

    def test_empty_query_returns_empty_results(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0


class TestErrorState:
    def test_service_returns_error(self, mock_service):
        mock_service.search.return_value = {
            "ok": False, "error_code": "SEARCH_FAILED",
            "message": "Search engine unavailable"
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert not result.get("ok")
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_service_raises_exception(self, mock_service):
        mock_service.search.side_effect = RuntimeError("DB connection lost")
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert "error" in result
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_error_code_property(self, mock_service):
        mock_service.search.side_effect = Exception("Error")
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Test")
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_error_message_property(self, mock_service):
        mock_service.search.side_effect = Exception("DB error")
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Test")
        assert "error" in bridge.errorMessage.lower() or bridge.errorMessage != ""

    def test_error_after_success(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Good")
        assert bridge.errorCode == ""
        mock_service.search.side_effect = Exception("Fail")
        bridge.search("Bad")
        assert bridge.errorCode != ""


class TestNullBridge:
    def test_no_search_service(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.search("Test")
        assert not result["ok"]
        assert bridge.errorCode == "SERVICE_UNAVAILABLE"

    def test_no_service_cancel_still_ok(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.cancel()
        assert result["ok"]

    def test_no_service_search_empty_query(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0

    def test_no_service_no_error_on_empty_query(self):
        bridge = GlobalSearchBridge(search_service=None)
        bridge.search("")
        assert bridge.errorCode == ""

    def test_no_service_is_not_searching(self):
        bridge = GlobalSearchBridge(search_service=None)
        assert not bridge.isSearching

    def test_generation_monotonic(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        gens = []
        for i in range(10):
            bridge.search(str(i))
            gens.append(bridge._search_gen)
        for i in range(1, len(gens)):
            assert gens[i] >= gens[i - 1]
"""Test GlobalSearchBridge negative cases: stale requests, empty results, error, null bridge."""


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Song", "subtitle": "Artist",
             "section": "Canciones", "score": 1.0},
        ],
        "count": 1,
    }
    return svc


class TestStaleRequestProtection:
    def test_stale_request_ignored(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge._request_counter = 1
        bridge._active_request_id = 100
        result = bridge.search("Fresh")
        assert result["ok"]

    def test_stale_result_not_applied_to_results(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("First")
        bridge._active_request_id = 9999
        bridge.search("Second")
        assert bridge.query == "Second"

    def test_generation_increment_on_each_search(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        gen1 = bridge._search_gen
        bridge.search("A")
        gen2 = bridge._search_gen
        bridge.search("B")
        gen3 = bridge._search_gen
        assert gen3 > gen2 > gen1

    def test_rapid_sequential_searches(self, mock_service):
        mock_calls = []
        def side_effect(q, owner="", timeout_ms=5000):
            mock_calls.append(q)
            return {"ok": True, "results": [
                {"type": "track", "id": 1, "title": q, "section": "Canciones"}
            ], "count": 1}
        mock_service.search.side_effect = side_effect
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("A")
        bridge.search("B")
        bridge.search("C")
        assert mock_calls[-1] == "C"


class TestEmptyResults:
    def test_search_no_results(self, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [], "count": 0
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("zzzznonexistent")
        assert result["ok"]
        assert len(bridge.results) == 0

    def test_search_no_results_clears_error(self, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [], "count": 0
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("nothing")
        assert bridge.errorCode == ""
        assert bridge.errorMessage == ""

    def test_empty_query_returns_empty_results(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0


class TestErrorState:
    def test_service_returns_error(self, mock_service):
        mock_service.search.return_value = {
            "ok": False, "error_code": "SEARCH_FAILED",
            "message": "Search engine unavailable"
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert not result.get("ok")
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_service_raises_exception(self, mock_service):
        mock_service.search.side_effect = RuntimeError("DB connection lost")
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert "error" in result
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_error_code_property(self, mock_service):
        mock_service.search.side_effect = Exception("Error")
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Test")
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_error_message_property(self, mock_service):
        mock_service.search.side_effect = Exception("DB error")
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Test")
        assert "error" in bridge.errorMessage.lower() or bridge.errorMessage != ""

    def test_error_after_success(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Good")
        assert bridge.errorCode == ""
        mock_service.search.side_effect = Exception("Fail")
        bridge.search("Bad")
        assert bridge.errorCode != ""


class TestNullBridge:
    def test_no_search_service(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.search("Test")
        assert not result["ok"]
        assert bridge.errorCode == "SERVICE_UNAVAILABLE"

    def test_no_service_cancel_still_ok(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.cancel()
        assert result["ok"]

    def test_no_service_search_empty_query(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0

    def test_no_service_no_error_on_empty_query(self):
        bridge = GlobalSearchBridge(search_service=None)
        bridge.search("")
        assert bridge.errorCode == ""

    def test_no_service_is_not_searching(self):
        bridge = GlobalSearchBridge(search_service=None)
        assert not bridge.isSearching

    def test_no_service_cancel_then_search_empty(self):
        bridge = GlobalSearchBridge(search_service=None)
        bridge.cancel()
        result = bridge.search("")
        assert result["ok"]

    def test_no_service_search_returns_service_unavailable(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.search("Anything")
        assert not result["ok"]
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_no_service_results_empty(self):
        bridge = GlobalSearchBridge(search_service=None)
        bridge.search("Test")
        assert bridge.results == []

    def test_no_service_handles_gracefully(self):
        bridge = GlobalSearchBridge(search_service=None)
        assert bridge.query == ""
        assert not bridge.isSearching
        assert bridge.errorCode == ""
        assert bridge.results == []

    def test_no_service_cancel_clears_query_not(self):
        bridge = GlobalSearchBridge(search_service=None)
        bridge.search("Test")
        bridge.cancel()
        assert bridge.results == []

    def test_service_without_search_method(self):
        svc = MagicMock()
        del svc.search
        bridge = GlobalSearchBridge(search_service=svc)
        result = bridge.search("Test")
        assert not result["ok"]
        assert bridge.errorCode == "SERVICE_UNAVAILABLE"
