"""Test: equalizer service, presets, and bridge."""


class TestEqService:
    def test_eq_service_imports(self):
        from core.equalizer_service import EqualizerService
        assert EqualizerService is not None

    def test_eq_presets_import(self):
        from audio.eq_presets import get_preset_names
        assert len(get_preset_names()) > 0

    def test_eq_biquad_import(self):
        pass

    def test_eq_presets_loaded(self):
        from audio.eq_presets import GRAPHIC_PRESETS, get_preset_names
        names = get_preset_names()
        assert "Flat" in names
        for name in names:
            bands = GRAPHIC_PRESETS[name]
            assert len(bands) == 31, f"{name} should have 31 bands, got {len(bands)}"


class TestEqBridge:
    def test_eq_bridge_import(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert EqBridge is not None

    def test_eq_bridge_has_slots(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert hasattr(EqBridge, 'setEnabled')
        assert hasattr(EqBridge, 'toggleBypass')
        assert hasattr(EqBridge, 'setPreamp')
        assert hasattr(EqBridge, 'reset')
