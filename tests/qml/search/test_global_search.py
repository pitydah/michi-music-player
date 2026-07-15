"""Test GlobalSearchPage and related components for correct search behavior."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

pytestmark = [pytest.mark.qml_module("global_search")]


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Test Song", "subtitle": "Artist · Album",
             "section": "track", "score": 1.0},
            {"type": "album", "id": 10, "title": "Test Album", "subtitle": "Artist",
             "section": "album", "score": 0.9},
            {"type": "artist", "id": 20, "title": "Test Artist", "subtitle": "",
             "section": "artist", "score": 0.8},
            {"type": "playlist", "id": 30, "title": "Test Playlist", "subtitle": "5 canciones",
             "section": "playlist", "score": 0.7},
            {"type": "folder", "id": 40, "title": "Test Folder", "subtitle": "/music/test",
             "section": "folder", "score": 0.6},
            {"type": "genre", "id": 50, "title": "Jazz", "subtitle": "120 canciones",
             "section": "genre", "score": 0.5},
            {"type": "radio", "id": 60, "title": "Jazz FM", "subtitle": "MP3 · UK",
             "section": "radio", "score": 0.4},
            {"type": "device", "id": 70, "title": "Office Speaker", "subtitle": "Snapcast",
             "section": "device", "score": 0.3},
            {"type": "server", "id": 80, "title": "Media Server", "subtitle": "192.168.1.100",
             "section": "server", "score": 0.2},
            {"type": "action", "id": "scan", "title": "Escanear biblioteca", "subtitle": "",
             "section": "action", "score": 0.1},
            {"type": "setting", "id": "audio", "title": "Configuración de audio",
             "subtitle": "Perfil de salida", "section": "setting", "score": 0.05},
        ],
        "count": 11,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


class TestGlobalSearchBridge:
    """Test bridge-level search functionality."""

    def test_search_returns_all_sectioned_results(self, bridge):
        result = bridge.search("Test")
        assert result["ok"]
        sections = set(r["section"] for r in result.get("results", bridge.results))
        expected = {"track", "album", "artist", "playlist", "folder", "genre",
                    "radio", "device", "server", "action", "setting"}
        assert sections == expected

    def test_search_empty_query(self, bridge):
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0

    def test_searching_state(self, bridge):
        assert not bridge.isSearching
        bridge.search("Test")
        assert not bridge.isSearching

    def test_error_code_on_failure(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("DB error")
        result = bridge.search("Test")
        assert not result.get("ok")

    def test_cancel_search(self, bridge):
        result = bridge.cancel()
        assert result["ok"]

    def test_generation_counter_increments(self, bridge):
        gen_before = bridge._search_gen
        bridge.search("First")
        gen_mid = bridge._search_gen
        assert gen_mid > gen_before
        bridge.search("Second")
        assert bridge._search_gen > gen_mid

    def test_stale_request_protection(self, bridge):
        bridge._active_request_id = 9999
        bridge._query = "Stale"
        bridge.search("Fresh")
        assert bridge._query == "Fresh"

    def test_no_search_service(self):
        b = GlobalSearchBridge(search_service=None)
        result = b.search("Test")
        assert not result.get("ok")
        assert b.errorCode == "SERVICE_UNAVAILABLE"

    def test_search_domain_unknown(self, bridge):
        result = bridge.searchDomain("unknown_domain", "test")
        assert not result.get("ok")
        assert result.get("error") == "UNKNOWN_DOMAIN"

    def test_search_debounce_timer(self, bridge):
        bridge.search("A")
        bridge.search("AB")
        bridge.search("ABC")
        assert bridge.query == "ABC"

    def test_results_cleared_on_empty_query(self, bridge):
        bridge.search("Test")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0

    def test_error_message_property(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("Connection error")
        bridge.search("Test")
        assert bridge.errorMessage != ""

    def test_error_code_property(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("DB locked")
        bridge.search("Test")
        assert bridge.errorCode == "SEARCH_FAILED"
