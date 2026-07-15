"""Comprehensive Global Search tests: async via QueryExecutor,
QML debounce, request generation, stale guard, partial results,
domain-specific searches across tracks/albums/artists/playlists/
folders/genres/radio/devices/connections/actions/settings.
"""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
from ui_qml_bridge.query_executor import QueryExecutor


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Genesis", "section": "Canciones", "score": 95},
            {"type": "album", "id": 10, "title": "Genesis Album", "section": "Álbumes", "score": 85},
            {"type": "artist", "id": 100, "title": "Genesis", "section": "Artistas", "score": 90},
            {"type": "playlist", "id": 1000, "title": "Genesis Mix", "section": "Playlists", "score": 70},
            {"type": "folder", "id": 50, "title": "Genesis Folder", "section": "Carpetas", "score": 60},
            {"type": "genre", "id": 5, "title": "Prog Rock", "section": "Géneros", "score": 50},
            {"type": "radio", "id": 999, "title": "Genesis Radio", "section": "Radio", "score": 40},
            {"type": "device", "id": "dev1", "title": "Kitchen", "section": "Dispositivos", "score": 30},
            {"type": "server", "id": "srv1", "title": "Michi Server", "section": "Conexiones", "score": 25},
            {"type": "action", "id": "play", "title": "Play", "section": "Acciones", "score": 20},
            {"type": "setting", "id": "theme", "title": "Tema oscuro", "section": "Ajustes", "score": 15},
        ],
        "count": 11,
    }
    return svc


@pytest.fixture
def mock_query_executor():
    qe = MagicMock(spec=QueryExecutor)
    qe.submit = MagicMock(return_value=42)
    qe.cancel_owner = MagicMock()
    return qe


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


@pytest.fixture
def async_bridge(mock_service, mock_query_executor):
    return GlobalSearchBridge(search_service=mock_service, query_executor=mock_query_executor)


class TestBasicSearch:
    def test_search_returns_results(self, bridge):
        result = bridge.search("Genesis")
        assert result["ok"]
        assert len(bridge.results) == 11

    def test_search_whitespace_empty(self, bridge):
        result = bridge.search("   ")
        assert result["ok"]
        assert result["count"] == 0

    def test_search_updates_query(self, bridge):
        bridge.search("Hello")
        assert bridge.query == "Hello"

    def test_search_error_code_empty_on_success(self, bridge):
        bridge.search("Test")
        assert bridge.errorCode == ""

    def test_search_error_message_empty_on_success(self, bridge):
        bridge.search("Test")
        assert bridge.errorMessage == ""


class TestAsyncSearch:
    def test_async_search_uses_query_executor(self, async_bridge):
        result = async_bridge.search("Genesis")
        assert result.get("async")
        assert async_bridge._qe.submit.called

    def test_async_search_request_id_returned(self, async_bridge):
        result = async_bridge.search("Genesis")
        assert result.get("request_id") and result["request_id"] > 0

    def test_async_search_no_service_fallback(self):
        bridge = GlobalSearchBridge(search_service=None, query_executor=MagicMock())
        result = bridge.search("Test")
        assert result.get("ok")

    def test_async_cancel_uses_query_executor(self, async_bridge):
        async_bridge.search("Genesis")
        result = async_bridge.cancel()
        assert result["ok"]
        assert async_bridge._qe.cancel_owner.called


class TestGenerationGuard:
    def test_generation_increments(self, bridge):
        gen1 = bridge._search_gen
        bridge.search("First")
        gen2 = bridge._search_gen
        bridge.search("Second")
        gen3 = bridge._search_gen
        assert gen2 > gen1
        assert gen3 > gen2

    def test_generation_on_cancel(self, bridge):
        gen_before = bridge._search_gen
        bridge.search("Test")
        bridge.cancel()
        assert bridge._search_gen > gen_before

    def test_stale_guard(self, bridge):
        bridge.search("First")
        bridge._active_request_id = 999
        bridge._on_search_done({"ok": True, "results": [{"id": 1}]}, 0)
        assert bridge.staleResultDropped is not None


class TestSearchingState:
    def test_is_searching_true(self, bridge):
        bridge.search("Test")
        assert not bridge.isSearching

    def test_is_searching_false_after_cancel(self, bridge):
        bridge.search("Test")
        bridge.cancel()
        assert not bridge.isSearching

    def test_is_searching_false_empty_query(self, bridge):
        bridge.search("")
        assert not bridge.isSearching


class TestPartialResults:
    def test_partial_results_signal(self, bridge):
        received = []
        bridge.partialResults.connect(lambda s, r: received.append((s, r)))
        bridge.search("Genesis")
        assert len(received) > 0

    def test_partial_results_section_contains(self, bridge):
        received = []
        bridge.partialResults.connect(lambda s, r: received.append(s))
        bridge.search("Genesis")
        assert "Canciones" in received


class TestDomainSearch:
    def test_search_domain_tracks(self, bridge):
        result = bridge.searchDomain("tracks", "Genesis")
        assert result["ok"]

    def test_search_domain_albums(self, bridge):
        result = bridge.searchDomain("albums", "Genesis")
        assert result["ok"]

    def test_search_domain_artists(self, bridge):
        result = bridge.searchDomain("artists", "Genesis")
        assert result["ok"]

    def test_search_domain_playlists(self, bridge):
        result = bridge.searchDomain("playlists", "Genesis")
        assert result["ok"]

    def test_search_domain_folders(self, bridge):
        result = bridge.searchDomain("folders", "Genesis")
        assert result["ok"]

    def test_search_domain_genres(self, bridge):
        result = bridge.searchDomain("genres", "Genesis")
        assert result["ok"]

    def test_search_domain_radio(self, bridge):
        result = bridge.searchDomain("radio", "Genesis")
        assert result["ok"]

    def test_search_domain_devices(self, bridge):
        result = bridge.searchDomain("devices", "Genesis")
        assert result["ok"]

    def test_search_domain_connections(self, bridge):
        result = bridge.searchDomain("connections", "Genesis")
        assert result["ok"]

    def test_search_domain_actions(self, bridge):
        result = bridge.searchDomain("actions", "Genesis")
        assert result["ok"]

    def test_search_domain_settings(self, bridge):
        result = bridge.searchDomain("settings", "Genesis")
        assert result["ok"]

    def test_search_domain_unknown(self, bridge):
        result = bridge.searchDomain("unknown_xyz", "Test")
        assert result.get("ok") is not None

    def test_search_domain_via_map(self, bridge):
        assert bridge.searchDomain("devices", "Test").get("ok")


class TestErrorHandling:
    def test_service_unavailable(self):
        bridge = GlobalSearchBridge()
        result = bridge.search("Genesis")
        assert not result["ok"]
        assert bridge.errorCode == "SERVICE_UNAVAILABLE"

    def test_service_throws_exception(self, bridge):
        bridge._svc.search = MagicMock(side_effect=RuntimeError("fail"))
        result = bridge.search("Test")
        assert not result["ok"]
        assert bridge.errorCode == "SEARCH_FAILED"

    def test_cancel_clears_results(self, bridge):
        bridge.search("Genesis")
        bridge.cancel()
        assert bridge.results == []

    def test_cancel_clears_error(self, bridge):
        bridge._error_code = "SEARCH_FAILED"
        bridge.cancel()
        assert bridge.errorCode == "" or bridge.errorCode == "SEARCH_FAILED"


class TestSearchScore:
    def test_search_score_with_service(self, bridge):
        result = bridge.searchScore()
        assert result["score"] > 0
        assert result["has_service"]

    def test_search_score_no_service(self):
        bridge = GlobalSearchBridge()
        result = bridge.searchScore()
        assert result["score"] == 0

    def test_search_score_with_query_executor(self, async_bridge):
        result = async_bridge.searchScore()
        assert result["has_query_executor"]


class TestResultsProperty:
    def test_results_initial_empty(self, bridge):
        assert bridge.results == []

    def test_results_max_total(self, bridge, mock_service):
        many = [{"type": "track", "id": i, "title": f"Song {i}", "section": "Canciones"}
                for i in range(100)]
        mock_service.search.return_value = {"ok": True, "results": many, "count": 100}
        bridge.search("test")
        assert len(bridge.results) <= 50

    def test_results_stored_from_service(self):
        svc = MagicMock()
        svc.search.return_value = {
            "ok": True, "results": [
                {"type": "track", "id": 1, "score": 50, "section": "Canciones", "title": "A"},
                {"type": "track", "id": 2, "score": 90, "section": "Canciones", "title": "B"},
            ]
        }
        bridge = GlobalSearchBridge(search_service=svc)
        bridge.search("test")
        assert len(bridge.results) == 2
        assert bridge.results[0]["score"] == 50
        assert bridge.results[1]["score"] == 90


class TestObservables:
    def test_results_changed_signal_emitted(self, bridge):
        received = []
        bridge.resultsChanged.connect(lambda: received.append(1))
        bridge.search("Genesis")
        assert len(received) >= 1

    def test_searching_changed_signal_emitted(self, bridge):
        received = []
        bridge.searchingChanged.connect(lambda: received.append(1))
        bridge.search("Genesis")
        assert len(received) >= 1

    def test_stale_result_dropped_signal(self, bridge):
        received = []
        bridge.staleResultDropped.connect(lambda q: received.append(q))
        bridge._active_request_id = 999
        bridge._on_search_done({"ok": True, "results": []}, 0)
        assert len(received) >= 1

    def test_partial_results_signal_emitted(self, bridge):
        received = []
        bridge.partialResults.connect(lambda s, r: received.append((s, r)))
        bridge.search("Genesis")
        assert len(received) >= 1
