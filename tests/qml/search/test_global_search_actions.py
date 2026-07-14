"""Test GlobalSearchBridge integration with GlobalSearchService (no direct db.conn)."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Test Song", "subtitle": "Artist · Album",
             "section": "Canciones", "score": 1.0},
        ],
        "count": 1,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


def test_search_returns_results(bridge):
    result = bridge.search("Test")
    assert result["ok"]
    assert len(bridge.results) > 0


def test_search_empty_query(bridge):
    result = bridge.search("")
    assert result["ok"]
    assert result["count"] == 0
    assert len(bridge.results) == 0


def test_searching_state(bridge):
    assert not bridge.isSearching
    bridge.search("Test")
    assert not bridge.isSearching


def test_error_code_on_failure(bridge, mock_service):
    mock_service.search.side_effect = Exception("DB error")
    result = bridge.search("Test")
    assert "error" not in result or not result.get("ok")


def test_cancel_search(bridge):
    result = bridge.cancel()
    assert result["ok"]


def test_multiple_searches_generation(bridge):
    bridge.search("First")
    first_gen = bridge._search_gen
    bridge.search("Second")
    assert bridge._search_gen > first_gen


def test_stale_result_ignored(bridge, mock_service):
    bridge._search_gen = 100
    bridge._query = "Stale"
    bridge.search("Fresh")
    assert bridge._query == "Fresh"


def test_no_search_service():
    bridge = GlobalSearchBridge(search_service=None)
    result = bridge.search("Test")
    assert result.get("ok")
    assert result.get("count") == 0


def test_results_property(bridge):
    assert bridge.results == []


def test_query_property(bridge):
    bridge.search("Hello")
    assert bridge.query == "Hello"
