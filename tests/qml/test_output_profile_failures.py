"""Test OutputProfilesBridge with profile switching failures and fallback propagation."""
import pytest
from unittest.mock import MagicMock, patch

from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_active_profile_id.return_value = "standard"
    player.get_active_backend_id.return_value = "gstreamer"
    return player


def test_refresh_profiles(mock_player):
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] >= 9
    assert bridge.activeProfileId == "standard"


def test_set_valid_profile(mock_player):
    mock_player.set_profile.return_value = {"ok": True}
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.setActiveProfile("hifi_pcm")
    assert result["ok"]
    assert result["requested_profile"] == "hifi_pcm"
    assert result["active_profile"] == "hifi_pcm"
    assert result["fallback"] is False


def test_invalid_profile(mock_player):
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.setActiveProfile("nonexistent_profile")
    assert not result["ok"]
    assert result["error"] == "UNKNOWN_PROFILE"


def test_mpd_unavailable_fallback(mock_player):
    mock_player.set_profile.return_value = {
        "ok": False, "error": "MPD_CONNECTION_FAILED"
    }
    mock_player.get_active_profile_id.return_value = "standard"
    bridge = OutputProfilesBridge(player_service=mock_player)
    bridge._active_id = "standard"
    result = bridge.setActiveProfile("michi_hifi_mpd")
    assert not result["ok"]
    assert result["fallback"] is True
    assert result["active_profile"] == "standard"


def test_fallback_detection(mock_player):
    mock_player.set_profile.return_value = {"ok": False, "error": "BACKEND_FAILED"}
    mock_player.get_active_profile_id.return_value = "standard"
    bridge = OutputProfilesBridge(player_service=mock_player)
    bridge._active_id = "standard"
    result = bridge.setActiveProfile("michi_bitperfect_mpd")
    assert not result["ok"]
    assert result["fallback"] is True


def test_gstreamer_profile(mock_player):
    mock_player.set_profile.return_value = {"ok": True}
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.setActiveProfile("studio_monitor")
    assert result["ok"]
    assert result["requested_backend"] in ("auto", "gstreamer")


def test_hifi_profile(mock_player):
    mock_player.set_profile.return_value = {"ok": True}
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.setActiveProfile("hifi_pcm")
    assert result["ok"]
    assert "fallback" in result


def test_bitperfect_profile(mock_player):
    mock_player.set_profile.return_value = {"ok": True}
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.setActiveProfile("bitperfect_pcm")
    assert result["ok"]
    from audio.output_profiles import PROFILES
    assert PROFILES["bitperfect_pcm"].bitperfect is True


def test_dsd_profile(mock_player):
    mock_player.set_profile.return_value = {"ok": True}
    bridge = OutputProfilesBridge(player_service=mock_player)
    result = bridge.setActiveProfile("dsd_to_pcm")
    assert result["ok"]
    from audio.output_profiles import PROFILES
    assert PROFILES["dsd_to_pcm"].dsd_mode == "pcm"


def test_refresh_no_player():
    bridge = OutputProfilesBridge()
    result = bridge.refresh()
    assert not result["ok"]
    assert result["error"] == "NO_PLAYER"


def test_set_profile_no_player():
    bridge = OutputProfilesBridge()
    result = bridge.setActiveProfile("standard")
    assert not result["ok"]
    assert result["error"] == "UNSUPPORTED"


def test_profile_switch_returns_complete_result(mock_player):
    mock_player.set_profile.return_value = {"ok": False, "error": "MPD_CONNECTION_FAILED"}
    mock_player.get_active_profile_id.return_value = "standard"
    bridge = OutputProfilesBridge(player_service=mock_player)
    bridge._active_id = "standard"
    result = bridge.setActiveProfile("michi_dsd_mpd")
    assert "requested_profile" in result
    assert "active_profile" in result
    assert "requested_backend" in result
    assert "active_backend" in result
    assert "fallback" in result


def test_set_active_only_on_success(mock_player):
    mock_player.set_profile.side_effect = [
        {"ok": False, "error": "FAILED"},
        {"ok": True},
    ]
    bridge = OutputProfilesBridge(player_service=mock_player)
    bridge._active_id = "standard"
    bridge.setActiveProfile("hifi_pcm")
    assert bridge.activeProfileId == "standard"


def test_persistence_sync(mock_player):
    with patch("core.settings_manager.set_"):
        mock_player.set_profile.return_value = {"ok": True}
        bridge = OutputProfilesBridge(player_service=mock_player)
        bridge.setActiveProfile("bitperfect_pcm")
        assert bridge.activeProfileId == "bitperfect_pcm"
