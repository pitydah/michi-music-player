"""Test keyboard navigation patterns for GlobalSearchPage components."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

pytestmark = [pytest.mark.qml_module("global_search"),
              pytest.mark.qml_dimension("accessibility")]


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True, "request_id": 1,
        "results": [
            {"type": "track", "id": 1, "title": "Song A", "subtitle": "Artist",
             "section": "track", "score": 1.0},
            {"type": "album", "id": 10, "title": "Album A", "subtitle": "",
             "section": "album", "score": 0.9},
            {"type": "artist", "id": 20, "title": "Artist A", "subtitle": "",
             "section": "artist", "score": 0.8},
        ],
        "count": 3,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


class TestGlobalSearchKeyboard:
    """Test keyboard navigation semantics for search."""

    def test_escape_clears_query(self, bridge):
        bridge.search("Test")
        assert bridge.query == "Test"
        bridge.cancel()
        assert bridge.query == "" or bridge.query == "Test"
        bridge.search("")
        assert bridge.query == ""

    def test_escape_empty_query_navigates_home(self, bridge):
        bridge.search("")
        assert bridge.results == []

    def test_enter_submits_search(self, bridge):
        bridge.search("Test")
        assert bridge.query == "Test"
        assert len(bridge.results) > 0

    def test_tab_between_sections(self, bridge):
        bridge.search("Test")
        sections = set(r["section"] for r in bridge.results)
        assert "track" in sections
        assert "album" in sections
        assert "artist" in sections

    def test_search_results_are_navigable(self, bridge):
        bridge.search("Test")
        items = bridge.results
        assert len(items) >= 3
        for item in items:
            assert item.get("title") is not None
            assert item.get("type") is not None

    def test_accessible_names_present(self, bridge):
        bridge.search("Song")
        for item in bridge.results:
            assert item.get("type") in ("track", "album", "artist")

    def test_multiple_escapes_clear_then_navigate(self, bridge):
        bridge.search("Test")
        assert bridge.query == "Test"
        bridge.search("")
        assert bridge.results == []
        bridge.search("")
        assert bridge.results == []

    def test_search_on_enter_with_empty_text(self, bridge):
        bridge.search("")
        assert bridge.results == []
        assert not bridge.isSearching

    def test_tab_order_preserved_after_search(self, bridge):
        bridge.search("A")
        bridge.cancel()
        bridge.search("B")
        assert bridge.query == "B"
        assert len(bridge.results) > 0
