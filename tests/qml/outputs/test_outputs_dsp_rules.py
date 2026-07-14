"""Test output profile DSP rules: backend compatibility, fallback, bit-perfect, EQ blocking."""

from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge

PROFILES_MODULE = "audio.output_profiles"


@pytest.fixture
def profiles_dict():
    return {
        "standard": {
            "name": "Standard", "preferred_backend": "gstreamer",
            "allows_eq": True, "bitperfect": False,
        },
        "bitperfect_pcm": {
            "name": "Bit-Perfect PCM", "preferred_backend": "gstreamer",
            "allows_eq": False, "bitperfect": True,
        },
        "mpd_hifi": {
            "name": "MPD Hi-Fi", "preferred_backend": "mpd",
            "allows_eq": False, "bitperfect": True,
        },
    }


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_active_profile_id.return_value = "standard"
    player.get_active_backend_id.return_value = "gstreamer"
    return player


def test_eq_blocked_on_bitperfect_profile(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        bp = [p for p in bridge.profiles if p["id"] == "bitperfect_pcm"][0]
        assert bp.get("bitperfect") is True
        assert bp.get("allows_eq") is False or bp.get("allows_eq") is False


def test_eq_allowed_on_standard_profile(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        std = [p for p in bridge.profiles if p["id"] == "standard"][0]
        assert std.get("allows_eq") is True


def test_backend_compatibility_gstreamer(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        for p in bridge.profiles:
            assert p.get("backend") in ("gstreamer", "mpd")


def test_backend_compatibility_mpd(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        mpd = [p for p in bridge.profiles if p["id"] == "mpd_hifi"][0]
        assert mpd.get("backend") == "mpd"


def test_fallback_on_bitperfect_failure(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {
        "ok": False, "error": "MPD_FAILED",
        "fallback": True, "requires_restart": False,
    }
    mock_player.get_active_profile_id.return_value = "standard"
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.setActiveProfile("mpd_hifi")
        assert result["fallback"] is True
        assert result["active_profile"] == "standard"


def test_profile_switch_returns_backend_info(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.setActiveProfile("bitperfect_pcm")
        assert "requested_backend" in result
        assert "active_backend" in result


def test_duplicate_profile_preserves_dsp_rules(mock_player, profiles_dict):
    mock_player.duplicate_profile.return_value = {"ok": True}
    mock_player.get_active_profile_id.return_value = "standard"
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        result = bridge.duplicateProfile("standard")
        assert result["ok"]


def test_create_profile_with_dsp_fields(mock_player, profiles_dict):
    mock_player.create_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.createProfile({
            "name": "Custom", "backend": "gstreamer",
            "allows_eq": True, "bitperfect": False,
        })
        assert result["ok"]
        mock_player.create_profile.assert_called_once_with({
            "name": "Custom", "backend": "gstreamer",
            "allows_eq": True, "bitperfect": False,
        })


def test_delete_profile_fallback_to_standard(mock_player, profiles_dict):
    mock_player.delete_profile.return_value = True
    mock_player.get_active_profile_id.return_value = "standard"
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "mpd_hifi"
        result = bridge.deleteProfile("mpd_hifi")
        assert result["ok"]
        assert bridge.activeProfileId == "standard"
