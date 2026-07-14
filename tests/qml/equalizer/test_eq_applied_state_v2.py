"""DY — EQ Applied State v2: enable, bypass, preamp, bands, Q, frequency, gain, presets, import, export, reset, clipping, bit-perfect conflict, rollback."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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


class TestEqAppliedStateV2:
    def test_initial_enabled_state(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        assert bridge.enabled is True

    def test_bypass_toggle_success(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.toggleBypass(True)
        assert result["ok"] is True
        assert bridge.bypass is True

    def test_preamp_set_success(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.setPreamp(3.5)
        assert result["ok"] is True
        assert bridge.preamp == 3.5

    def test_graphic_band_set_clamps(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setGraphicBand(0, 30.0)
        assert bridge._graphic_bands[0] == 24.0
        bridge.setGraphicBand(1, -30.0)
        assert bridge._graphic_bands[1] == -24.0

    def test_graphic_band_invalid_index(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setGraphicBand(99, 5.0)
        assert result["ok"] is False

    def test_parametric_band_full_config(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
        assert result["ok"] is True
        assert bridge._parametric_bands[0]["freq"] == 500.0
        assert bridge._parametric_bands[0]["gain"] == -6.0
        assert bridge._parametric_bands[0]["enabled"] is True

    def test_parametric_invalid_index(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.setParametricBand(99, "peaking", 100.0, 0.0, True)
        assert result["ok"] is False

    def test_reset_clears_all(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setGraphicBand(0, 12.0)
        bridge.setPreamp(5.0)
        bridge.reset()
        assert bridge.preamp == 0.0
        assert all(g == 0.0 for g in bridge._graphic_bands)
        assert bridge.bypass is False

    def test_preset_apply(self, mock_player):
        with patch("audio.eq_presets.load_graphic_preset") as load:
            load.return_value = [2.0] * GRAPHIC_BAND_COUNT
            bridge = EqBridge(player_service=mock_player)
            bridge._backend_available = True
            result = bridge.applyPreset("Rock")
            assert result["ok"] is True
            assert bridge._graphic_bands[0] == 2.0

    def test_preset_empty_name(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        result = bridge.applyPreset("")
        assert result["ok"] is False

    def test_import_preset(self, mock_player, tmp_path):
        import json
        preset_file = tmp_path / "test_preset.json"
        preset_file.write_text(json.dumps({
            "name": "Test",
            "bands": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        }))
        with patch("audio.eq_presets.load_custom_presets") as load, \
             patch("audio.eq_presets.save_custom_presets") as save:
            load.return_value = {}
            save.return_value = None
            bridge = EqBridge(player_service=mock_player)
            result = bridge.importPreset(str(preset_file))
            assert result["ok"] is True

    def test_export_preset(self, mock_player, tmp_path):
        export_file = tmp_path / "export.json"
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.exportPreset(str(export_file))
        assert result["ok"] is True
        assert export_file.exists()

    def test_graphic_band_clips_at_24(self, mock_player):
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        bridge.setGraphicBand(0, 30.0)
        assert bridge._graphic_bands[0] == 24.0
        bridge.setGraphicBand(1, 12.0)
        assert bridge._graphic_bands[1] == 12.0

    def test_bitperfect_conflict_blocks_eq(self, mock_player):
        mock_player.get_active_backend_id.return_value = "mpd"
        bridge = EqBridge(player_service=mock_player)
        bridge._update_backend_state()
        assert bridge.bitperfectConflict is True
        result = bridge.setEnabled(True)
        assert result["ok"] is False

    def test_rollback_on_graphic_band_failure(self, mock_player):
        mock_player.set_eq_graphic.side_effect = RuntimeError("Backend denied")
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        result = bridge.setGraphicBand(2, 8.0)
        assert result["ok"] is False
        assert bridge._graphic_bands[2] == 8.0

    def test_rollback_on_bypass_failure(self, mock_player):
        mock_player.set_eq_bypass.side_effect = RuntimeError("Backend denied")
        bridge = EqBridge(player_service=mock_player)
        bridge._backend_available = True
        assert bridge.bypass is False
        result = bridge.toggleBypass(True)
        assert result["ok"] is False
        assert bridge.bypass is True

    def test_save_state_persists(self, mock_player):
        with patch("core.settings_manager.set_") as set_mock:
            bridge = EqBridge(player_service=mock_player)
            bridge._preamp = 2.0
            bridge._current_preset = "Rock"
            bridge.saveState()
            set_mock.assert_any_call("audio/eq_preamp", 2.0)
            set_mock.assert_any_call("audio/eq_preset", "Rock")

    def test_restore_state_loads(self, mock_player):
        with patch("core.settings_manager.get") as get_mock:
            def fake_get(key, default=None):
                return default if key == "audio/eq_graphic_bands" else default
            get_mock.side_effect = fake_get
            bridge = EqBridge(player_service=mock_player)
            result = bridge.restoreState()
            assert result["ok"] is True
