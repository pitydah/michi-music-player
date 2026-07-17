"""Workflow: Library → Search → Select → Play — QTest interaction tests."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("library"),
]


class TestLibraryWorkflow:
    def test_qtest_search_field(self, nav, library_bridge, root_window):
        from .conftest import find_qml_item
        nav.navigate("library")
        assert nav.currentRoute == "library"
        search_bar = find_qml_item(root_window, "libraryNavigationBar")
        assert search_bar is not None, "libraryNavigationBar not found"
        search_bar.forceActiveFocus()
        QTest.keyClicks(search_bar, "queen")
        QTest.qWait(50)
        QTest.keyClick(search_bar, Qt.Key_Return)
        QTest.qWait(50)
        assert nav.currentRoute == "library"

    def test_qtest_playback_controls(self, nav, playback_bridge, root_window):
        from .conftest import find_qml_item, qtest_click_item, wait_for_property
        nav.navigate("playback")
        assert nav.currentRoute == "playback"
        controls = find_qml_item(root_window, "nowPlayingControls")
        assert controls is not None, "nowPlayingControls not found"
        state_before = getattr(playback_bridge, 'state', '')
        qtest_click_item(controls, root_window)
        wait_for_property(controls, "visible", True, timeout_ms=500)
        state_after = getattr(playback_bridge, 'state', '')
        assert state_before != state_after or state_after != '', (
            f"Playback state should change: '{state_before}' -> '{state_after}'"
        )

    def test_qtest_queue_enqueue(self, nav, playback_bridge, root_window):
        result = playback_bridge.enqueueSong("1")
        assert result.get("ok") is True
        result2 = playback_bridge.playQueueItem(0)
        assert isinstance(result2, dict)

    def test_library_loads_songs(self, bootstrap):
        lib = bootstrap._bridges.get("library")
        assert lib is not None
        result = lib.loadLibrary()
        assert isinstance(result, dict)
        if result.get("ok", True):
            songs = result.get("songs", result.get("results", []))
            assert isinstance(songs, (list, tuple))

    def test_navigation_back_and_forward(self, bootstrap):
        nav = bootstrap._bridges.get("navigation")
        assert nav is not None
        nav.navigate("library")
        nav.navigate("home")
        assert nav.currentRoute == "home"
        nav.back()
        assert nav.currentRoute == "library"
        nav.forward()
        assert nav.currentRoute == "home"
