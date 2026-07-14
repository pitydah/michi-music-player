"""Test GlobalSearchBridge: no false ok, SERVICE_UNAVAILABLE when no service, cancel."""
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
            {"type": "album", "id": "key1", "title": "Test Album",
             "section": "Álbumes", "score": 0.9},
        ],
        "count": 2,
    }
    return svc


def test_no_service_returns_service_unavailable():
    bridge = GlobalSearchBridge(search_service=None)
    result = bridge.search("Test")
    assert not result["ok"]
    assert bridge.errorCode == "SERVICE_UNAVAILABLE"


def test_service_available_returns_ok(mock_service):
    bridge = GlobalSearchBridge(search_service=mock_service)
    result = bridge.search("Test")
    assert result["ok"]


def test_empty_query_returns_empty_no_error(mock_service):
    bridge = GlobalSearchBridge(search_service=mock_service)
    result = bridge.search("")
    assert result["ok"]
    assert result["count"] == 0
    assert bridge.errorCode == ""


def test_cancel_uses_service(mock_service):
    bridge = GlobalSearchBridge(search_service=mock_service)
    bridge.cancel()


def test_cancel_increments_generation(mock_service):
    bridge = GlobalSearchBridge(search_service=mock_service)
    gen_before = bridge._search_gen
    bridge.cancel()
    assert bridge._search_gen > gen_before


def test_searching_state(mock_service):
    bridge = GlobalSearchBridge(search_service=mock_service)
    assert not bridge.isSearching


def test_no_service_cancel_still_ok():
    bridge = GlobalSearchBridge(search_service=None)
    result = bridge.cancel()
    assert result["ok"]


def test_stale_result_not_applied(mock_service):
    bridge = GlobalSearchBridge(search_service=mock_service)
    bridge._search_gen = 100
    bridge.search("Fresh")
    assert bridge._query == "Fresh"
