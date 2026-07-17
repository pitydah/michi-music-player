"""Tests for equalizer presets."""
import os
import tempfile

import pytest

from audio.eq_presets import (
    ISO_31_FREQS, ISO_31_LABELS,
    GRAPHIC_PRESETS, PARAMETRIC_PRESETS,
    get_preset_names, load_graphic_preset, load_parametric_preset,
    save_custom_presets, load_custom_presets,
    PRESETS_PATH, SETTINGS_DIR,
)


class TestConstants:
    def test_iso_31_freqs_length(self):
        assert len(ISO_31_FREQS) == 31

    def test_iso_31_labels_length(self):
        assert len(ISO_31_LABELS) == 31

    def test_iso_freqs_are_sorted(self):
        assert sorted(ISO_31_FREQS) == ISO_31_FREQS

    def test_iso_first_is_20(self):
        assert ISO_31_FREQS[0] == 20

    def test_iso_last_is_20000(self):
        assert ISO_31_FREQS[-1] == 20000

    def test_labels_match_freqs_count(self):
        assert len(ISO_31_LABELS) == len(ISO_31_FREQS)


class TestGraphicPresets:
    def test_flat_preset_all_zeros(self):
        assert GRAPHIC_PRESETS["Flat"] == [0.0] * 31

    def test_all_presets_have_31_bands(self):
        for name, bands in GRAPHIC_PRESETS.items():
            assert len(bands) == 31, f"{name} has {len(bands)} bands, expected 31"

    def test_all_presets_values_in_range(self):
        for name, bands in GRAPHIC_PRESETS.items():
            for v in bands:
                assert -12.0 <= v <= 12.0, f"{name} has out-of-range value {v}"

    def test_bass_boost_has_high_low_end(self):
        bb = GRAPHIC_PRESETS["Bass Boost"]
        assert bb[0] > 5.0
        assert bb[-5] == pytest.approx(0.0)

    def test_treble_boost_has_high_high_end(self):
        tb = GRAPHIC_PRESETS["Treble Boost"]
        assert tb[-5] > 5.0
        assert tb[0] == pytest.approx(0.0)

    def test_rock_not_flat(self):
        assert GRAPHIC_PRESETS["Rock"] != GRAPHIC_PRESETS["Flat"]

    def test_pop_has_mid_boost(self):
        pop = GRAPHIC_PRESETS["Pop"]
        mid_idx = 15
        assert pop[mid_idx] > 0

    def test_get_preset_names_sorted(self):
        names = get_preset_names()
        assert names == sorted(names)
        assert "Flat" in names
        assert "Rock" in names

    def test_load_graphic_preset_flat(self):
        assert load_graphic_preset("Flat") == [0.0] * 31

    def test_load_graphic_preset_unknown_returns_flat(self):
        assert load_graphic_preset("NonExistent") == [0.0] * 31

    def test_load_graphic_preset_returns_copy(self):
        r = load_graphic_preset("Rock")
        r[0] = 999
        assert GRAPHIC_PRESETS["Rock"][0] != 999

    def test_all_presets_loadable(self):
        for name in GRAPHIC_PRESETS:
            bands = load_graphic_preset(name)
            assert len(bands) == 31


class TestParametricPresets:
    def test_flat_is_empty(self):
        assert PARAMETRIC_PRESETS["Flat"] == []

    def test_all_presets_have_expected_keys(self):
        for name, bands in PARAMETRIC_PRESETS.items():
            if name == "Flat":
                continue
            for band in bands:
                assert "type" in band
                assert "freq" in band
                assert "gain" in band
                assert "Q" in band

    def test_rock_preset_has_6_bands(self):
        assert len(PARAMETRIC_PRESETS["Rock"]) == 6

    def test_load_parametric_flat(self):
        assert load_parametric_preset("Flat") == []

    def test_load_parametric_unknown_returns_empty(self):
        assert load_parametric_preset("NonExistent") == []

    def test_load_parametric_rock(self):
        bands = load_parametric_preset("Rock")
        assert len(bands) == 6
        assert bands[0]["type"] == "LowShelf"

    def test_parametric_types_valid(self):
        valid_types = {"Peak", "LowShelf", "HighShelf", "LowPass", "HighPass", "Notch", "BandPass"}
        for name, bands in PARAMETRIC_PRESETS.items():
            for band in bands:
                assert band["type"] in valid_types, f"{name} has invalid type {band['type']}"

    def test_load_parametric_returns_copy(self):
        bands = load_parametric_preset("Rock")
        bands[0] = dict(bands[0])
        bands[0]["gain"] = 999
        assert PARAMETRIC_PRESETS["Rock"][0]["gain"] != 999

    def test_load_parametric_jazz(self):
        bands = load_parametric_preset("Jazz")
        assert len(bands) == 6
        assert any(b["type"] == "LowShelf" for b in bands)

    def test_load_parametric_classical(self):
        bands = load_parametric_preset("Classical")
        assert len(bands) == 6

    def test_load_parametric_pop(self):
        bands = load_parametric_preset("Pop")
        assert len(bands) == 6


class TestCustomPresets:
    def setup_method(self):
        self._orig_path = PRESETS_PATH
        self._orig_dir = SETTINGS_DIR

    def teardown_method(self):
        pass

    def test_save_and_load_custom(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            old_path = os.path.join(SETTINGS_DIR, "eq_presets.json")
            presets = {"MyCustom": [1.0, 2.0]}
            custom_dir = os.path.dirname(tmp_path)
            from audio import eq_presets
            eq_presets.PRESETS_PATH = tmp_path
            eq_presets.SETTINGS_DIR = custom_dir
            save_custom_presets(presets)
            loaded = load_custom_presets()
            assert loaded == presets
            eq_presets.PRESETS_PATH = old_path
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_load_custom_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            from audio import eq_presets
            old_path = eq_presets.PRESETS_PATH
            eq_presets.SETTINGS_DIR = d
            eq_presets.PRESETS_PATH = os.path.join(d, "eq_presets.json")
            result = load_custom_presets()
            assert result == {}
            eq_presets.PRESETS_PATH = old_path

    def test_save_custom_creates_dir(self):
        with tempfile.TemporaryDirectory() as d:
            from audio import eq_presets
            old_path = eq_presets.PRESETS_PATH
            old_dir = eq_presets.SETTINGS_DIR
            sub = os.path.join(d, "sub")
            eq_presets.SETTINGS_DIR = sub
            eq_presets.PRESETS_PATH = os.path.join(sub, "eq_presets.json")
            save_custom_presets({"test": [0.0]})
            assert os.path.exists(eq_presets.PRESETS_PATH)
            eq_presets.PRESETS_PATH = old_path
            eq_presets.SETTINGS_DIR = old_dir

    def test_custom_presets_round_trip_types(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            from audio import eq_presets
            old = eq_presets.PRESETS_PATH
            eq_presets.PRESETS_PATH = tmp_path
            eq_presets.SETTINGS_DIR = os.path.dirname(tmp_path)
            data = {"CustomParam": [
                {"type": "Peak", "freq": 1000.0, "gain": 3.0, "Q": 1.41},
            ]}
            save_custom_presets(data)
            loaded = load_custom_presets()
            assert loaded["CustomParam"][0]["freq"] == 1000.0
            eq_presets.PRESETS_PATH = old
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
