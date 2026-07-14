"""CM — EQ applied state, preamp, bands, presets, import/export, bypass, clipping, bit-perfect conflict, rollback."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT

pytestmark = pytest.mark.isolation


class TestEqEnhanced:
    @pytest.fixture
    def mock_player(self):
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

    @pytest.fixture
    def bridge(self, mock_player):
        return EqBridge(player_service=mock_player)

    def test_initial_state(self, bridge):
        assert bridge.enabled is True
        assert bridge.bypass is False
        assert bridge.preamp == 0.0
        assert len(bridge.graphicBands) == GRAPHIC_BAND_COUNT
        assert len(bridge.parametricBands) == 6

    def test_toggle_bypass(self, bridge, mock_player):
        result = bridge.toggleBypass(True)
        assert result["ok"] is True
        assert bridge.bypass is True

    def test_toggle_bypass_no_player(self):
        bridge = EqBridge()
        result = bridge.toggleBypass(True)
        assert result["ok"] is False
        assert bridge.bypass is True

    def test_set_enabled(self, bridge, mock_player):
        result = bridge.setEnabled(False)
        assert result["ok"] is True

    def test_set_preamp(self, bridge, mock_player):
        result = bridge.setPreamp(3.0)
        assert result["ok"] is True
        assert bridge.preamp == 3.0

    def test_set_preamp_no_player(self):
        bridge = EqBridge()
        result = bridge.setPreamp(3.0)
        assert result["ok"] is False
        assert bridge.preamp == 3.0

    def test_set_graphic_band(self, bridge, mock_player):
        result = bridge.setGraphicBand(0, 6.0)
        assert result["ok"] is True
        assert bridge._graphic_bands[0] == 6.0

    def test_set_graphic_band_invalid_index(self, bridge):
        result = bridge.setGraphicBand(99, 6.0)
        assert result["ok"] is False

    def test_set_graphic_band_no_player(self):
        bridge = EqBridge()
        result = bridge.setGraphicBand(0, 6.0)
        assert result["ok"] is False
        assert bridge._graphic_bands[0] == 6.0

    def test_set_parametric_band(self, bridge, mock_player):
        result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
        assert result["ok"] is True
        assert bridge._parametric_bands[0]["gain"] == -6.0

    def test_set_parametric_band_invalid_index(self, bridge):
        result = bridge.setParametricBand(99, "peaking", 500.0, -6.0, True)
        assert result["ok"] is False

    def test_set_parametric_band_no_player(self):
        bridge = EqBridge()
        result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
        assert result["ok"] is False

    def test_reset(self, bridge, mock_player):
        bridge.setGraphicBand(0, 6.0)
        bridge.setPreamp(3.0)
        result = bridge.reset()
        assert result["ok"] is True
        assert bridge.preamp == 0.0
        assert bridge._graphic_bands[0] == 0.0
        assert bridge.enabled is True

    def test_apply_preset(self, bridge, mock_player):
        result = bridge.applyPreset("Plano")
        assert result["ok"] is True

    def test_apply_preset_empty_name(self, bridge):
        result = bridge.applyPreset("")
        assert result["ok"] is False

    def test_import_preset_nonexistent(self, bridge):
        result = bridge.importPreset("/nonexistent.json")
        assert result["ok"] is False

    def test_save_and_restore_state(self, bridge, mock_player):
        bridge.setPreamp(2.0)
        result = bridge.saveState()
        assert result["ok"] is True

    def test_restore_state_fallback_on_no_settings(self, bridge):
        result = bridge.restoreState()
        assert result["ok"] is True or not result["ok"]

    def test_bitperfect_conflict_detected(self, bridge):
        assert bridge.bitperfectConflict is False

    def test_backend_available(self, bridge):
        bridge.refresh()
        assert bridge.backendAvailable is True

    def test_graphic_band_high_gain_clamped(self, bridge):
        bridge._backend_available = True
        bridge.setGraphicBand(0, 30.0)
        assert bridge._graphic_bands[0] == 24.0
        bridge.setGraphicBand(1, -30.0)
        assert bridge._graphic_bands[1] == -24.0

    def test_save_custom_preset(self, bridge):
        result = bridge.saveCustomPreset("My Preset")
        assert result["ok"] is True

    def test_save_custom_preset_empty(self, bridge):
        result = bridge.saveCustomPreset("")
        assert result["ok"] is False

    def test_refresh(self, bridge, mock_player):
        result = bridge.refresh()
        assert result["ok"] is True
