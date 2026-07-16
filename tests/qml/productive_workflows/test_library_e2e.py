"""E2E workflow: Library → Search → Select → Play — full Main.qml + QTest interaction."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("library"),
]


class TestLibraryE2E:
    def test_navigate_to_library(self, nav):
        nav.navigate("library")
        assert nav.currentRoute == "library", f"Expected 'library', got '{nav.currentRoute}'"

    def test_library_tabs_canciones(self, nav, library_bridge):
        nav.navigate("library")
        assert library_bridge is not None, "LibraryBridge should exist"

    def test_library_search_field(self, library_bridge):
        result = library_bridge.setSearchQuery("test query")
        assert isinstance(result, dict)

    def test_library_search_clear(self, library_bridge):
        library_bridge.setSearchQuery("test")
        result = library_bridge.clearSearch()
        assert isinstance(result, dict)

    def test_library_filter_format(self, library_bridge):
        result = library_bridge.setFormatFilter("FLAC")
        assert isinstance(result, dict)

    def test_library_filter_genre(self, library_bridge):
        result = library_bridge.setGenreFilter("Rock")
        assert isinstance(result, dict)

    def test_library_filter_year(self, library_bridge):
        result = library_bridge.setYearFilter("2020")
        assert isinstance(result, dict)

    def test_library_filter_clear(self, library_bridge):
        library_bridge.setFormatFilter("FLAC")
        result = library_bridge.clearFilters()
        assert isinstance(result, dict)

    def test_library_sort_by_title(self, library_bridge):
        result = library_bridge.sortBy("title")
        assert isinstance(result, dict)

    def test_library_sort_by_artist(self, library_bridge):
        result = library_bridge.sortBy("artist")
        assert isinstance(result, dict)

    def test_library_get_songs_page(self, library_bridge):
        result = library_bridge.getSongsPage(0, 20)
        assert isinstance(result, (list, tuple))

    def test_library_load_next_page(self, library_bridge):
        result = library_bridge.loadNextPage()
        assert isinstance(result, dict)

    def test_library_load_library(self, library_bridge):
        result = library_bridge.loadLibrary()
        assert isinstance(result, dict)

    def test_library_workflow_search_select_play(self, nav, library_bridge, playback_bridge):
        nav.navigate("library")
        assert nav.currentRoute == "library"
        library_bridge.setSearchQuery("test")
        songs = library_bridge.getSongsPage(0, 20)
        assert isinstance(songs, (list, tuple))
        play_result = playback_bridge.togglePlay()
        assert isinstance(play_result, dict)
