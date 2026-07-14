"""Test EQ preset operations through EqBridge."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.eq_bridge import EqBridge, GRAPHIC_BAND_COUNT

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


@patch(f"{PRESETS_MODULE}.get_preset_names")
def test_refresh_presets(mock_get_names, mock_player):
    mock_get_names.return_value = ["Plano", "Rock", "Jazz"]
    bridge = EqBridge(player_service=mock_player)
    with patch(f"{PRESETS_MODULE}.load_graphic_preset") as mock_load:
        mock_load.return_value = [0.0] * GRAPHIC_BAND_COUNT
        result = bridge.refresh()
        assert result["ok"]
        assert len(bridge._presets) >= 2


@patch(f"{PRESETS_MODULE}.get_preset_names")
def test_apply_preset(mock_get_names, mock_player):
    mock_get_names.return_value = ["Plano"]
    bridge = EqBridge(player_service=mock_player)
    bridge._backend_available = True
    with patch(f"{PRESETS_MODULE}.load_graphic_preset") as mock_load:
        mock_load.return_value = [2.0] * GRAPHIC_BAND_COUNT
        result = bridge.applyPreset("Plano")
        assert result["ok"]
        assert bridge._current_preset == "Plano"


def test_apply_empty_preset(mock_player):
    bridge = EqBridge(player_service=mock_player)
    result = bridge.applyPreset("")
    assert not result["ok"]
    assert result["error"] == "EMPTY_NAME"


def test_reset_eq(mock_player):
    bridge = EqBridge(player_service=mock_player)
    bridge._graphic_bands = [3.0] * GRAPHIC_BAND_COUNT
    bridge._preamp = -6.0
    bridge._bypass = True
    result = bridge.reset()
    assert result["ok"]
    assert bridge._graphic_bands == [0.0] * GRAPHIC_BAND_COUNT
    assert bridge._preamp == 0.0
    assert bridge._bypass is False


@patch(f"{PRESETS_MODULE}.save_custom_presets")
def test_import_preset(mock_save, mock_player):
    with patch("ui_qml_bridge.eq_bridge.Path") as mock_path:
        mock_file = MagicMock()
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = '{"name": "Test", "bands": [0,0,0,0,0,0,0,0,0,0]}'
        mock_file.stem = "test_preset"
        mock_path.return_value = mock_file
        bridge = EqBridge(player_service=mock_player)
        result = bridge.importPreset("/fake/preset.json")
        assert result["ok"]


def test_export_preset(mock_player):
    import pathlib
    original = pathlib.Path.write_text
    pathlib.Path.write_text = lambda self, data: None
    try:
        bridge = EqBridge(player_service=mock_player)
        result = bridge.exportPreset("/tmp/_test_export.json")
        assert result["ok"]
    finally:
        pathlib.Path.write_text = original
