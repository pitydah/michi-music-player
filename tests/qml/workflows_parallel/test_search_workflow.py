"""Full workflow: type query, debounce, navigate results, activate with keyboard."""
"""Workflow test: query characters → debounce → navigate → activate result."""
"""Full workflow: type query, debounce, navigate results, activate with keyboard."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Bohemian Rhapsody",
             "subtitle": "Queen · A Night at the Opera", "section": "track", "score": 1.0},
            {"type": "album", "id": 10, "title": "A Night at the Opera",
             "subtitle": "Queen", "section": "album", "score": 0.9},
            {"type": "artist", "id": 20, "title": "Queen", "subtitle": "",
             "section": "artist", "score": 0.85},
            {"type": "playlist", "id": 30, "title": "Queen Essentials",
             "subtitle": "20 canciones", "section": "playlist", "score": 0.7},
            {"type": "track", "id": 1, "title": "Supper's Ready", "subtitle": "Genesis · Foxtrot",
             "section": "Canciones", "score": 1.0},
            {"type": "track", "id": 2, "title": "Firth of Fifth", "subtitle": "Genesis · Selling England",
             "section": "Canciones", "score": 0.95},
            {"type": "album", "id": "key1", "title": "Foxtrot", "subtitle": "Genesis · 1972",
             "section": "Álbumes", "score": 0.90},
            {"type": "artist", "id": 10, "title": "Genesis", "subtitle": "Rock progresivo",
             "section": "Artistas", "score": 0.85},
        ],
        "count": 4,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


class TestFullSearchWorkflow:
    def test_type_query_returns_results(self, bridge):
        result = bridge.search("Genesis")
        assert result["ok"]
        assert result["count"] == 4
        assert len(bridge.results) == 4
class TestSearchWorkflow:
    """Complete search workflow: query → debounce → navigate → activate."""

    def test_debounce_generation_tracking(self, bridge):
        gen1 = bridge._search_gen
        bridge.search("Foxtrot")
        assert bridge._search_gen > gen1
        assert bridge.query == "Foxtrot"

    def test_navigate_first_result(self, bridge):
        bridge.search("Genesis")
        first = bridge.results[0]
        assert first["type"] == "track"
        assert first["title"] == "Supper's Ready"

    def test_navigate_by_section(self, bridge):
        bridge.search("Genesis")
        albums = [r for r in bridge.results if r["section"] == "Álbumes"]
        assert len(albums) == 1
        assert albums[0]["title"] == "Foxtrot"

    def test_activate_result(self, bridge):
        bridge.search("Genesis")
        target = bridge.results[3]
        assert target["type"] == "artist"
        assert target["title"] == "Genesis"

    def test_clear_and_restart(self, bridge):
        bridge.search("Genesis")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0
        bridge.search("Selling England")
        assert len(bridge.results) > 0

    def test_sequential_search_updates_results(self, bridge, mock_service):
        bridge.search("Genesis")
        mock_service.search.return_value = {
            "ok": True, "request_id": 2,
            "results": [
                {"type": "track", "id": 3, "title": "Aqualung", "subtitle": "Jethro Tull",
                 "section": "Canciones", "score": 1.0},
            ],
            "count": 1,
        }
        bridge.search("Aqualung")
        assert len(bridge.results) == 1
        assert bridge.results[0]["title"] == "Aqualung"

    def test_cancel_mid_search(self, bridge):
        bridge.search("Genesis")
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_wf_result_has_score(self, bridge):
        bridge.search("Queen")
        for r in bridge.results:
            assert r["score"] > 0
class TestFullSearchWorkflow:
    def test_type_query_returns_results(self, bridge):
        result = bridge.search("Genesis")
        assert result["ok"]
        assert result["count"] == 4
        assert len(bridge.results) == 4

    def test_debounce_generation_tracking(self, bridge):
        gen1 = bridge._search_gen
        bridge.search("Foxtrot")
        assert bridge._search_gen > gen1
        assert bridge.query == "Foxtrot"

    def test_navigate_first_result(self, bridge):
        bridge.search("Genesis")
        first = bridge.results[0]
        assert first["type"] == "track"
        assert first["title"] == "Supper's Ready"

    def test_navigate_by_section(self, bridge):
        bridge.search("Genesis")
        albums = [r for r in bridge.results if r["section"] == "Álbumes"]
        assert len(albums) == 1
        assert albums[0]["title"] == "Foxtrot"

    def test_activate_result(self, bridge):
        bridge.search("Genesis")
        target = bridge.results[3]
        assert target["type"] == "artist"
        assert target["title"] == "Genesis"

    def test_clear_and_restart(self, bridge):
        bridge.search("Genesis")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0
        bridge.search("Selling England")
        assert len(bridge.results) > 0

    def test_sequential_search_updates_results(self, bridge, mock_service):
        bridge.search("Genesis")
        mock_service.search.return_value = {
            "ok": True, "request_id": 2,
            "results": [
                {"type": "track", "id": 3, "title": "Aqualung", "subtitle": "Jethro Tull",
                 "section": "Canciones", "score": 1.0},
            ],
            "count": 1,
        }
        bridge.search("Aqualung")
        assert len(bridge.results) == 1
        assert bridge.results[0]["title"] == "Aqualung"

    def test_cancel_mid_search(self, bridge):
        bridge.search("Genesis")
        bridge.cancel()
        assert len(bridge.results) == 0

    def test_cancel_then_new_search(self, bridge):
        bridge.search("Unwanted")
        bridge.cancel()
        result = bridge.search("Wanted")
        assert result["ok"]
        assert len(bridge.results) > 0

    def test_full_workflow_keyboard(self, bridge):
        bridge.search("Search")
        assert bridge.query == "Search"
        first = bridge.results[0]
        bridge.cancel()
        assert len(bridge.results) == 0
        bridge.search(first["title"])
        assert bridge.query == first["title"]

    def test_search_then_clear_then_repeat(self, bridge):
        bridge.search("First")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0
        bridge.search("First")
        assert len(bridge.results) > 0
        assert bridge.query == "First"
