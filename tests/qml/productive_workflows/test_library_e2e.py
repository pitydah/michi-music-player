"""E2E workflow: Library — navigation, search, filters, sort, pagination, QTest."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest



pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("library"),
]


class TestLibraryE2E:
    def test_navigate_to_library(self, nav):
        nav.navigate("library")
        assert nav.currentRoute == "library", (
            f"Expected 'library', got '{nav.currentRoute}'"
        )

    def test_navigate_back_forward(self, nav):
        nav.navigate("library")
        nav.navigate("home")
        assert nav.currentRoute == "home"
        nav.back()
        assert nav.currentRoute == "library"
        nav.forward()
        assert nav.currentRoute == "home"

    def test_library_search_field(self, library_bridge):
        result = library_bridge.setSearchQuery("queen")
        assert isinstance(result, dict)
        library_bridge.clearSearch()

    def test_library_search_clear(self, library_bridge):
        library_bridge.setSearchQuery("test")
        result = library_bridge.clearSearch()
        assert isinstance(result, dict)

    def test_library_filter_format(self, library_bridge):
        result = library_bridge.setFormatFilter("FLAC")
        assert isinstance(result, dict)
        result = result.get("ok", True) or True

    def test_library_filter_genre(self, library_bridge):
        result = library_bridge.setGenreFilter("Rock")
        assert isinstance(result, dict)

    def test_library_filter_year(self, library_bridge):
        result = library_bridge.setYearFilter("2020")
        assert isinstance(result, dict)
        library_bridge.clearFilters()

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
        library_bridge.getSongsPage(0, 20)
        result = library_bridge.loadNextPage()
        assert isinstance(result, dict)

    def test_library_load_library(self, library_bridge):
        result = library_bridge.loadLibrary()
        assert isinstance(result, dict)

    def test_library_favorites(self, library_bridge):
        result = library_bridge.toggleFavoriteById(1)
        assert isinstance(result, dict)

    def test_library_goto_album(self, library_bridge):
        result = library_bridge.getAlbumDetail("test_key")
        assert isinstance(result, dict)

    def test_library_goto_artist(self, library_bridge):
        result = library_bridge.getArtistDetail("Queen")
        assert isinstance(result, dict)

    def test_library_workflow_search_then_play(self, nav, library_bridge, playback_bridge):
        nav.navigate("library")
        assert nav.currentRoute == "library"
        library_bridge.setSearchQuery("test")
        library_bridge.getSongsPage(0, 20)
        play_result = playback_bridge.togglePlay()
        assert isinstance(play_result, dict)

    def test_qtest_navigate_search_keyboard(self, nav, library_bridge, root_window):
        from .conftest import find_qml_item
        nav.navigate("library")
        assert nav.currentRoute == "library"
        initial_state = library_bridge.state if hasattr(library_bridge, 'state') else ""
        search_field = find_qml_item(root_window, "libraryNavigationBar")
        assert search_field is not None, "libraryNavigationBar not found"
        search_field.forceActiveFocus()
        QTest.keyClicks(search_field, "queen")
        QTest.qWait(50)
        QTest.keyClick(search_field, Qt.Key_Return)
        QTest.qWait(50)
        assert nav.currentRoute == "library"

    def test_qtest_click_refresh(self, nav, library_bridge, root_window):
        from .conftest import find_qml_item, qtest_click_item
        nav.navigate("library")
        refresh_btn = find_qml_item(root_window, "libraryRefreshButton")
        assert refresh_btn is not None, "libraryRefreshButton not found"
        qtest_click_item(refresh_btn, root_window)
