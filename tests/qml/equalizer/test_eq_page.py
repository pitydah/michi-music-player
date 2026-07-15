"""Tests for EQ Page — bypass, preamp, graphic bands, parametric bands, presets, clipping."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT, PARAMETRIC_BAND_COUNT

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
    player.set_eq_parametric.return_value = True
    return player


class TestEqBypass:
    def test_bypass_initial_state(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        assert bridge.bypass is False
        assert bridge.enabled is True

    def test_toggle_bypass_on(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.toggleBypass(True)
        assert result["ok"] is True
        assert bridge.bypass is True

    def test_toggle_bypass_off(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.toggleBypass(True)
        result = bridge.toggleBypass(False)
        assert result["ok"] is True
        assert bridge.bypass is False

    def test_toggle_bypass_no_player(self):
        bridge = EqBridge()
        result = bridge.toggleBypass(True)
        assert result["ok"] is False
        assert bridge.bypass is True


class TestEqPreamp:
    def test_set_preamp(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.setPreamp(-6.0)
        assert result["ok"] is True
        assert bridge.preamp == -6.0

    def test_set_preamp_positive(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setPreamp(3.5)
        assert bridge.preamp == 3.5

    def test_set_preamp_no_player(self):
        bridge = EqBridge()
        result = bridge.setPreamp(4.0)
        assert result["ok"] is False
        assert bridge.preamp == 4.0

    def test_preamp_initial_state(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        assert bridge.preamp == 0.0


class TestGraphicBands:
    def test_graphic_band_count(self):
        assert GRAPHIC_BAND_COUNT == 10

    def test_set_graphic_band(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.setGraphicBand(0, 6.0)
        assert result["ok"] is True
        assert bridge._graphic_bands[0] == 6.0

    def test_graphic_band_clamp_positive(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setGraphicBand(0, 50.0)
        assert bridge._graphic_bands[0] == 24.0

    def test_graphic_band_clamp_negative(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setGraphicBand(0, -50.0)
        assert bridge._graphic_bands[0] == -24.0

    def test_graphic_band_invalid_index(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setGraphicBand(-1, 3.0)
        assert result["ok"] is False

    def test_graphic_band_out_of_range(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setGraphicBand(GRAPHIC_BAND_COUNT, 3.0)
        assert result["ok"] is False

    def test_graphic_bands_property(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bands = bridge.graphicBands
        assert len(bands) == GRAPHIC_BAND_COUNT
        for b in bands:
            assert "freq" in b
            assert "gain" in b

    def test_graphic_band_no_player(self):
        bridge = EqBridge()
        result = bridge.setGraphicBand(0, 3.0)
        assert result["ok"] is False
        assert bridge._graphic_bands[0] == 3.0


class TestParametricBands:
    def test_parametric_band_count(self):
        assert PARAMETRIC_BAND_COUNT == 6

    def test_set_parametric_band(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.setParametricBand(0, "peaking", 100.0, -3.0, True)
        assert result["ok"] is True
        assert bridge._parametric_bands[0]["freq"] == 100.0
        assert bridge._parametric_bands[0]["gain"] == -3.0
        assert bridge._parametric_bands[0]["enabled"] is True

    def test_parametric_band_invalid_index(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setParametricBand(99, "peaking", 100.0, 0, True)
        assert result["ok"] is False

    def test_parametric_band_clamp(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setParametricBand(0, "peaking", 100.0, 50.0, True)
        assert bridge._parametric_bands[0]["gain"] == 24.0

    def test_parametric_bands_property(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bands = bridge.parametricBands
        assert len(bands) == PARAMETRIC_BAND_COUNT
        for b in bands:
            assert "freq" in b
            assert "gain" in b
            assert "q" in b
            assert "enabled" in b

    def test_parametric_band_no_player(self):
        bridge = EqBridge()
        result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
        assert result["ok"] is False
        assert bridge._parametric_bands[0]["freq"] == 500.0


class TestClipping:
    def test_no_clipping_at_flat(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        max_sum = bridge.preamp + max(bridge._graphic_bands)
        assert max_sum <= 12

    def test_clipping_detected(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setPreamp(10.0)
        bridge.setGraphicBand(0, 10.0)
        preamp = bridge.preamp
        max_band = max(bridge._graphic_bands)
        assert (preamp + max_band) > 12


class TestBitperfectConflict:
    def test_bitperfect_conflict_detected(self, mock_player):
        mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        assert bridge._bitperfect_conflict is True

    def test_bitperfect_blocks_graphic_band(self, mock_player):
        mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        result = bridge.setGraphicBand(0, 3.0)
        assert result["ok"] is False

    def test_bitperfect_blocks_parametric(self, mock_player):
        mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        result = bridge.setParametricBand(0, "peaking", 100, 0, True)
        assert result["ok"] is False

    def test_bitperfect_blocks_toggle_bypass(self, mock_player):
        mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        result = bridge.toggleBypass(True)
        assert result["ok"] is False

    def test_no_bitperfect_conflict_with_gstreamer(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        assert bridge._bitperfect_conflict is False


class TestPresets:
    def test_presets_property(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge.refresh()
        assert len(bridge.presets) > 0
        assert bridge.presets[0]["name"] != ""

    def test_current_preset_initial(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge.refresh()
        assert bridge.currentPreset != ""

    def test_apply_preset_empty_name(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.applyPreset("")
        assert result["ok"] is False

    def test_reset_to_flat(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setGraphicBand(0, 12.0)
        bridge.setPreamp(5.0)
        result = bridge.reset()
        assert result["ok"] is True
        assert all(g == 0.0 for g in bridge._graphic_bands)
        assert bridge.preamp == 0.0

    def test_save_custom_preset_empty_name(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.saveCustomPreset("")
        assert result["ok"] is False

    def test_save_state_returns_dict(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.saveState()
        assert isinstance(result, dict)
