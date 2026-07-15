"""Test GlobalSearchBridge integration with GlobalSearchService (no direct db.conn)."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
pytestmark = [pytest.mark.qml_module("global_search")]


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
def mock_qe():
    qe = MagicMock()
    qe.submit = MagicMock(return_value=42)
    qe.cancel_owner = MagicMock()
    return qe


@pytest.fixture
def bridge(mock_service, mock_qe):
    return GlobalSearchBridge(search_service=mock_service, query_executor=mock_qe)


def test_search_returns_results(bridge, mock_service):
    mock_service.search.return_value = {
        "ok": True, "results": [
            {"type": "track", "id": 1, "title": "Test Song", "subtitle": "Artist · Album",
             "section": "Canciones", "score": 1.0},
        ],
        "count": 1,
    }
    bridge._active_request_id = 1
    bridge._on_search_done(mock_service.search.return_value, 1)
    assert len(bridge.results) > 0


def test_search_empty_query(bridge):
    result = bridge.search("")
    assert result["ok"]
    assert result["count"] == 0


def test_searching_state(bridge):
    assert not bridge.isSearching
    bridge.search("Test")
    assert bridge.isSearching
    bridge._active_request_id = 1
    bridge._on_search_done({"ok": True, "results": []}, 1)
    assert not bridge.isSearching


def test_error_code_on_failure(bridge, mock_service):
    mock_service.search.side_effect = Exception("DB error")
    bridge.search("Test")


def test_cancel_search(bridge):
    result = bridge.cancel()
    assert result["ok"]


def test_multiple_searches_generation(bridge):
    bridge.search("First")
    first_gen = bridge._search_gen
    bridge.search("Second")
    assert bridge._search_gen > first_gen


def test_stale_result_ignored(bridge):
    bridge._search_gen = 100
    bridge._query = "Stale"
    bridge.search("Fresh")
    assert bridge._query == "Fresh"


def test_no_search_service():
    qe = MagicMock()
    qe.submit = MagicMock(return_value=42)
    bridge = GlobalSearchBridge(search_service=None, query_executor=qe)
    bridge.search("Test")


def test_execute_result_action_navigate(bridge):
    bridge._results = [{"id": "1", "type": "track", "route": "library"}]
    bridge._navigation = MagicMock()
    result = bridge.executeResultAction("1", "navigate")
    assert result["ok"]
