"""Test output profile operations through OutputProfilesBridge."""
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
    }


def test_refresh_profiles(mock_player, profiles_dict):
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.refresh()
        assert result["ok"]
        assert result["count"] == 3
        assert bridge.activeProfileId == "standard"


def test_set_valid_profile(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.setActiveProfile("hifi_pcm")
        assert result["ok"]
        assert result["active_profile"] == "hifi_pcm"


def test_invalid_profile(mock_player, profiles_dict):
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.setActiveProfile("nonexistent")
        assert not result["ok"]
        assert "UNKNOWN_PROFILE" in str(result.get("error", ""))


def test_set_profile_no_player():
    bridge = OutputProfilesBridge()
    result = bridge.setActiveProfile("standard")
    assert not result["ok"]
    assert "UNSUPPORTED" in str(result.get("error", ""))


def test_refresh_no_player():
    bridge = OutputProfilesBridge()
    result = bridge.refresh()
    assert not result["ok"]
    assert result["error"] == "NO_PLAYER"


def test_fallback_on_mpd_failure(mock_player, profiles_dict):
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


def test_profile_switch_returns_complete_result(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": False, "error": "FAILED"}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.setActiveProfile("hifi_pcm")
        assert "requested_profile" in result
        assert "active_profile" in result
        assert "fallback" in result


def test_profile_list_includes_all_profiles(mock_player, profiles_dict):
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        ids = [p["id"] for p in bridge.profiles]
        assert "standard" in ids
        assert "hifi_pcm" in ids
        assert "bitperfect_pcm" in ids


def test_set_active_only_on_success(mock_player, profiles_dict):
    mock_player.set_profile.side_effect = [
        {"ok": False, "error": "FAILED"},
    ]
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        bridge.setActiveProfile("hifi_pcm")
        assert bridge.activeProfileId == "standard"


def test_requires_restart_flag(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {
        "ok": False, "error": "NEEDS_RESTART", "requires_restart": True, "fallback": False,
    }
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.setActiveProfile("hifi_pcm")
        assert result.get("requires_restart") is True
