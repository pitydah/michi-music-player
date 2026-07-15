"""Test EqBridge applied-state correctness: UI must reflect APPLIED state, not requested value."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT
pytestmark = [pytest.mark.qml_module("eq_dsp")]


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_eq_state.return_value = {
        "bypass": False, "preamp": 0.0,
        "graphic_bands": [0.0] * GRAPHIC_BAND_COUNT,
    }
    player.get_active_backend_id.return_value = "gstreamer"
    player.set_eq_graphic.return_value = True
    player.set_eq_bypass.return_value = True
    player.set_eq_preamp.return_value = True
    return player


def test_preamp_set_on_backend_success(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setPreamp(3.0)
    assert result["ok"] is True
    assert bridge.preamp == 3.0


def test_preamp_set_no_player():
    bridge = EqBridge()
    result = bridge.setPreamp(5.0)
    assert result["ok"] is False
    assert bridge.preamp == 5.0


def test_graphic_band_set_on_backend_success(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setGraphicBand(2, 8.0)
    assert result["ok"] is True
    assert bridge._graphic_bands[2] == 8.0


def test_graphic_band_set_no_player():
    bridge = EqBridge()
    result = bridge.setGraphicBand(0, 6.0)
    assert result["ok"] is False
    assert bridge._graphic_bands[0] == 6.0


def test_bypass_toggle_on_backend_success(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    assert bridge.bypass is False
    result = bridge.toggleBypass(True)
    assert result["ok"] is True
    assert bridge.bypass is True


def test_bypass_toggle_no_player():
    bridge = EqBridge()
    result = bridge.toggleBypass(True)
    assert result["ok"] is False
    assert bridge.bypass is True


def test_parametric_band_update(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
    assert result["ok"] is True
    assert bridge._parametric_bands[0]["freq"] == 500.0
    assert bridge._parametric_bands[0]["gain"] == -6.0


def test_parametric_band_no_player():
    bridge = EqBridge()
    result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
    assert result["ok"] is False
    assert bridge._parametric_bands[0]["freq"] == 500.0


def test_graphic_band_clamps_at_24(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(0, 30.0)
    assert bridge._graphic_bands[0] == 24.0


def test_graphic_band_clamps_at_negative_24(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(0, -30.0)
    assert bridge._graphic_bands[0] == -24.0
