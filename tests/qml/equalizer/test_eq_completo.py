"""EQ/DSP completo: enable, disable, bands, preamp, presets, save, rename, delete, reset, backend capability, applied state, error."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT, PARAMETRIC_BAND_COUNT

PRESETS_MODULE = "audio.eq_presets"


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


@pytest.fixture
def bridge(mock_player):
    return EqBridge(player_service=mock_player)


def test_initial_state(bridge):
    assert bridge.enabled is True
    assert bridge.bypass is False
    assert bridge.preamp == 0.0
    assert len(bridge.graphicBands) == GRAPHIC_BAND_COUNT
    assert len(bridge.parametricBands) == PARAMETRIC_BAND_COUNT
    assert bridge.backendAvailable is False


def test_enable_disable(bridge, mock_player):
    bridge._backend_available = True
    result = bridge.setEnabled(False)
    assert result["ok"] is True
    assert bridge.enabled is False
    result = bridge.setEnabled(True)
    assert result["ok"] is True
    assert bridge.enabled is True


def test_disable_with_bitperfect(bridge, mock_player):
    mock_player.get_active_backend_id.return_value = "mpd"
    bridge._update_backend_state()
    assert bridge.bitperfectConflict is True
    result = bridge.setEnabled(True)
    assert result["ok"] is False
    assert "BITPERFECT_CONFLICT" in result.get("error", "")


def test_graphic_band_set_and_clamp(bridge, mock_player):
    bridge._backend_available = True
    bridge.setGraphicBand(0, 12.0)
    assert bridge._graphic_bands[0] == 12.0
    bridge.setGraphicBand(1, 30.0)
    assert bridge._graphic_bands[1] == 24.0
    bridge.setGraphicBand(2, -30.0)
    assert bridge._graphic_bands[2] == -24.0


def test_graphic_band_invalid_index(bridge):
    assert not bridge.setGraphicBand(-1, 3.0)["ok"]
    assert not bridge.setGraphicBand(GRAPHIC_BAND_COUNT, 3.0)["ok"]
    assert not bridge.setGraphicBand(99, 3.0)["ok"]


def test_graphic_band_no_player():
    b = EqBridge()
    result = b.setGraphicBand(0, 6.0)
    assert result["ok"] is False
    assert b._graphic_bands[0] == 6.0


def test_parametric_band_set_and_clamp(bridge, mock_player):
    bridge._backend_available = True
    result = bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
    assert result["ok"] is True
    assert bridge._parametric_bands[0]["freq"] == 500.0
    assert bridge._parametric_bands[0]["gain"] == -6.0
    assert bridge._parametric_bands[0]["enabled"] is True
    bridge.setParametricBand(1, "low_shelf", 80.0, 50.0, True)
    assert bridge._parametric_bands[1]["gain"] == 24.0


def test_parametric_band_invalid_index(bridge):
    assert not bridge.setParametricBand(-1, "peaking", 100.0, 0, True)["ok"]
    assert not bridge.setParametricBand(PARAMETRIC_BAND_COUNT, "peaking", 100.0, 0, True)["ok"]


def test_preamp_set_and_reflect(bridge, mock_player):
    bridge._backend_available = True
    assert bridge.setPreamp(3.5)["ok"] is True
    assert bridge.preamp == 3.5
    assert bridge.setPreamp(-12.0)["ok"] is True
    assert bridge.preamp == -12.0


def test_preamp_no_player():
    b = EqBridge()
    result = b.setPreamp(5.0)
    assert result["ok"] is False
    assert b.preamp == 5.0


def test_bypass_toggle(bridge, mock_player):
    bridge._backend_available = True
    assert bridge.bypass is False
    assert bridge.toggleBypass(True)["ok"] is True
    assert bridge.bypass is True
    assert bridge.toggleBypass(False)["ok"] is True
    assert bridge.bypass is False


def test_bypass_bitperfect_blocked(bridge, mock_player):
    mock_player.get_active_backend_id.return_value = "mpd"
    bridge._update_backend_state()
    result = bridge.toggleBypass(True)
    assert result["ok"] is False
    assert "BITPERFECT_CONFLICT" in result.get("error", "")


def test_reset_clears_all_state(bridge, mock_player):
    bridge._backend_available = True
    bridge.setGraphicBand(0, 12.0)
    bridge.setGraphicBand(3, -6.0)
    bridge.setPreamp(5.0)
    bridge.toggleBypass(True)
    result = bridge.reset()
    assert result["ok"] is True
    assert bridge.preamp == 0.0
    assert bridge.bypass is False
    assert all(g == 0.0 for g in bridge._graphic_bands)
    assert all(b["gain"] == 0 for b in bridge._parametric_bands)
    assert all(b["enabled"] is False for b in bridge._parametric_bands)


def test_presets_refresh_and_apply(bridge, mock_player):
    bridge._backend_available = True
    with patch(f"{PRESETS_MODULE}.get_preset_names") as names, \
         patch(f"{PRESETS_MODULE}.load_graphic_preset") as load:
        names.return_value = ["Plano", "Rock", "Jazz"]
        load.return_value = [2.0] * GRAPHIC_BAND_COUNT
        bridge.refresh()
        assert len(bridge.presets) >= 3
        result = bridge.applyPreset("Rock")
        assert result["ok"] is True
        assert bridge._current_preset == "Rock"
        assert bridge._graphic_bands[0] == 2.0


def test_apply_preset_empty_name(bridge):
    assert bridge.applyPreset("")["error"] == "EMPTY_NAME"


def test_save_custom_preset(bridge, mock_player):
    bridge._graphic_bands = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    with patch(f"{PRESETS_MODULE}.save_custom_presets") as save, \
         patch(f"{PRESETS_MODULE}.load_custom_presets") as load:
        load.return_value = {}
        save.return_value = None
        result = bridge.saveCustomPreset("MyPreset")
        assert result["ok"] is True
        assert result["name"] == "MyPreset"
        save.assert_called_once()


def test_save_custom_preset_empty_name(bridge):
    assert bridge.saveCustomPreset("")["error"] == "EMPTY_NAME"


def test_import_preset(bridge, tmp_path):
    preset_file = tmp_path / "import_test.json"
    preset_file.write_text(json.dumps({
        "name": "Imported", "bands": [0.5] * GRAPHIC_BAND_COUNT,
    }))
    with patch(f"{PRESETS_MODULE}.load_custom_presets") as load, \
         patch(f"{PRESETS_MODULE}.save_custom_presets") as save:
        load.return_value = {}
        save.return_value = None
        result = bridge.importPreset(str(preset_file))
        assert result["ok"] is True
        assert result["name"] == "Imported"


def test_import_preset_file_not_found(bridge):
    result = bridge.importPreset("/nonexistent/file.json")
    assert result["ok"] is False


def test_import_preset_invalid_band_count(bridge, tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"name": "Bad", "bands": [0.0, 0.0]}))
    result = bridge.importPreset(str(f))
    assert result["ok"] is False
    assert result["error"] == "INVALID_BAND_COUNT"


def test_export_preset(bridge, tmp_path):
    bridge._backend_available = True
    bridge._graphic_bands = [3.0] * GRAPHIC_BAND_COUNT
    bridge._preamp = -2.0
    export_file = tmp_path / "export.json"
    result = bridge.exportPreset(str(export_file))
    assert result["ok"] is True
    assert export_file.exists()
    data = json.loads(export_file.read_text())
    assert data["name"] == "Plano"
    assert len(data["bands"]) == GRAPHIC_BAND_COUNT


def test_export_preset_invalid_path(bridge):
    result = bridge.exportPreset("")
    assert result["ok"] is False


def test_save_state_persists_settings(bridge):
    with patch("core.settings_manager.set_") as set_mock:
        bridge._preamp = -3.0
        bridge._current_preset = "Rock"
        bridge._enabled = False
        result = bridge.saveState()
        assert result["ok"] is True
        set_mock.assert_any_call("audio/eq_preamp", -3.0)
        set_mock.assert_any_call("audio/eq_preset", "Rock")
        set_mock.assert_any_call("audio/eq_enabled", False)


def test_restore_state_loads_settings(bridge):
    def fake_get(key, default=None):
        store = {
            "audio/eq_enabled": False,
            "audio/eq_bypass": True,
            "audio/eq_preamp": -2.5,
            "audio/eq_preset": "Jazz",
            "audio/eq_graphic_bands": json.dumps([2.0] * GRAPHIC_BAND_COUNT),
        }
        return store.get(key, default)
    with patch("core.settings_manager.get", side_effect=fake_get):
        result = bridge.restoreState()
        assert result["ok"] is True
        assert bridge.enabled is False
        assert bridge.bypass is True
        assert bridge.preamp == -2.5
        assert bridge._current_preset == "Jazz"


def test_backend_available_reflects_player(bridge, mock_player):
    assert bridge.backendAvailable is False
    bridge._update_backend_state()
    assert bridge.backendAvailable is True


def test_backend_unavailable_without_player():
    b = EqBridge()
    b._update_backend_state()
    assert b.backendAvailable is False


def test_bitperfect_conflict_detection(bridge, mock_player):
    mock_player.get_active_backend_id.return_value = "mpd"
    bridge._update_backend_state()
    assert bridge.bitperfectConflict is True
    assert bridge._backend_restrictions.get("reason") == "MPD backend bloquea EQ"


def test_bitperfect_blocks_graphic_band(bridge, mock_player):
    mock_player.get_active_backend_id.return_value = "mpd"
    bridge._update_backend_state()
    result = bridge.setGraphicBand(0, 3.0)
    assert result["ok"] is False
    assert result["error"] == "BITPERFECT_CONFLICT"


def test_bitperfect_blocks_parametric_band(bridge, mock_player):
    mock_player.get_active_backend_id.return_value = "mpd"
    bridge._update_backend_state()
    result = bridge.setParametricBand(0, "peaking", 100.0, 0.0, True)
    assert result["ok"] is False
    assert result["error"] == "BITPERFECT_CONFLICT"


def test_bitperfect_blocks_preamp(bridge, mock_player):
    mock_player.get_active_backend_id.return_value = "mpd"
    bridge._update_backend_state()
    result = bridge.setEnabled(True)
    assert result["ok"] is False


def test_applied_state_graphic_band_local_first(bridge):
    bridge._backend_available = False
    bridge.setGraphicBand(0, 8.0)
    assert bridge._graphic_bands[0] == 8.0


def test_applied_state_parametric_band_local_first(bridge):
    bridge._backend_available = False
    bridge.setParametricBand(0, "peaking", 500.0, -6.0, True)
    assert bridge._parametric_bands[0]["freq"] == 500.0


def test_applied_state_bypass_local_first():
    b = EqBridge()
    b.toggleBypass(True)
    assert b.bypass is True


def test_applied_state_preamp_local_first():
    b = EqBridge()
    b.setPreamp(4.0)
    assert b.preamp == 4.0


def test_error_on_no_player_generic():
    b = EqBridge()
    assert b.toggleBypass(True)["ok"] is False
    assert b.setPreamp(0.0)["ok"] is False
    assert b.setGraphicBand(0, 0.0)["ok"] is False


def test_error_on_backend_exception(bridge, mock_player):
    mock_player.set_eq_graphic.side_effect = RuntimeError("Backend denied")
    bridge._backend_available = True
    result = bridge.setGraphicBand(0, 5.0)
    assert result["ok"] is False
    assert bridge._graphic_bands[0] == 5.0


def test_refresh_fallback_presets(bridge):
    with patch(f"{PRESETS_MODULE}.get_preset_names") as names, \
         patch(f"{PRESETS_MODULE}.load_graphic_preset") as load:
        names.side_effect = Exception("DB error")
        result = bridge.refresh()
        assert result["ok"] is True
        assert len(bridge.presets) == 1
        assert bridge.presets[0]["name"] == "Plano"


def test_graphic_bands_property_includes_freq(bridge):
    bands = bridge.graphicBands
    assert len(bands) == GRAPHIC_BAND_COUNT
    for i, b in enumerate(bands):
        assert b["freq"] > 0
        assert "gain" in b


def test_parametric_bands_property_full(bridge):
    bands = bridge.parametricBands
    assert len(bands) == PARAMETRIC_BAND_COUNT
    for b in bands:
        assert "freq" in b
        assert "gain" in b
        assert "q" in b
        assert "type" in b
        assert "enabled" in b


def test_presets_property_after_refresh(bridge):
    with patch(f"{PRESETS_MODULE}.get_preset_names") as names, \
         patch(f"{PRESETS_MODULE}.load_graphic_preset") as load:
        names.return_value = ["Plano", "Rock"]
        load.return_value = [0.0] * GRAPHIC_BAND_COUNT
        bridge.refresh()
        presets = bridge.presets
        assert len(presets) >= 2
        for p in presets:
            assert "name" in p
            assert "bands" in p
