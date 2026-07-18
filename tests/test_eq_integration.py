"""Tests for EQ bridge/server synchronization — state sync, presets persistence."""
from unittest.mock import MagicMock

import pytest


class TestEqStateSync:
    def test_eq_bridge_has_state(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert hasattr(EqBridge, 'stateChanged')

    def test_eq_bridge_has_bands_property(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert hasattr(EqBridge, 'graphicBands')

    def test_eq_bridge_has_preamp(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert hasattr(EqBridge, 'preamp')

    def test_eq_bridge_toggle_bypass(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert hasattr(EqBridge, 'toggleBypass')

    def test_eq_presets_persistence(self):
        from audio.eq_presets import GRAPHIC_PRESETS, get_preset_names
        names = get_preset_names()
        assert len(names) > 0
        # Verify each preset has 31 bands
        for name in names:
            bands = GRAPHIC_PRESETS.get(name, [])
            assert len(bands) == 31, f"{name} has {len(bands)} bands"


class TestOutputProfiles:
    def test_profiles_bridge_import(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        assert OutputProfilesBridge is not None

    def test_profiles_have_signals(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        assert hasattr(OutputProfilesBridge, 'dataChanged')

    def test_profiles_bridge_apply(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        assert hasattr(OutputProfilesBridge, 'setActiveProfile')
