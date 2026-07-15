from __future__ import annotations
"""CM — Output profiles: create, edit, duplicate, delete, validate, backend compatibility, select, fallback."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.isolation


class TestOutputProfiles:
    @pytest.fixture
    def mock_player(self):
        player = MagicMock()
        player.get_active_profile_id.return_value = "standard"
        player.set_profile.return_value = {"ok": True}
        return player

    @pytest.fixture
    def bridge(self, mock_player):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        return OutputProfilesBridge(player_service=mock_player)

    def test_initial_state(self, bridge):
        assert bridge.activeProfileId == "standard" or bridge.activeProfileId == ""

    def test_refresh_populates_profiles(self, bridge):
        with patch("audio.output_profiles.PROFILES", {
            "standard": {"name": "Standard", "preferred_backend": "gstreamer",
                          "allows_eq": True, "bitperfect": False, "dsd_mode": "pcm"},
            "bitperfect": {"name": "Bit-Perfect", "preferred_backend": "mpd",
                           "allows_eq": False, "bitperfect": True, "dsd_mode": "dop"},
        }):
            result = bridge.refresh()
            assert result["ok"] is True
            assert result["count"] >= 2

    def test_set_active_profile(self, bridge, mock_player):
        with patch("audio.output_profiles.PROFILES", {
            "standard": {"name": "Standard", "preferred_backend": "gstreamer",
                          "allows_eq": True, "bitperfect": False, "dsd_mode": "pcm"},
        }):
            result = bridge.setActiveProfile("standard")
            assert result["ok"] is True

    def test_set_active_profile_no_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        bridge = OutputProfilesBridge()
        result = bridge.setActiveProfile("standard")
        assert result["ok"] is False

    def test_set_active_profile_unsupported(self, bridge, mock_player):
        with patch("audio.output_profiles.PROFILES", {}):
            result = bridge.setActiveProfile("nonexistent")
            assert result["ok"] is False

    def test_duplicate_profile(self, bridge):
        bridge._player = MagicMock()
        bridge._player.duplicate_profile.return_value = {"ok": True}
        result = bridge.duplicateProfile("standard")
        assert result["ok"] is True

    def test_duplicate_profile_unsupported(self, bridge):
        bridge._player = None
        result = bridge.duplicateProfile("standard")
        assert result["ok"] is False

    def test_delete_profile(self, bridge):
        bridge._player = MagicMock()
        bridge._player.delete_profile.return_value = None
        result = bridge.deleteProfile("standard")
        assert result["ok"] is True

    def test_delete_profile_unsupported(self, bridge):
        bridge._player = None
        result = bridge.deleteProfile("standard")
        assert result["ok"] is False

    def test_create_profile(self, bridge):
        bridge._player = MagicMock()
        bridge._player.create_profile.return_value = None
        result = bridge.createProfile({"name": "Custom"})
        assert result["ok"] is True

    def test_create_profile_unsupported(self, bridge):
        bridge._player = None
        result = bridge.createProfile({"name": "Custom"})
        assert result["ok"] is False

    def test_update_profile(self, bridge):
        bridge._player = MagicMock()
        bridge._player.update_profile.return_value = None
        result = bridge.updateProfile({"id": "standard", "name": "Updated"})
        assert result["ok"] is True

    def test_update_profile_unsupported(self, bridge):
        bridge._player = None
        result = bridge.updateProfile({"id": "standard"})
        assert result["ok"] is False
