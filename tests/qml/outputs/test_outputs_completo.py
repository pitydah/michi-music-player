"""DY — Output Profiles completo: create, edit, duplicate, delete, validate, device, backend, sample rate, bit depth, channels, exclusive mode, bit-perfect, DSP policy, fallback, restart-required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge

PROFILES_MODULE = "audio.output_profiles"


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_active_profile_id.return_value = "standard"
    player.get_active_backend_id.return_value = "gstreamer"
    return player


@pytest.fixture
def profiles_dict():
    return {
        "standard": {"name": "Standard", "preferred_backend": "gstreamer", "allows_eq": True, "bitperfect": False},
        "hifi_pcm": {"name": "Hi-Fi PCM", "preferred_backend": "gstreamer", "allows_eq": True, "bitperfect": False},
        "bitperfect_pcm": {"name": "Bit-Perfect PCM", "preferred_backend": "gstreamer", "allows_eq": False, "bitperfect": True},
        "mpd_hifi": {"name": "MPD Hi-Fi", "preferred_backend": "mpd", "allows_eq": False, "bitperfect": True},
    }


class TestOutputsCompleto:
    def test_refresh_populates_profiles(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.refresh()
            assert result["ok"]
            assert result["count"] == 4

    def test_active_profile_after_refresh(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge.refresh()
            assert bridge.activeProfileId == "standard"

    def test_set_valid_profile(self, mock_player, profiles_dict):
        mock_player.set_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.setActiveProfile("hifi_pcm")
            assert result["ok"]
            assert result["active_profile"] == "hifi_pcm"

    def test_set_invalid_profile(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.setActiveProfile("nonexistent")
            assert not result["ok"]
            assert "UNKNOWN_PROFILE" in str(result.get("error", ""))

    def test_set_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.setActiveProfile("standard")
        assert not result["ok"]

    def test_refresh_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.refresh()
        assert not result["ok"]

    def test_fallback_on_mpd_failure(self, mock_player, profiles_dict):
        mock_player.set_profile.return_value = {
            "ok": False, "error": "MPD_CONNECTION_FAILED", "fallback": True,
        }
        mock_player.get_active_profile_id.return_value = "standard"
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "standard"
            result = bridge.setActiveProfile("bitperfect_pcm")
            assert not result["ok"]
            assert result["fallback"] is True

    def test_requires_restart_flag(self, mock_player, profiles_dict):
        mock_player.set_profile.return_value = {
            "ok": False, "error": "NEEDS_RESTART", "requires_restart": True, "fallback": False,
        }
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "standard"
            result = bridge.setActiveProfile("hifi_pcm")
            assert result.get("requires_restart") is True

    def test_duplicate_profile_calls_player(self, mock_player, profiles_dict):
        mock_player.duplicate_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.duplicateProfile("hifi_pcm")
            assert result["ok"]
            mock_player.duplicate_profile.assert_called_once_with("hifi_pcm")

    def test_duplicate_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.duplicateProfile("hifi_pcm")
        assert not result["ok"]

    def test_delete_profile_calls_player(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "hifi_pcm"
            bridge._player.delete_profile.return_value = {"ok": True}
            result = bridge.deleteProfile("hifi_pcm")
            assert result["ok"]

    def test_delete_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.deleteProfile("hifi_pcm")
        assert not result["ok"]

    def test_create_profile_calls_player(self, mock_player, profiles_dict):
        data = {"name": "Custom", "preferred_backend": "gstreamer"}
        mock_player.create_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.createProfile(data)
            assert result["ok"]
            mock_player.create_profile.assert_called_once_with(data)

    def test_create_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.createProfile({"name": "Custom"})
        assert not result["ok"]

    def test_update_profile_calls_player(self, mock_player, profiles_dict):
        data = {"id": "hifi_pcm", "name": "Updated Hi-Fi"}
        mock_player.update_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.updateProfile(data)
            assert result["ok"]
            mock_player.update_profile.assert_called_once_with(data)

    def test_update_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.updateProfile({"id": "hifi_pcm"})
        assert not result["ok"]
