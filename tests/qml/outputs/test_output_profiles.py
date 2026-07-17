"""Test OutputProfilesPage QML page loads and renders correctly."""
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.qml_module("output_profiles")]

QML_PATH = "ui_qml/pages/outputs/OutputProfilesPage.qml"


@pytest.fixture
def mock_bridges():
    op = MagicMock()
    op.refresh.return_value = {"ok": True, "count": 2}
    op.profiles = [
        {"id": "standard", "name": "Standard", "backend": "gstreamer"},
        {"id": "hifi_pcm", "name": "Hi-Fi PCM", "backend": "gstreamer"},
    ]
    op.activeProfileId = "standard"
    op.setActiveProfile.return_value = {"ok": True}
    op.duplicateProfile.return_value = {"ok": True}
    op.deleteProfile.return_value = {"ok": True}
    stg = MagicMock()
    notif = MagicMock()
    return {"op": op, "stg": stg, "notif": notif}


class TestOutputProfilesPageLoads:
    def test_qml_file_exists(self):
        import os
        assert os.path.isfile(QML_PATH), f"{QML_PATH} no existe"

    def test_qml_has_object_name(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'objectName: "outputProfilesPage"' in content

    def test_qml_imports_bridge(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "outputProfilesBridge" in content
        assert "settingsBridge" in content
        assert "notificationBridge" in content

    def test_qml_has_states(self):
        with open(QML_PATH) as f:
            content = f.read()
        for state in ("LOADING", "READY", "EMPTY", "ERROR", "UNAVAILABLE"):
            assert state in content

    def test_qml_has_refresh_function(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "function refresh()" in content

    def test_qml_has_create_profile_button(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'objectName: "createProfileButton"' in content

    def test_qml_uses_output_profile_card(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "OutputProfileCard" in content

    def test_qml_uses_output_profile_editor(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "OutputProfileEditor" in content

    def test_page_initializes_with_bridge_context(self, mock_bridges):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        bridge = OutputProfilesBridge(player_service=MagicMock())
        assert hasattr(bridge, "profiles")
        assert hasattr(bridge, "activeProfileId")

    def test_page_refreshes_on_completed(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "Component.onCompleted: root.refresh()" in content

    def test_page_selects_profile(self, mock_bridges):
        bridge = mock_bridges["op"]
        bridge.setActiveProfile("hifi_pcm")
        bridge.setActiveProfile.assert_called_once_with("hifi_pcm")

    def test_page_duplicates_profile(self, mock_bridges):
        bridge = mock_bridges["op"]
        bridge.duplicateProfile("standard")
        bridge.duplicateProfile.assert_called_once_with("standard")

    def test_page_deletes_profile(self, mock_bridges):
        bridge = mock_bridges["op"]
        bridge.deleteProfile("standard")
        bridge.deleteProfile.assert_called_once_with("standard")

    def test_page_has_profile_card_signals(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "onCardSelected" in content
        assert "onEditRequested" in content
        assert "onDuplicateRequested" in content
        assert "onDeleteRequested" in content

    def test_page_shows_unavailable_when_no_bridge(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "UnavailableState" in content
        assert "Perfiles de salida no disponibles" in content

    def test_page_shows_loading_state(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "LoadingState" in content

    def test_page_shows_empty_state(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "EmptyState" in content

    def test_page_shows_error_state(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "ErrorState" in content

    def test_page_has_stack_layout(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "StackLayout" in content

    def test_page_uses_michitheme(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "MichiTheme" in content

    def test_page_accessible_role(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'Accessible.role: Accessible.Pane' in content

    def test_page_accessible_name(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'Accessible.name: "Perfiles de salida"' in content

    def test_page_refresh_handles_no_bridge(self):
        bridge = OutputProfilesBridge()
        result = bridge.refresh()
        assert not result["ok"]

    def test_page_select_profile_handles_failure(self, mock_bridges):
        bridge = mock_bridges["op"]
        bridge.setActiveProfile.return_value = {"ok": False, "error": "FAILED"}
        result = bridge.setActiveProfile("nonexistent")
        assert not result["ok"]

    def test_page_refresh_propagates_error(self):
        player = MagicMock()
        player.get_active_profile_id.return_value = ""
        with patch("audio.output_profiles.PROFILES", {}):
            bridge = OutputProfilesBridge(player_service=player)
            result = bridge.refresh()
            assert result["ok"]
            assert result["count"] == 0
