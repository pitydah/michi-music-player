"""Tests for Output Profiles — list, create, edit, duplicate, delete, validation."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge

pytestmark = [pytest.mark.qml_module("output_profiles")]

PROFILES_MODULE = "audio.output_profiles"


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_active_profile_id.return_value = "standard"
    player.get_active_backend_id.return_value = "gstreamer"
    player.set_profile.return_value = {"ok": True}
    return player


@pytest.fixture
def profiles_dict():
    return {
        "standard": {
            "name": "Standard", "preferred_backend": "gstreamer",
            "allows_eq": True, "bitperfect": False, "dsd_mode": "pcm",
        },
        "hifi_pcm": {
            "name": "Hi-Fi PCM", "preferred_backend": "gstreamer",
            "allows_eq": True, "bitperfect": False, "dsd_mode": "pcm",
        },
        "bitperfect_pcm": {
            "name": "Bit-Perfect PCM", "preferred_backend": "gstreamer",
            "allows_eq": False, "bitperfect": True, "dsd_mode": "pcm",
        },
        "mpd_hifi": {
            "name": "MPD Hi-Fi", "preferred_backend": "mpd",
            "allows_eq": False, "bitperfect": True, "dsd_mode": "native",
        },
    }


class TestProfileList:
    def test_refresh_profiles(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.refresh()
            assert result["ok"]
            assert result["count"] == 4
            assert bridge.activeProfileId == "standard"

    def test_profile_list_contains_all(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge.refresh()
            ids = [p["id"] for p in bridge.profiles]
            assert "standard" in ids
            assert "hifi_pcm" in ids
            assert "bitperfect_pcm" in ids
            assert "mpd_hifi" in ids

    def test_profile_has_name(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge.refresh()
            for p in bridge.profiles:
                assert "name" in p
                assert "id" in p
                assert "backend" in p

    def test_refresh_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.refresh()
        assert result["ok"] is False
        assert result["error"] == "NO_PLAYER"


class TestSetActiveProfile:
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
            assert result["ok"] is False
            assert "UNKNOWN_PROFILE" in result.get("error", "")

    def test_set_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.setActiveProfile("standard")
        assert result["ok"] is False
        assert "UNSUPPORTED" in result.get("error", "")

    def test_set_profile_returns_complete_result(self, mock_player, profiles_dict):
        mock_player.set_profile.return_value = {"ok": False, "error": "FAILED"}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "standard"
            result = bridge.setActiveProfile("hifi_pcm")
            assert "requested_profile" in result
            assert "active_profile" in result
            assert "fallback" in result

    def test_requires_restart_flag(self, mock_player, profiles_dict):
        mock_player.set_profile.return_value = {
            "ok": False, "error": "NEEDS_RESTART",
            "requires_restart": True, "fallback": False,
        }
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "standard"
            result = bridge.setActiveProfile("hifi_pcm")
            assert result.get("requires_restart") is True

    def test_fallback_on_mpd_failure(self, mock_player, profiles_dict):
        mock_player.set_profile.return_value = {
            "ok": False, "error": "MPD_CONNECTION_FAILED", "fallback": True,
        }
        mock_player.get_active_profile_id.return_value = "standard"
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "standard"
            result = bridge.setActiveProfile("mpd_hifi")
            assert result["ok"] is False
            assert result["fallback"] is True

    def test_active_only_on_success(self, mock_player, profiles_dict):
        mock_player.set_profile.side_effect = [{"ok": False, "error": "FAILED"}]
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "standard"
            bridge.setActiveProfile("hifi_pcm")
            assert bridge.activeProfileId == "standard"


class TestCreateEditDuplicateDelete:
    def test_create_profile(self, mock_player, profiles_dict):
        mock_player.create_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.createProfile({"name": "Custom", "backend": "gstreamer"})
            assert result["ok"] is True

    def test_create_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.createProfile({"name": "Custom"})
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_update_profile(self, mock_player, profiles_dict):
        mock_player.update_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.updateProfile({"id": "standard", "name": "Updated"})
            assert result["ok"] is True

    def test_update_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.updateProfile({"id": "standard"})
        assert result["ok"] is False

    def test_duplicate_profile(self, mock_player, profiles_dict):
        mock_player.duplicate_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.duplicateProfile("standard")
            assert result["ok"] is True

    def test_duplicate_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.duplicateProfile("standard")
        assert result["ok"] is False

    def test_delete_profile(self, mock_player, profiles_dict):
        mock_player.delete_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            result = bridge.deleteProfile("hifi_pcm")
            assert result["ok"] is True

    def test_delete_active_profile_resets(self, mock_player, profiles_dict):
        mock_player.delete_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge._active_id = "hifi_pcm"
            bridge.deleteProfile("hifi_pcm")
            assert bridge.activeProfileId == "standard"

    def test_delete_profile_no_player(self):
        bridge = OutputProfilesBridge()
        result = bridge.deleteProfile("standard")
        assert result["ok"] is False

    def test_duplicate_profile_no_duplicate_method(self, mock_player):
        del mock_player.duplicate_profile
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.duplicateProfile("standard")
        assert result["ok"] is False


class TestValidation:
    def test_profiles_property_returns_copy(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            bridge.refresh()
            profiles = bridge.profiles
            assert len(profiles) == 4
            profiles.clear()
            assert len(bridge.profiles) == 4

    def test_data_changed_signal(self, mock_player, profiles_dict):
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            signals = []
            bridge.dataChanged.connect(lambda: signals.append(1))
            bridge.refresh()
            assert len(signals) >= 1

    def test_resolve_backend_unknown(self, mock_player):
        bridge = OutputProfilesBridge(player_service=mock_player)
        backend = bridge._resolve_backend("unknown_profile")
        assert backend == "gstreamer"

    def test_create_profile_with_data_dict(self, mock_player, profiles_dict):
        mock_player.create_profile.return_value = {"ok": True}
        with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
            bridge = OutputProfilesBridge(player_service=mock_player)
            data = {
                "name": "Test Profile",
                "description": "A test",
                "backend": "gstreamer",
                "sample_rate": 48000,
                "bit_depth": 24,
                "channels": 2,
                "exclusive_mode": True,
                "bitperfect": False,
            }
            result = bridge.createProfile(data)
            assert result["ok"] is True

    def test_refresh_with_exception(self, mock_player):
        mock_player.get_active_profile_id.side_effect = Exception("fail")
        bridge = OutputProfilesBridge(player_service=mock_player)
        with patch(f"{PROFILES_MODULE}.PROFILES", {}):
            result = bridge.refresh()
            assert result["ok"] is True
