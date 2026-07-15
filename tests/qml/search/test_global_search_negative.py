"""Test negative/error cases for global search to ensure robustness."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

pytestmark = [pytest.mark.qml_module("global_search"),
              pytest.mark.qml_dimension("negative")]


@pytest.fixture
def bridge_no_service():
    return GlobalSearchBridge(search_service=None)


@pytest.fixture
def mock_service():
    return MagicMock()


class TestGlobalSearchNegative:
    """Test error/edge case handling."""

    def test_null_bridge_handling(self):
        bridge = GlobalSearchBridge(search_service=None)
        result = bridge.search("Test")
        assert not result.get("ok")
        assert bridge.errorCode == "SERVICE_UNAVAILABLE"

    def test_search_service_throws(self, mock_service):
        mock_service.search.side_effect = RuntimeError("Unexpected crash")
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert not result.get("ok")

    def test_search_service_returns_none(self, mock_service):
        mock_service.search.return_value = None
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert not result.get("ok")

    def test_search_service_returns_malformed(self, mock_service):
        mock_service.search.return_value = {"unexpected": True}
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("Test")
        assert "ok" not in result or not result.get("ok")

    def test_empty_query_clears_error(self, bridge_no_service):
        bridge_no_service.search("")
        assert bridge_no_service.errorCode == ""
        assert bridge_no_service.errorMessage == ""

    def test_very_long_query(self, mock_service):
        mock_service.search.return_value = {"ok": True, "results": [], "count": 0}
        bridge = GlobalSearchBridge(search_service=mock_service)
        long_query = "a" * 10000
        result = bridge.search(long_query)
        assert result.get("ok", False) is True

    def test_special_characters_query(self, mock_service):
        mock_service.search.return_value = {"ok": True, "results": [], "count": 0}
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("!@#$%^&*()_+")
        assert result.get("ok", False) is True

    def test_search_unicode_query(self, mock_service):
        mock_service.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "title": "Canción",
                 "subtitle": "Artista", "section": "track", "score": 1.0}
            ], "count": 1
        }
        bridge = GlobalSearchBridge(search_service=mock_service)
        result = bridge.search("canción")
        assert result.get("ok")

    def test_concurrent_searches_stale_protected(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge._active_request_id = 0
        bridge.search("First")
        first_id = bridge._active_request_id
        bridge._active_request_id = 9999
        bridge.search("Override")
        assert first_id >= 0
        assert bridge._active_request_id >= 1

    def test_cancel_while_searching(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Test")
        bridge.cancel()
        mock_service.search.assert_called()
        assert bridge.results == []

    def test_search_after_cancel(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.cancel()
        result = bridge.search("After cancel")
        assert result.get("ok", False) is True

    def test_is_searching_reset_on_cancel(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        bridge.search("Test")
        bridge.cancel()
        assert not bridge.isSearching

    def test_generation_monotonic(self, mock_service):
        bridge = GlobalSearchBridge(search_service=mock_service)
        gens = []
        for i in range(10):
            bridge.search(str(i))
            gens.append(bridge._search_gen)
        for i in range(1, len(gens)):
            assert gens[i] >= gens[i - 1]
