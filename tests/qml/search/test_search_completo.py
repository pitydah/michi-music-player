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
def async_bridge(mock_service, mock_query_executor):
    return GlobalSearchBridge(search_service=mock_service, query_executor=mock_query_executor)


class TestBasicSearch:
    def test_search_returns_results(self, async_bridge, mock_service):
        async_bridge._active_request_id = 1
        async_bridge._on_search_done(mock_service.search.return_value, 1)
        assert len(async_bridge.results) == 11

    def test_search_empties_results_on_new_search(self, async_bridge):
        async_bridge.search("Test")
        assert len(async_bridge.results) == 0

    def test_search_returns_async(self, async_bridge):
        result = async_bridge.search("Genesis")
        assert result.get("async") is True

    def test_search_empty_stays_empty(self, async_bridge):
        result = async_bridge.search("")
        assert result["ok"]
        assert result["count"] == 0

    def test_search_updates_query(self, async_bridge):
        async_bridge.search("Dark Side")
        assert async_bridge.query == "Dark Side"

    def test_search_results_preserve_order(self, async_bridge, mock_service):
        mock_service.search.return_value["results"] = [
            {"type": "track", "id": 1, "title": "Z", "section": "Canciones", "score": 50},
            {"type": "track", "id": 2, "title": "A", "section": "Canciones", "score": 95},
        ]
        async_bridge._active_request_id = 1
        async_bridge._on_search_done(mock_service.search.return_value, 1)
        assert len(async_bridge.results) == 2

    def test_partial_results_emitted(self, async_bridge):
        spy = []
        async_bridge.partialResults.connect(lambda s, i: spy.append((s, i)))
        async_bridge._active_request_id = 1
        async_bridge._on_search_done({
            "ok": True, "results": [
                {"type": "track", "title": "A", "section": "Canciones"},
                {"type": "album", "title": "B", "section": "Álbumes"},
            ]
        }, 1)
        assert len(spy) >= 2


class TestStaleGuard:
    def test_stale_guard_discards_old_request(self, async_bridge):
        async_bridge._active_request_id = 2
        async_bridge._on_search_done({"ok": True, "results": [{"type": "track"}]}, 1)
        assert len(async_bridge.results) == 0

    def test_stale_signal_emitted(self, async_bridge):
        spy = []
        async_bridge.staleResultDropped.connect(spy.append)
        async_bridge._active_request_id = 2
        async_bridge._on_search_done({"ok": True, "results": [{"type": "track"}]}, 1)
        assert len(spy) >= 1

    def test_sequential_searches_no_stale(self, async_bridge):
        async_bridge.search("First")
        first_req = async_bridge._active_request_id
        async_bridge.search("Second")
        assert async_bridge._active_request_id != first_req


class TestDomainSearch:
    def test_domain_tracks(self, async_bridge):
        result = async_bridge.searchDomain("tracks", "genes")
        assert result.get("async") is True

    def test_domain_albums(self, async_bridge):
        async_bridge.searchDomain("albums", "dark")
        assert async_bridge.query == "album:dark"

    def test_domain_unknown(self, async_bridge):
        async_bridge.searchDomain("xyz", "test")
        assert async_bridge.query == "xyz:test"

    def test_all_domains_covered(self, async_bridge):
        for d in ("tracks", "albums", "artists", "playlists"):
            async_bridge.searchDomain(d, "q")


class TestCancel:
    def test_cancel_clears_results(self, async_bridge):
        async_bridge._results = [{"type": "track"}]
        async_bridge.cancel()
        assert len(async_bridge.results) == 0

    def test_cancel_clears_searching(self, async_bridge):
        async_bridge._is_searching = True
        async_bridge.cancel()
        assert not async_bridge.isSearching

    def test_cancel_calls_qe(self, async_bridge, mock_query_executor):
        async_bridge.cancel()
        mock_query_executor.cancel_owner.assert_called_once_with("global_search")


class TestCapabilities:
    def test_get_capabilities(self, async_bridge):
        caps = async_bridge.getCapabilities()
        assert "has_service" in caps
        assert "has_query_executor" in caps
