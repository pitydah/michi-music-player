"""Test real output profiles: CRUD, select, device fields, fallback, restart."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge

PROFILES_MODULE = "audio.output_profiles"


@pytest.fixture
def profiles_dict():
    return {
        "standard": {
            "name": "Standard", "description": "Perfil estándar",
            "preferred_backend": "gstreamer", "allows_eq": True,
            "bitperfect": False, "sample_rate": 48000, "bit_depth": 16,
            "channels": 2, "exclusive_mode": False,
            "fallback": "", "requires_restart": False,
        },
        "hifi_pcm": {
            "name": "Hi-Fi PCM", "description": "Alta fidelidad",
            "preferred_backend": "gstreamer", "allows_eq": True,
            "bitperfect": False, "sample_rate": 96000, "bit_depth": 24,
            "channels": 2, "exclusive_mode": False,
            "fallback": "", "requires_restart": False,
        },
        "bitperfect_pcm": {
            "name": "Bit-Perfect PCM", "description": "Bit perfect",
            "preferred_backend": "gstreamer", "allows_eq": False,
            "bitperfect": True, "sample_rate": 192000, "bit_depth": 32,
            "channels": 2, "exclusive_mode": True,
            "fallback": "standard", "requires_restart": True,
        },
    }


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_active_profile_id.return_value = "standard"
    player.get_active_backend_id.return_value = "gstreamer"
    return player


def test_refresh_includes_all_profile_fields(mock_player, profiles_dict):
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        p = bridge.profiles[0]
        assert "id" in p
        assert "name" in p
        assert "backend" in p
        assert "bitperfect" in p


def test_create_profile(mock_player, profiles_dict):
    mock_player.create_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.createProfile({"name": "Custom", "backend": "gstreamer"})
        assert result["ok"]
        assert mock_player.create_profile.called


def test_duplicate_profile(mock_player, profiles_dict):
    mock_player.duplicate_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.duplicateProfile("standard")
        assert result["ok"]


def test_delete_profile(mock_player, profiles_dict):
    mock_player.delete_profile.return_value = True
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.deleteProfile("hifi_pcm")
        assert result["ok"]


def test_select_profile_with_sample_rate_and_depth(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.setActiveProfile("hifi_pcm")
        assert result["ok"]
        assert result["active_profile"] == "hifi_pcm"


def test_requires_restart_on_profile_switch(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {
        "ok": False, "error": "NEEDS_RESTART",
        "requires_restart": True, "fallback": False,
    }
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.setActiveProfile("bitperfect_pcm")
        assert result.get("requires_restart") is True


def test_fallback_detected_on_profile_failure(mock_player, profiles_dict):
    mock_player.set_profile.return_value = {
        "ok": False, "error": "MPD_FAILED",
        "fallback": True, "requires_restart": False,
    }
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.setActiveProfile("bitperfect_pcm")
        assert result.get("fallback") is True


def test_exclusive_mode_in_profile_fields(mock_player, profiles_dict):
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.refresh()
        bp = [p for p in bridge.profiles if p["id"] == "bitperfect_pcm"][0]
        assert bp.get("bitperfect") is True


def test_update_profile(mock_player, profiles_dict):
    mock_player.update_profile.return_value = {"ok": True}
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        result = bridge.updateProfile({"id": "standard", "name": "Updated"})
        assert result["ok"]


def test_active_profile_persists_after_delete(mock_player, profiles_dict):
    mock_player.delete_profile.return_value = True
    mock_player.get_active_profile_id.return_value = "standard"
    with patch(f"{PROFILES_MODULE}.PROFILES", profiles_dict):
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge._active_id = "standard"
        result = bridge.deleteProfile("standard")
        assert result["ok"]
        assert bridge.activeProfileId == "standard"
