"""Test EQ band operations through EqBridge."""
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
    return player


def test_band_count():
    assert GRAPHIC_BAND_COUNT == 10


def test_set_graphic_band_valid(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setGraphicBand(0, 6.0)
    assert result["ok"]
    assert bridge._graphic_bands[0] == 6.0


def test_set_graphic_band_clamped(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setGraphicBand(0, 50.0)
    assert result["ok"]
    assert bridge._graphic_bands[0] == 24.0


def test_set_graphic_band_invalid_index(mock_player):
    bridge = EqBridge(player_service=mock_player)
    result = bridge.setGraphicBand(-1, 3.0)
    assert not result["ok"]
    assert result["error"] == "INVALID_INDEX"


def test_set_graphic_band_out_of_range(mock_player):
    bridge = EqBridge(player_service=mock_player)
    result = bridge.setGraphicBand(GRAPHIC_BAND_COUNT + 5, 3.0)
    assert not result["ok"]
    assert result["error"] == "INVALID_INDEX"


def test_set_parametric_band_valid(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    result = bridge.setParametricBand(0, "peaking", 100.0, -3.0, True)
    assert result["ok"]
    assert bridge._parametric_bands[0]["freq"] == 100.0
    assert bridge._parametric_bands[0]["gain"] == -3.0
    assert bridge._parametric_bands[0]["enabled"] is True


def test_set_parametric_band_invalid_index(mock_player):
    bridge = EqBridge(player_service=mock_player)
    result = bridge.setParametricBand(99, "peaking", 100.0, 0, True)
    assert not result["ok"]
    assert result["error"] == "INVALID_INDEX"


def test_set_graphic_band_bitperfect_blocked(mock_player):
    mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
    bridge = EqBridge(player_service=mock_player)
    bridge._update_backend_state()
    assert bridge._bitperfect_conflict
    result = bridge.setGraphicBand(0, 3.0)
    assert not result["ok"]


def test_graphic_bands_property(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bands = bridge.graphicBands
    assert len(bands) == GRAPHIC_BAND_COUNT
    for b in bands:
        assert "freq" in b
        assert "gain" in b
