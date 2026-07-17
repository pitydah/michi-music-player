"""Workflow: Lyrics → Load → Edit → Save."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("lyrics"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestLyrics:
    def test_lyrics_service_methods(self, bootstrap):
        svc = bootstrap.container.get("lyrics_service")
        assert svc is not None
        assert hasattr(svc, 'get_lyrics')
        assert hasattr(svc, 'save_lyrics')
        assert hasattr(svc, 'health')

    def test_lyrics_bridge_exists(self, bootstrap):
        lb = bootstrap._bridges.get("lyrics")
        assert lb is not None

    def test_qtest_navigate_lyrics(self, nav, root_window, all_bridges):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, wait_for_property
        nav.navigate("lyrics")
        assert nav.currentRoute == "lyrics"
        page = find_qml_item(root_window, "lyricsPage")
        assert page is not None, "lyricsPage not found"
        page.forceActiveFocus()
        QTest.keyClick(page, Qt.Key_Down)
        wait_for_property(page, "visible", True, timeout_ms=500)
        QTest.qWait(50)
        assert nav.currentRoute == "lyrics"
        lyrics_bridge = all_bridges.get("lyrics")
        assert lyrics_bridge is not None
        assert hasattr(lyrics_bridge, 'getLyrics') or hasattr(lyrics_bridge, 'get_lyrics')
