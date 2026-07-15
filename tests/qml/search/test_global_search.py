<<<<<<< Updated upstream
"""Test GlobalSearchBridge: search flow with debounce, results grouping, sections."""
import pytest
=======
<<<<<<< HEAD
"""Test GlobalSearchPage and related components for correct search behavior."""
>>>>>>> Stashed changes
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

<<<<<<< Updated upstream
=======
pytestmark = [pytest.mark.qml_module("global_search")]

=======
"""Test GlobalSearchBridge: search flow with debounce, results grouping, sections."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
<<<<<<< Updated upstream
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
=======
<<<<<<< HEAD
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
=======
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
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


<<<<<<< Updated upstream
class TestSearchFlow:
    def test_search_returns_grouped_results(self, bridge):
        result = bridge.search("Genesis")
=======
<<<<<<< HEAD
class TestGlobalSearchBridge:
    """Test bridge-level search functionality."""

    def test_search_returns_all_sectioned_results(self, bridge):
        result = bridge.search("Test")
>>>>>>> Stashed changes
        assert result["ok"]
        assert len(bridge.results) == 5
        sections = {r["section"] for r in bridge.results}
        assert "Canciones" in sections
        assert "Álbumes" in sections
        assert "Artistas" in sections

<<<<<<< Updated upstream
    def test_search_empty_query_returns_empty(self, bridge):
=======
    def test_search_empty_query(self, bridge):
=======
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
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        result = bridge.search("")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    def test_searching_state(self, bridge):
=======
>>>>>>> Stashed changes
    def test_search_whitespace_query_returns_empty(self, bridge):
        result = bridge.search("   ")
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.results) == 0

    def test_searching_state_during_search(self, bridge):
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        assert not bridge.isSearching
        bridge.search("Test")
        assert not bridge.isSearching

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    def test_error_code_on_failure(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("DB error")
        result = bridge.search("Test")
        assert not result.get("ok")
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    def test_cancel_search(self, bridge):
        result = bridge.cancel()
        assert result["ok"]

<<<<<<< Updated upstream
    def test_cancel_clears_results(self, bridge):
        bridge.search("Genesis")
=======
<<<<<<< HEAD
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
>>>>>>> Stashed changes
        assert len(bridge.results) > 0
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_cancel_increments_generation(self, bridge):
        gen_before = bridge._search_gen
        bridge.cancel()
        assert bridge._search_gen > gen_before

<<<<<<< Updated upstream
=======
    def test_error_code_property(self, bridge, mock_service):
        mock_service.search.side_effect = Exception("DB locked")
        bridge.search("Test")
        assert bridge.errorCode == "SEARCH_FAILED"
=======
    def test_cancel_clears_results(self, bridge):
        bridge.search("Genesis")
        assert len(bridge.results) > 0
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_cancel_increments_generation(self, bridge):
        gen_before = bridge._search_gen
        bridge.cancel()
        assert bridge._search_gen > gen_before

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
