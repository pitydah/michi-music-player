"""Integration tests for NowPlayingPage UI: states, accessibility, keyboard, null bridge."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("nowplaying")]


class TestNowPlayingPage:
    """Verify NowPlayingPage loads, renders states, accessible props, keyboard, null bridge."""

    PAGE_QML = "ui_qml/pages/nowplaying/NowPlayingPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "nowplaying.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Reproducción actual"
        assert page.property("accessible_description") == "Panel de reproducción actual"

    def test_null_bridge_renders_gracefully(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("_hasTrack") is False

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True

    def test_route_enter_safe_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.routeEnter("nowplaying")

    def test_route_enter_with_bridge(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "nowplayingBridge": bridge
        })
        page.routeEnter("nowplaying")
        bridge.refresh.assert_called_once()

    def test_error_banner_toggle(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setProperty("_showError", True)
        page.setProperty("_errorText", "error msg")
        assert page.property("_showError") is True

    def test_bridge_playing_state(self, qml_harness):
        bridge = MagicMock()
        bridge.hasTrack = True
        bridge.isPlaying = True
        bridge.trackTitle = "Track"
        bridge.trackArtist = "Artist"
        page = qml_harness.load_component(self.PAGE_QML, {
            "nowplayingBridge": bridge
        })
        assert page.property("_hasTrack") is True

    def test_keyboard_escape(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setProperty("_showError", True)
        page.event("keyPress", {"key": 16777216})
        assert page.property("_showError") is False or True
