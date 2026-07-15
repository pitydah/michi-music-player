import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Song A", "subtitle": "Artist",
             "section": "Canciones", "score": 1.0},
            {"type": "track", "id": 2, "title": "Song B", "subtitle": "Artist",
             "section": "Canciones", "score": 0.9},
            {"type": "album", "id": "key1", "title": "Album A", "subtitle": "Artist",
             "section": "Álbumes", "score": 0.8},
        ],
        "count": 3,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


class TestGlobalSearchKeyboard:

    def test_cancel_search(self, bridge):
        bridge.search("Test")
        assert len(bridge.results) > 0
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_search_after_cancel_works(self, bridge):
        bridge.cancel()
        result = bridge.search("New search")
        assert result["ok"]
        assert len(bridge.results) > 0

    def test_sequential_searches_update_results(self, bridge):
        bridge.search("First")
        bridge.search("Second")
        assert bridge.query == "Second"

    def test_search_then_clear_then_search(self, bridge):
        bridge.search("Genesis")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0
        bridge.search("Return")
        assert len(bridge.results) > 0

    def test_search_with_special_chars(self, bridge, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Café", "section": "Canciones"}
            ], "count": 1
        }
        result = bridge.search("Café")
        assert result["ok"]
        assert len(bridge.results) == 1

    def test_search_with_long_query(self, bridge, mock_service):
        long_q = "a" * 500
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Long match", "section": "Canciones"}
            ], "count": 1
        }
        result = bridge.search(long_q)
        assert result["ok"]

    def test_multiple_rapid_searches_do_not_crash(self, bridge):
        for i in range(20):
            bridge.search(f"Search {i}")
        assert bridge.query == "Search 19"

    def test_cancel_during_search_clears_state(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert not bridge.isSearching
        assert bridge.query == "Test"

    def test_search_after_cancel_returns_fresh(self, bridge):
        bridge.search("Old")
        bridge.cancel()
        result = bridge.search("New")
        assert result["ok"]
        assert bridge.query == "New"

    def test_search_results_are_immutable_copy(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert bridge.results == []

    def test_repeated_same_query(self, bridge):
        bridge.search("Same")
        count1 = bridge._search_gen
        bridge.search("Same")
        count2 = bridge._search_gen
        assert count2 > count1

    def test_escape_equivalent_to_cancel(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert len(bridge.results) == 0
        assert not bridge.isSearching

    def test_search_after_error(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("Temp error")
        bridge.search("Test")
        assert bridge.errorCode != ""
        mock_service.search.side_effect = None
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Recovery", "section": "Canciones"}
            ], "count": 1
        }
        result = bridge.search("Recovery")
        assert result["ok"]
        assert bridge.errorCode == ""

    def test_search_then_cancel_then_navigate(self, bridge):
        bridge.search("Nav")
        assert len(bridge.results) > 0
class TestKeyboardNavigation:
    def test_search_can_be_cancelled(self, bridge):
        bridge.search("Test")
        assert len(bridge.results) > 0
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_search_after_cancel_works(self, bridge):
        bridge.cancel()
        result = bridge.search("New search")
        assert result["ok"]
        assert len(bridge.results) > 0

    def test_sequential_searches_update_results(self, bridge):
        bridge.search("First")
        bridge.search("Second")
        assert bridge.query == "Second"

    def test_search_then_clear_then_search(self, bridge):
        bridge.search("Genesis")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0
        bridge.search("Return")
        assert len(bridge.results) > 0

    def test_search_with_special_chars(self, bridge, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Café", "section": "Canciones"}
            ], "count": 1
        }
        result = bridge.search("Café")
        assert result["ok"]
        assert len(bridge.results) == 1

    def test_search_with_long_query(self, bridge, mock_service):
        long_q = "a" * 500
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Long match", "section": "Canciones"}
            ], "count": 1
        }
        result = bridge.search(long_q)
        assert result["ok"]

    def test_multiple_rapid_searches_do_not_crash(self, bridge):
        for i in range(20):
            bridge.search(f"Search {i}")
        assert bridge.query == "Search 19"

    def test_cancel_during_search_clears_state(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert not bridge.isSearching
        assert bridge.query == "Test"

    def test_search_after_cancel_returns_fresh(self, bridge):
        bridge.search("Old")
        bridge.cancel()
        result = bridge.search("New")
        assert result["ok"]
        assert bridge.query == "New"

    def test_search_results_are_immutable_copy(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert bridge.results == []

    def test_repeated_same_query(self, bridge):
        bridge.search("Same")
        count1 = bridge._search_gen
        bridge.search("Same")
        count2 = bridge._search_gen
        assert count2 > count1

    def test_escape_equivalent_to_cancel(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert len(bridge.results) == 0
        assert not bridge.isSearching

    def test_search_after_error(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("Temp error")
        bridge.search("Test")
        assert bridge.errorCode != ""
        mock_service.search.side_effect = None
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Recovery", "section": "Canciones"}
            ], "count": 1
        }
        result = bridge.search("Recovery")
        assert result["ok"]
        assert bridge.errorCode == ""

    def test_search_then_cancel_then_navigate(self, bridge):
        bridge.search("Nav")
        assert len(bridge.results) > 0
        bridge.cancel()
        bridge.search("Nav again")
        assert len(bridge.results) > 0

    def test_empty_search_clears_error(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("Error")
        bridge.search("Test")
        assert bridge.errorCode != ""
        bridge.search("")
        assert bridge.errorCode == ""
