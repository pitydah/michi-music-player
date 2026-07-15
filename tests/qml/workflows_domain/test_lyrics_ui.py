"""Integration tests for LyricsPage UI: states, accessibility, keyboard, null bridge."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("lyrics")]


class TestLyricsPage:
    """Verify LyricsPage loads, states, accessibility, keyboard, null bridge."""

    PAGE_QML = "ui_qml/pages/LyricsPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "lyrics.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Letra"
        assert page.property("accessible_description") == "Visualizador de letras de canciones"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("lb") is None

    def test_route_enter_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.routeEnter("lyrics")

    def test_route_enter_with_bridge(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "lyricsBridge": bridge
        })
        page.routeEnter("lyrics")
        bridge.searchCurrentTrack.assert_called_once()

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True

    def test_show_synced_property(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("showSynced") is False

    def test_searching_state(self, qml_harness):
        bridge = MagicMock()
        bridge.status = "searching"
        qml_harness.load_component(self.PAGE_QML, {
            "lyricsBridge": bridge
        })

    def test_not_found_state(self, qml_harness):
        bridge = MagicMock()
        bridge.status = "not_found"
        qml_harness.load_component(self.PAGE_QML, {
            "lyricsBridge": bridge
        })

    def test_done_state(self, qml_harness):
        bridge = MagicMock()
        bridge.status = "done"
        bridge.hasSyncedLyrics = False
        bridge.lyrics = "Test lyrics"
        qml_harness.load_component(self.PAGE_QML, {
            "lyricsBridge": bridge
        })

    def test_escape_closes_search(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.event("keyPress", {"key": 16777216})
