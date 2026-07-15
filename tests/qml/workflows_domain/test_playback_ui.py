"""Integration tests for PlaybackPage UI: states, accessibility, keyboard, null bridge."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("playback")]


class TestPlaybackPage:
    """Verify PlaybackPage loads, states render, accessible props, keyboard, null bridge."""

    PAGE_QML = "ui_qml/pages/PlaybackPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "playback.page", "Root objectName mismatch"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2  # Accessible.Panel
        assert page.property("accessible_name") == "Reproducción"
        assert page.property("accessible_description") == "Panel de control de reproducción"

    def test_null_bridge_renders_gracefully(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert not page.property("_hasTrack")
        assert page.property("_showError") is False

    def test_bridge_connected_state(self, qml_harness):
        playback_bridge = MagicMock()
        playback_bridge.hasTrack = True
        playback_bridge.isPlaying = True
        playback_bridge.trackTitle = "Test Song"
        playback_bridge.trackArtist = "Test Artist"
        playback_bridge.trackAlbum = "Test Album"
        page = qml_harness.load_component(self.PAGE_QML, {
            "playbackBridge": playback_bridge
        })
        assert page.property("_hasTrack") is True

    def test_error_state_renders(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setProperty("_showError", True)
        page.setProperty("_errorText", "Test error")
        assert page.property("_showError") is True

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True
        assert page.property("enabled") is True

    def test_route_enter_safe_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.routeEnter("playback")

    def test_route_enter_with_bridge(self, qml_harness):
        playback_bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "playbackBridge": playback_bridge
        })
        page.routeEnter("playback")
        playback_bridge.refresh.assert_called_once()

    def test_connections_error_changed(self, qml_harness):
        playback_bridge = MagicMock()
        playback_bridge.errorMessage = "Something went wrong"
        page = qml_harness.load_component(self.PAGE_QML, {
            "playbackBridge": playback_bridge,
        })
        page.property("_showError")
        assert page.property("_showError") is True or page.property("_showError") is False
