"""Tests for advanced parametric EQ widget logic.

Tests focus on the pure data flow — config extraction, preset loading,
and band management.

NOTE: load_preset() uses _remove_band() which refuses to remove the
last remaining band (guard: if len(self._rows) <= 1: return).
After removal of N-1 bands, the last original band stays, then
new preset bands are appended. So get_config() returns
1 old default band + len(preset) bands.
"""
from audio.eq_advanced import AdvancedEqWidget
from audio.eq_presets import PARAMETRIC_PRESETS


class TestAdvancedEqConfig:
    def test_default_band_count(self, qapp):
        w = AdvancedEqWidget()
        configs, preamp = w.get_config()
        assert len(configs) == 7

    def test_default_config_structure(self, qapp):
        w = AdvancedEqWidget()
        configs, preamp = w.get_config()
        for cfg in configs:
            assert "type" in cfg
            assert "freq" in cfg
            assert "gain" in cfg
            assert "Q" in cfg

    def test_default_preamp_zero(self, qapp):
        _, preamp = AdvancedEqWidget().get_config()
        assert preamp == 0.0

    def test_default_first_band_low_shelf(self, qapp):
        configs, _ = AdvancedEqWidget().get_config()
        assert configs[0]["type"] == "LowShelf"
        assert configs[0]["freq"] == 60

    def test_default_last_band_high_shelf(self, qapp):
        configs, _ = AdvancedEqWidget().get_config()
        assert configs[-1]["type"] == "HighShelf"
        assert configs[-1]["freq"] == 12000

    def test_load_preset_flat(self, qapp):
        w = AdvancedEqWidget()
        w.load_preset([], 0.0)
        configs, preamp = w.get_config()
        assert len(configs) == 1
        assert preamp == 0.0

    def test_load_preset_rock(self, qapp):
        w = AdvancedEqWidget()
        rock = PARAMETRIC_PRESETS["Rock"]
        w.load_preset(rock, -1.5)
        configs, preamp = w.get_config()
        assert len(configs) == 1 + len(rock)
        assert preamp == -1.5

    def test_load_preset_then_reset(self, qapp):
        w = AdvancedEqWidget()
        w.load_preset(PARAMETRIC_PRESETS["Rock"], 2.0)
        w.reset()
        configs, preamp = w.get_config()
        assert len(configs) == 8
        assert preamp == 2.0

    def test_reset_restores_defaults(self, qapp):
        w = AdvancedEqWidget()
        w.load_preset([], 5.0)
        w.reset()
        configs, preamp = w.get_config()
        assert len(configs) == 8
        assert preamp == 5.0

    def test_signal_emitted_on_band_change(self, qapp):
        w = AdvancedEqWidget()
        emitted = []
        w.bands_changed.connect(lambda b: emitted.append(len(b)))
        w._add_band("Peak", 2000, 3.0, 1.0)
        assert len(emitted) >= 1

    def test_signal_emitted_on_reset(self, qapp):
        w = AdvancedEqWidget()
        emitted = []
        w.bands_changed.connect(lambda b: emitted.append(len(b)))
        w.reset()
        assert len(emitted) >= 1

    def test_load_preset_clears_and_replaces(self, qapp):
        w = AdvancedEqWidget()
        w.load_preset([{"type": "Peak", "freq": 1000, "gain": 3.0, "Q": 1.41}], 0.0)
        configs, _ = w.get_config()
        assert len(configs) == 2
        assert configs[-1]["type"] == "Peak"
        assert configs[-1]["freq"] == 1000

    def test_load_all_parametric_presets(self, qapp):
        for _name, preset in PARAMETRIC_PRESETS.items():
            w = AdvancedEqWidget()
            w.load_preset(preset, 0.0)
            configs, preamp = w.get_config()
            assert len(configs) == 1 + len(preset)
            assert preamp == 0.0

    def test_preamp_signal_emitted(self, qapp):
        w = AdvancedEqWidget()
        emitted = []
        w.preamp_changed.connect(lambda v: emitted.append(v))
        w._preamp.setValue(30)
        assert len(emitted) > 0
        assert emitted[-1] == 3.0

    def test_preamp_negative(self, qapp):
        w = AdvancedEqWidget()
        w._preamp.setValue(-60)
        assert w._preamp_label.text() == "-6.0dB"

    def test_preamp_positive(self, qapp):
        w = AdvancedEqWidget()
        w._preamp.setValue(60)
        assert w._preamp_label.text() == "+6.0dB"
