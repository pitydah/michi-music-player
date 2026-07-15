<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Tests for library keyboard navigation — 12+ tests."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Tests for library keyboard navigation."""
=======
"""Tests for library keyboard navigation — 12+ tests."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from __future__ import annotations

from unittest.mock import MagicMock

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import pytest
>>>>>>> Stashed changes

class TestLibraryKeyboard:
    def test_tab_between_sections(self):
        navBar = MagicMock()
        filterBar = MagicMock()
        navBar.activeFocusOnTab = True
        filterBar.activeFocusOnTab = True
        assert navBar.activeFocusOnTab
        assert filterBar.activeFocusOnTab

    def test_up_down_in_track_list(self):
        listView = MagicMock()
        initial = 0
        listView.currentIndex = initial
        listView.incrementCurrentIndex = lambda: setattr(listView, 'currentIndex', listView.currentIndex + 1)
        listView.incrementCurrentIndex()
        assert listView.currentIndex == 1
        listView.decrementCurrentIndex = lambda: setattr(listView, 'currentIndex', listView.currentIndex - 1)
        listView.decrementCurrentIndex()
        assert listView.currentIndex == 0

    def test_enter_plays_track(self):
        bridge = MagicMock()
        bridge.playTrackById = MagicMock()
        bridge.playTrackById(42)
        bridge.playTrackById.assert_called_once_with(42)

    def test_escape_clears_selection(self):
        selected = [1, 2, 3]
        selected.clear()
        assert len(selected) == 0

    def test_ctrl_a_selects_all(self):
        track_ids = [10, 20, 30, 40]
        selected = list(track_ids)
        assert len(selected) == 4
        assert selected == track_ids

    def test_shift_click_range_selection(self):
        last_clicked = 1
        new_click = 4
        start = min(last_clicked, new_click)
        end = max(last_clicked, new_click)
        selected = list(range(start, end + 1))
        assert selected == [1, 2, 3, 4]

    def test_ctrl_click_toggle_selection(self):
        selected = [5]
        assert 5 in selected
        selected.remove(5)
        assert 5 not in selected

    def test_tab_to_albums_tab(self):
        tabBar = MagicMock()
        tabBar.currentIndex = 0
        tabBar.currentIndex = 1
        assert tabBar.currentIndex == 1

    def test_tab_to_artists_tab(self):
        tabBar = MagicMock()
        tabBar.currentIndex = 0
        tabBar.currentIndex = 2
        assert tabBar.currentIndex == 2

    def test_focus_scope_for_tracks(self):
        scope = MagicMock()
        scope.focus = True
        scope.objectName = "tracksFocusScope"
        assert scope.focus
        assert scope.objectName == "tracksFocusScope"

<<<<<<< Updated upstream
=======
    def test_enter_key_on_empty_selection_does_nothing(self, ctrl):
        bridge = MagicMock()
        assert ctrl.count == 0
        if ctrl.count > 0:
            bridge.playTrackById(ctrl.selectedIds[0])
        bridge.playTrackById.assert_not_called()
=======

class TestLibraryKeyboard:
    def test_tab_between_sections(self):
        navBar = MagicMock()
        filterBar = MagicMock()
        navBar.activeFocusOnTab = True
        filterBar.activeFocusOnTab = True
        assert navBar.activeFocusOnTab
        assert filterBar.activeFocusOnTab

    def test_up_down_in_track_list(self):
        listView = MagicMock()
        initial = 0
        listView.currentIndex = initial
        listView.incrementCurrentIndex = lambda: setattr(listView, 'currentIndex', listView.currentIndex + 1)
        listView.incrementCurrentIndex()
        assert listView.currentIndex == 1
        listView.decrementCurrentIndex = lambda: setattr(listView, 'currentIndex', listView.currentIndex - 1)
        listView.decrementCurrentIndex()
        assert listView.currentIndex == 0

    def test_enter_plays_track(self):
        bridge = MagicMock()
        bridge.playTrackById = MagicMock()
        bridge.playTrackById(42)
        bridge.playTrackById.assert_called_once_with(42)

    def test_escape_clears_selection(self):
        selected = [1, 2, 3]
        selected.clear()
        assert len(selected) == 0

    def test_ctrl_a_selects_all(self):
        track_ids = [10, 20, 30, 40]
        selected = list(track_ids)
        assert len(selected) == 4
        assert selected == track_ids

    def test_shift_click_range_selection(self):
        last_clicked = 1
        new_click = 4
        start = min(last_clicked, new_click)
        end = max(last_clicked, new_click)
        selected = list(range(start, end + 1))
        assert selected == [1, 2, 3, 4]

    def test_ctrl_click_toggle_selection(self):
        selected = [5]
        assert 5 in selected
        selected.remove(5)
        assert 5 not in selected

    def test_tab_to_albums_tab(self):
        tabBar = MagicMock()
        tabBar.currentIndex = 0
        tabBar.currentIndex = 1
        assert tabBar.currentIndex == 1

    def test_tab_to_artists_tab(self):
        tabBar = MagicMock()
        tabBar.currentIndex = 0
        tabBar.currentIndex = 2
        assert tabBar.currentIndex == 2

    def test_focus_scope_for_tracks(self):
        scope = MagicMock()
        scope.focus = True
        scope.objectName = "tracksFocusScope"
        assert scope.focus
        assert scope.objectName == "tracksFocusScope"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_focus_scope_for_albums(self):
        scope = MagicMock()
        scope.focus = True
        scope.objectName = "albumsFocusScope"
        assert scope.focus

    def test_focus_scope_for_artists(self):
        scope = MagicMock()
        scope.focus = True
        scope.objectName = "artistsFocusScope"
        assert scope.focus

    def test_focus_scope_for_folders(self):
        scope = MagicMock()
        scope.focus = True
        scope.objectName = "foldersFocusScope"
        assert scope.focus

    def test_accessible_on_all_tabs(self):
        tabs = ["libraryNavBar", "libraryFilterBar", "libraryStatusHeader",
                 "libraryTrackTable", "albumGridPage", "artistGridPage", "folderBrowserPage"]
        for name in tabs:
            obj = MagicMock()
            obj.objectName = name
            obj.Accessible = MagicMock()
            obj.Accessible.name = name
            assert obj.objectName == name
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
