"""Test GlobalSearchBridge: search flow with debounce, results grouping, sections."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Supper's Ready", "subtitle": "Genesis · Foxtrot",
             "section": "Canciones", "score": 0.95},
            {"type": "album", "id": "key1", "title": "Foxtrot", "subtitle": "Genesis · 1972",
             "section": "Álbumes", "score": 0.90},
            {"type": "artist", "id": 10, "title": "Genesis", "subtitle": "Rock progresivo",
             "section": "Artistas", "score": 0.85},
            {"type": "playlist", "id": 5, "title": "Rock Classics", "subtitle": "25 canciones",
             "section": "Playlists", "score": 0.70},
            {"type": "radio", "id": 3, "title": "Jazz FM", "subtitle": "MP3 · US",
             "section": "Radio", "score": 0.60},
        ],
        "count": 5,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


class TestSearchFlow:
    def test_search_returns_grouped_results(self, bridge):
        result = bridge.search("Genesis")
        assert result["ok"]
        assert len(bridge.results) == 5
        sections = {r["section"] for r in bridge.results}
        assert "Canciones" in sections
        assert "Álbumes" in sections
        assert "Artistas" in sections

    def test_search_empty_query_returns_empty(self, bridge):
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0

    def test_search_whitespace_query_returns_empty(self, bridge):
        result = bridge.search("   ")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0

    def test_searching_state_during_search(self, bridge):
        assert not bridge.isSearching
        bridge.search("Test")
        assert not bridge.isSearching

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
        bridge.search("Test")
        assert bridge.errorCode == ""

    def test_error_message_empty_on_success(self, bridge):
        bridge.search("Test")
        assert bridge.errorMessage == ""

    def test_multiple_sections_in_results(self, bridge):
        bridge.search("Genesis")
        sections = set()
        for r in bridge.results:
            sections.add(r["section"])
        assert len(sections) >= 4

    def test_result_score_ordering(self, bridge):
        bridge.search("Genesis")
        scores = [r.get("score", 0) for r in bridge.results]
        assert scores == sorted(scores, reverse=True)

    def test_search_domain_track(self, bridge):
        result = bridge.searchDomain("track", "Genesis")
        assert result["ok"]

    def test_search_domain_unknown(self, bridge):
        result = bridge.searchDomain("unknown", "Test")
        assert not result["ok"]
        assert result["error"] == "UNKNOWN_DOMAIN"

    def test_cancel_search(self, bridge):
        result = bridge.cancel()
        assert result["ok"]

    def test_cancel_clears_results(self, bridge):
        bridge.search("Genesis")
        assert len(bridge.results) > 0
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_cancel_increments_generation(self, bridge):
        gen_before = bridge._search_gen
        bridge.cancel()
        assert bridge._search_gen > gen_before

    def test_debounce_not_applicable_synchronous(self, bridge):
        result = bridge.search("Quick search")
        assert result["ok"]
        assert len(bridge.results) > 0

    def test_search_respects_max_total(self, bridge, mock_service):
        many_results = [
            {"type": "track", "id": i, "title": f"Song {i}", "section": "Canciones"}
            for i in range(100)
        ]
        mock_service.search.return_value = {
            "ok": True, "results": many_results, "count": 100
        }
        bridge.search("test")
        assert len(bridge.results) <= 50
