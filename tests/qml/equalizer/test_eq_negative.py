"""Negative and edge-case tests for EQ Bridge."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT

pytestmark = [pytest.mark.qml_module("eq_dsp"), pytest.mark.qml_dimension("negative")]


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_eq_state.return_value = {
        "bypass": False, "preamp": 0.0,
        "graphic_bands": [0.0] * GRAPHIC_BAND_COUNT,
    }
    player.get_active_backend_id.return_value = "gstreamer"
    return player


class TestEqNegative:
    def test_no_player_on_init(self):
        bridge = EqBridge()
        assert bridge.backendAvailable is False

    def test_apply_preset_with_bitperfect_block(self, mock_player):
        mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        result = bridge.applyPreset("Rock")
        assert result["ok"] is False
        assert "BITPERFECT_CONFLICT" in result.get("error", "")

    def test_set_parametric_band_negative_clamp(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setParametricBand(0, "peaking", 100, -50.0, True)
        assert bridge._parametric_bands[0]["gain"] == -24.0

    def test_export_preset_invalid_path(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.exportPreset("")
        assert result["ok"] is False

    def test_import_preset_nonexistent_file(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.importPreset("/nonexistent/preset.json")
        assert result["ok"] is False

    def test_set_enabled_with_bitperfect(self, mock_player):
        mock_player.get_active_backend_id.return_value = "michi_hifi_mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        result = bridge.setEnabled(True)
        assert result["ok"] is False

    def test_refresh_on_empty_presets(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        with pytest.MonkeyPatch().context() as m:
            import audio.eq_presets as ep
            m.setattr(ep, 'get_preset_names', lambda: [])
            bridge.refresh()
        assert len(bridge.presets) == 0

    def test_graphic_band_index_out_of_range_negative(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setGraphicBand(-5, 3.0)
        assert result["ok"] is False
        assert result["error"] == "INVALID_INDEX"

    def test_graphic_band_index_exact_boundary(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setGraphicBand(10, 3.0)
        assert result["ok"] is False

    def test_parametric_band_index_out_of_range(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setParametricBand(-1, "peaking", 100, 0, True)
        assert result["ok"] is False

    def test_parametric_band_index_exact_boundary(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setParametricBand(6, "peaking", 100, 0, True)
        assert result["ok"] is False

    def test_save_custom_preset_no_player(self):
        bridge = EqBridge()
        result = bridge.saveCustomPreset("My Preset")
        assert isinstance(result, dict)

    def test_restore_state_empty_bands(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        with pytest.MonkeyPatch().context() as m:
            import core.settings_manager as sm
            m.setattr(sm, 'get', lambda key, default=None: "[]" if "bands" in key else default)
            result = bridge.restoreState()
            assert result["ok"] is True

    def test_update_backend_state_no_player(self):
        bridge = EqBridge()
        bridge._player = None
        bridge._update_backend_state()
        assert bridge.backendAvailable is False

    def test_toggle_bypass_when_disabled(self):
        bridge = EqBridge()
        bridge._backend_available = False
        result = bridge.toggleBypass(False)
        assert result["ok"] is False
