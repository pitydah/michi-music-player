"""Workflow test: query characters → debounce → navigate → activate result."""
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
        ],
        "count": 4,
    }
    return svc


@pytest.fixture
def bridge(mock_service):
    return GlobalSearchBridge(search_service=mock_service)


class TestSearchWorkflow:
    """Complete search workflow: query → debounce → navigate → activate."""

    def test_wf_initial_state_empty(self, bridge):
        assert bridge.query == ""
        assert bridge.results == []
        assert not bridge.isSearching
        assert bridge.errorCode == ""
        assert bridge.errorMessage == ""

    def test_wf_type_query_characters(self, bridge):
        bridge.search("B")
        assert bridge.query == "B"
        bridge.search("Bo")
        assert bridge.query == "Bo"
        bridge.search("Bohem")
        assert bridge.query == "Bohem"

    def test_wf_debounce_effect(self, bridge):
        bridge.search("A")
        bridge.search("AB")
        bridge.search("ABC")
        assert bridge.query == "ABC"

    def test_wf_search_executed(self, bridge):
        bridge.search("Queen")
        assert bridge.query == "Queen"
        assert len(bridge.results) > 0

    def test_wf_results_sectioned(self, bridge):
        bridge.search("Queen")
        sections = set(r["section"] for r in bridge.results)
        assert "track" in sections
        assert "album" in sections
        assert "artist" in sections
        assert "playlist" in sections

    def test_wf_navigate_to_track(self, bridge):
        bridge.search("Queen")
        tracks = [r for r in bridge.results if r["type"] == "track"]
        assert len(tracks) >= 1
        assert tracks[0]["title"] == "Bohemian Rhapsody"

    def test_wf_navigate_to_album(self, bridge):
        bridge.search("Queen")
        albums = [r for r in bridge.results if r["type"] == "album"]
        assert len(albums) >= 1
        assert albums[0]["title"] == "A Night at the Opera"

    def test_wf_navigate_to_artist(self, bridge):
        bridge.search("Queen")
        artists = [r for r in bridge.results if r["type"] == "artist"]
        assert len(artists) >= 1
        assert artists[0]["title"] == "Queen"

    def test_wf_navigate_to_playlist(self, bridge):
        bridge.search("Queen")
        playlists = [r for r in bridge.results if r["type"] == "playlist"]
        assert len(playlists) >= 1
        assert playlists[0]["title"] == "Queen Essentials"

    def test_wf_clear_query_resets_results(self, bridge):
        bridge.search("Queen")
        assert len(bridge.results) > 0
        bridge.search("")
        assert len(bridge.results) == 0

    def test_wf_cancel_during_search(self, bridge):
        bridge.search("Queen")
        bridge.cancel()
        assert not bridge.isSearching

    def test_wf_search_after_cancel(self, bridge):
        bridge.search("Queen")
        bridge.cancel()
        bridge.search("Bohemian")
        assert bridge.query == "Bohemian"

    def test_wf_empty_results_state(self, bridge, mock_service):
        mock_service.search.return_value = {"ok": True, "results": [], "count": 0}
        bridge.search("zzzznonexistent")
        assert len(bridge.results) == 0

    def test_wf_result_has_score(self, bridge):
        bridge.search("Queen")
        for r in bridge.results:
            assert r["score"] > 0
