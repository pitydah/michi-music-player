"""Integration tests for PlaylistsPage UI: states, accessibility, keyboard, null bridge."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("playlists")]


class TestPlaylistsPage:
    """Verify PlaylistsPage, PlaylistCard, PlaylistEditorDialog, etc."""

    PAGE_QML = "ui_qml/pages/playlists/PlaylistsPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "playlists.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Playlists"
        assert page.property("accessible_description") == "Gestión de listas de reproducción"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("pl") is None
        assert page.property("_state") == "LOADING"

    def test_bridge_connected_empty(self, qml_harness):
        bridge = MagicMock()
        bridge.playlists = []
        page = qml_harness.load_component(self.PAGE_QML, {
            "playlistsBridge": bridge
        })
        assert page.property("pl") is not None

    def test_unavailable_state_shown(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("pl") is None

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True

    def test_get_filtered_playlists_empty(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        result = page.getFilteredPlaylists()
        assert result == []

    def test_bridge_refresh_on_completed(self, qml_harness):
        bridge = MagicMock()
        bridge.playlists = []
        page = qml_harness.load_component(self.PAGE_QML, {
            "playlistsBridge": bridge
        })
        assert page.property("_state") == "EMPTY"
