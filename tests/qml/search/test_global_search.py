import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1, "results": []
    }
    return svc


@pytest.fixture
def mock_query_executor():
    qe = MagicMock()
    qe.submit = MagicMock(return_value=42)
    qe.cancel_owner = MagicMock()
    return qe


@pytest.fixture
def bridge(mock_service, mock_query_executor):
    return GlobalSearchBridge(
        search_service=mock_service,
        query_executor=mock_query_executor,
    )


class TestGlobalSearch:

    def test_search_returns_results(self, bridge, mock_query_executor, mock_service):
        mock_service.search.return_value = {
            "ok": True, "request_id": 1, "results": [
                {"section": "track", "title": "A"},
                {"section": "album", "title": "B"},
                {"section": "artist", "title": "C"},
                {"section": "playlist", "title": "D"},
                {"section": "track", "title": "E"},
            ]
        }
        bridge._active_request_id = 1
        bridge._on_search_done(mock_service.search.return_value, 1)
        assert len(bridge.results) == 5

    def test_search_whitespace_query_returns_empty(self, bridge, mock_query_executor):
        result = bridge.search("   ")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0

    def test_searching_state_during_search(self, bridge):
        assert not bridge.isSearching
        bridge.search("Test")
        assert bridge.isSearching

    def test_search_generation_increments(self, bridge):
        gen1 = bridge._search_gen
        bridge.search("First")
        gen2 = bridge._search_gen
        bridge.search("Second")
        gen3 = bridge._search_gen
        assert gen2 > gen1
        assert gen3 > gen2

    def test_query_property_updated(self, bridge):
        assert bridge.query == ""
        bridge.search("Hello World")
        assert bridge.query == "Hello World"

    def test_results_property_initial_empty(self, bridge):
        assert bridge.results == []

    def test_error_code_empty_on_success(self, bridge):
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": True, "results": []}, 1)
        assert bridge.errorCode == ""

    def test_error_message_empty_on_success(self, bridge):
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": True, "results": []}, 1)
        assert bridge.errorMessage == ""

    def test_multiple_sections_in_results(self, bridge, mock_service):
        mock_service.search.return_value = {
            "ok": True, "request_id": 1, "results": [
                {"section": "track", "title": "A"},
                {"section": "album", "title": "B"},
                {"section": "artist", "title": "C"},
                {"section": "playlist", "title": "D"},
            ]
        }
        bridge._active_request_id = 1
        bridge._on_search_done(mock_service.search.return_value, 1)
        sections = set()
        for r in bridge.results:
            sections.add(r["section"])
        assert len(sections) >= 4

    def test_search_domain_track(self, bridge, mock_query_executor):
        result = bridge.searchDomain("tracks", "genesis")
        assert result.get("async") is True

    def test_search_domain_unknown(self, bridge, mock_query_executor):
        result = bridge.searchDomain("unknown_domain", "query")
        assert result.get("async") is True

    def test_cancel_search(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert not bridge.isSearching
        assert len(bridge.results) == 0

    def test_empty_bridge_defaults(self):
        b = GlobalSearchBridge()
        assert b._svc is None
        assert b._qe is None
        assert b._query == ""
        assert b.results == []
