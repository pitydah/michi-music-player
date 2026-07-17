"""Workflow: PlaybackPage — QTest navigation and interaction."""
from __future__ import annotations
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

pytestmark = [
    pytest.mark.qml_module("playback"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestPlaybackPage:
    def test_qtest_navigate_playback_page(self, nav, root_window):
        from .conftest import find_qml_item, wait_for_property
        nav.navigate("playback")
        assert nav.currentRoute == "playback"
        page = find_qml_item(root_window, "playbackPage")
        assert page is not None, "playbackPage not found"
        wait_for_property(page, "visible", True, timeout_ms=500)
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "playback"
