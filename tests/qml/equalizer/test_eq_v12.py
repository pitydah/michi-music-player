"""Tests for EQ v12 — enable, bypass, graphic bands, parametric bands, preamp, presets, reset."""
from unittest.mock import MagicMock, patch

import pytest


class TestEqBridgeCreation:
    def test_requires_player(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        with pytest.raises(Exception):
            EqBridge()

    def test_creation(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        assert eq is not None

    def test_enabled_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        assert isinstance(eq.enabled, bool)

    def test_bypass_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        assert isinstance(eq.bypass, bool)

    def test_preamp_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        assert isinstance(eq.preamp, float)

    def test_graphic_bands_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        bands = eq.graphicBands
        assert len(bands) == 10

    def test_parametric_bands_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        bands = eq.parametricBands
        assert len(bands) == 6

    def test_presets_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        eq._update_backend_state = MagicMock()
        eq.refresh()
        assert len(eq.presets) >= 1

    def test_current_preset_default(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        assert eq.currentPreset != ""


class TestEqOperations:
    def test_refresh(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        result = eq.refresh()
        assert result.get("ok")

    def test_set_graphic_band(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        player = MagicMock()
        player.set_eq_graphic = MagicMock()
        eq = EqBridge(player_service=player)
        result = eq.setGraphicBand(0, 3.0)
        assert result.get("ok")

    def test_set_graphic_band_invalid(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        result = eq.setGraphicBand(20, 3.0)
        assert not result.get("ok")

    def test_set_preamp(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        player = MagicMock()
        player.set_eq_preamp = MagicMock()
        eq = EqBridge(player_service=player)
        result = eq.setPreamp(-5.0)
        assert result.get("ok")

    def test_set_parametric_band(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        player = MagicMock()
        player.set_eq_parametric = MagicMock()
        eq = EqBridge(player_service=player)
        result = eq.setParametricBand(0, "peaking", 32, 2.0, True)
        assert result.get("ok")

    def test_reset(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        player = MagicMock()
        eq = EqBridge(player_service=player)
        result = eq.reset()
        assert result.get("ok")

    def test_toggle_bypass(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        player = MagicMock()
        player.set_eq_bypass = MagicMock()
        eq = EqBridge(player_service=player)
        result = eq.toggleBypass(True)
        assert result.get("ok")

    def test_set_enabled(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        player = MagicMock()
        player.set_eq_bypass = MagicMock()
        eq = EqBridge(player_service=player)
        result = eq.setEnabled(True)
        assert isinstance(result, dict)

    def test_save_state(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        result = eq.saveState()
        assert isinstance(result, dict)

    def test_restore_state(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        eq = EqBridge(player_service=MagicMock())
        result = eq.restoreState()
        assert isinstance(result, dict)
