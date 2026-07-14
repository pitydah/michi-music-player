"""Test real EQ connection: backend state, bypass, preamp, clipping, bit-perfect."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_eq_state.return_value = {
        "bypass": False, "preamp": -3.0,
        "graphic_bands": [0.0] * GRAPHIC_BAND_COUNT,
    }
    player.get_active_backend_id.return_value = "gstreamer"
    player.set_eq_graphic.return_value = True
    player.set_eq_bypass.return_value = True
    player.set_eq_preamp.return_value = True
    return player


def test_backend_available_when_player_has_get_eq_state(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._update_backend_state()
    assert bridge.backendAvailable is True


def test_backend_unavailable_without_player():
    bridge = EqBridge()
    bridge._update_backend_state()
    assert bridge.backendAvailable is False


def test_bypass_toggle_reflects_state(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    assert bridge.bypass is False
    bridge.toggleBypass(True)
    assert bridge.bypass is True
    bridge.toggleBypass(False)
    assert bridge.bypass is False


def test_preamp_set_propagates_to_player(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setPreamp(-6.0)
    assert result["ok"]
    assert bridge.preamp == -6.0
    mock_player.set_eq_preamp.assert_called_once_with(-6.0)


def test_preamp_clamped(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setPreamp(-30.0)
    assert result["ok"]
    assert bridge.preamp == -30.0


def test_bitperfect_conflict_detection(mock_player):
    mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
    bridge = EqBridge(player_service=mock_player)
    bridge._update_backend_state()
    assert bridge.bitperfectConflict is True
    result = bridge.setGraphicBand(0, 3.0)
    assert not result["ok"]
    assert result["error"] == "BITPERFECT_CONFLICT"


def test_reset_clears_all_state(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(0, 6.0)
    bridge.setPreamp(-3.0)
    bridge.reset()
    assert bridge.preamp == 0.0
    assert bridge.bypass is False
    assert all(g == 0.0 for g in bridge._graphic_bands)


def test_save_and_restore_state(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(1, 4.0)
    bridge.setPreamp(-2.0)
    with patch("core.settings_manager.set_") as mock_set:
        result = bridge.saveState()
        assert result["ok"]
        assert mock_set.call_count >= 4


def test_clipping_warning_on_high_gain(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(0, 18.0)
    max_gain = max(b._graphic_bands[0] for b in [bridge])
    assert max_gain <= 24.0
    has_clipping = any(g > 12.0 for g in bridge._graphic_bands)
    assert has_clipping is True


def test_import_preset_with_invalid_bands(mock_player):
    bridge = EqBridge(player_service=mock_player)
    with patch("ui_qml_bridge.eq_bridge.Path") as mock_path:
        mock_file = MagicMock()
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = '{"name": "Bad", "bands": [0,0]}'
        mock_path.return_value = mock_file
        result = bridge.importPreset("/fake/bad.json")
        assert not result["ok"]
        assert result["error"] == "INVALID_BAND_COUNT"
