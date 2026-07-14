"""Test EqBridge applied-state correctness: UI must reflect APPLIED state, not requested value."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT


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


def test_preamp_rollback_on_backend_failure(mock_player):
    mock_player.set_eq_preamp.side_effect = RuntimeError("Backend denied")
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setPreamp(3.0)
    assert bridge.preamp == 0.0


def test_preamp_rollback_on_no_player():
    bridge = EqBridge()
    bridge.setPreamp(5.0)
    assert bridge.preamp == 0.0


def test_graphic_band_rollback_on_backend_failure(mock_player):
    mock_player.set_eq_graphic.side_effect = RuntimeError("Backend denied")
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(2, 8.0)
    assert bridge._graphic_bands[2] == 0.0


def test_graphic_band_rollback_on_no_player():
    bridge = EqBridge()
    bridge.setGraphicBand(0, 6.0)
    assert bridge._graphic_bands[0] == 0.0


def test_bypass_rollback_on_backend_failure(mock_player):
    mock_player.set_eq_bypass.side_effect = RuntimeError("Backend denied")
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    assert bridge.bypass is False
    bridge.toggleBypass(True)
    assert bridge.bypass is False


def test_bypass_rollback_on_no_player():
    bridge = EqBridge()
    bridge.toggleBypass(True)
    assert bridge.bypass is False


def test_parametric_band_rollback_on_backend_failure(mock_player):
    mock_player.set_eq_parametric.side_effect = RuntimeError("Backend denied")
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    old = dict(bridge._parametric_bands[0])
    bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
    assert bridge._parametric_bands[0]["freq"] == old["freq"]
    assert bridge._parametric_bands[0]["gain"] == old["gain"]


def test_parametric_band_rollback_on_no_player():
    bridge = EqBridge()
    old = dict(bridge._parametric_bands[0])
    bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
    assert bridge._parametric_bands[0]["freq"] == old["freq"]


def test_clipping_warning_true_on_high_gain(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(0, 18.0)
    assert bridge.clippingWarning is True


def test_clipping_warning_false_on_low_gain(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge.setGraphicBand(0, 3.0)
    assert bridge.clippingWarning is False


def test_clipping_warning_from_preamp(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    bridge._preamp = 15.0
    assert bridge.clippingWarning is True
