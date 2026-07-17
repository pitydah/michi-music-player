"""Tests for graphic ↔ parametric EQ conversion."""
from __future__ import annotations

import numpy as np
import pytest

from audio.eq_convert import graphic_to_parametric, parametric_to_graphic
from audio.eq_presets import ISO_31_FREQS


FLAT_31 = [0.0] * 31

ROCK_GRAPHIC = [
    5.0, 4.5, 4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -2.5,
    -2.5, -2.0, -1.0, 0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5,
    4.0, 4.5, 5.0, 5.5, 6.0, 6.0, 5.5, 5.0, 4.0, 3.0, 2.0,
]

JAZZ_GRAPHIC = [
    3.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0, 0.0,
    0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 2.5, 2.0, 1.5, 1.0,
    0.5, 0.0, -0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -3.0, -2.5, -2.0,
]


class TestGraphicToParametric:
    def test_graphic_to_parametric_returns_tuple(self):
        result = graphic_to_parametric(FLAT_31)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_graphic_to_parametric_returns_bands_and_preamp(self):
        bands, preamp = graphic_to_parametric(FLAT_31)
        assert isinstance(bands, list)
        assert preamp == 0.0

    def test_graphic_to_parametric_band_structure(self):
        bands, _ = graphic_to_parametric(ROCK_GRAPHIC)
        for band in bands:
            assert "type" in band
            assert "freq" in band
            assert "gain" in band
            assert "Q" in band

    def test_graphic_to_parametric_rock_has_bands(self):
        bands, _ = graphic_to_parametric(ROCK_GRAPHIC)
        assert len(bands) > 0
        assert len(bands) <= 10

    def test_graphic_to_parametric_jazz_has_bands(self):
        bands, _ = graphic_to_parametric(JAZZ_GRAPHIC)
        assert len(bands) > 0

    def test_graphic_to_parametric_bands_sorted_by_freq(self):
        bands, _ = graphic_to_parametric(ROCK_GRAPHIC)
        freqs = [b["freq"] for b in bands]
        assert freqs == sorted(freqs)

    def test_graphic_to_parametric_contains_shelves(self):
        bands, _ = graphic_to_parametric(JAZZ_GRAPHIC)
        types = [b["type"] for b in bands]
        assert "LowShelf" in types or "HighShelf" in types

    def test_graphic_to_parametric_rounds_gain(self):
        bands, _ = graphic_to_parametric(ROCK_GRAPHIC)
        for band in bands:
            assert band["gain"] == round(band["gain"], 1)

    def test_graphic_to_parametric_flat_returns_few_bands(self):
        bands, _ = graphic_to_parametric(FLAT_31)
        assert len(bands) <= 3

    def test_graphic_to_parametric_rejects_wrong_length(self):
        with pytest.raises(AssertionError):
            graphic_to_parametric([0.0] * 10)

    def test_graphic_to_parametric_flat_low_shelf_skipped(self):
        bands, _ = graphic_to_parametric(FLAT_31)
        for band in bands:
            if band["type"] == "LowShelf":
                assert abs(band["gain"]) >= 0.5

    def test_graphic_to_parametric_flat_high_shelf_skipped(self):
        bands, _ = graphic_to_parametric(FLAT_31)
        for band in bands:
            if band["type"] == "HighShelf":
                assert abs(band["gain"]) >= 0.5


class TestParametricToGraphic:
    def test_parametric_to_graphic_returns_31_bands(self):
        result = parametric_to_graphic([])
        assert len(result) == 31

    def test_parametric_to_graphic_empty_returns_flat(self):
        result = parametric_to_graphic([])
        assert result == pytest.approx([0.0] * 31, abs=0.1)

    def test_parametric_to_graphic_empty_with_preamp(self):
        result = parametric_to_graphic([], -3.0)
        assert result == pytest.approx([-3.0] * 31, abs=0.1)

    def test_parametric_to_graphic_values_are_floats(self):
        result = parametric_to_graphic([])
        assert all(isinstance(v, float) for v in result)

    def test_parametric_to_graphic_values_rounded_one_decimal(self):
        result = parametric_to_graphic([])
        for v in result:
            assert v == round(v, 1)

    def test_parametric_to_graphic_single_band_has_peak(self):
        bands = [{"type": "Peak", "freq": 1000, "gain": 6.0, "Q": 1.41}]
        result = parametric_to_graphic(bands)
        idx = ISO_31_FREQS.index(1000)
        assert result[idx] > 0

    def test_parametric_to_graphic_peak_shape(self):
        bands = [{"type": "Peak", "freq": 1000, "gain": 6.0, "Q": 1.41}]
        result = parametric_to_graphic(bands)
        idx = ISO_31_FREQS.index(1000)
        assert result[idx] > result[idx - 1]
        assert result[idx] > result[idx + 1]

    def test_parametric_to_graphic_boost_at_exact_freq(self):
        bands = [{"type": "Peak", "freq": 1000, "gain": 12.0, "Q": 1.41}]
        result = parametric_to_graphic(bands)
        idx = ISO_31_FREQS.index(1000)
        assert 5.0 < result[idx] < 15.0

    def test_parametric_to_graphic_mixed_bands(self):
        bands = [
            {"type": "LowShelf", "freq": 60, "gain": 4.0, "Q": 0.7},
            {"type": "Peak", "freq": 1000, "gain": -3.0, "Q": 1.41},
            {"type": "HighShelf", "freq": 10000, "gain": 2.0, "Q": 0.7},
        ]
        result = parametric_to_graphic(bands)
        low_idx = ISO_31_FREQS.index(63)
        mid_idx = ISO_31_FREQS.index(1000)
        high_idx = ISO_31_FREQS.index(10000)
        assert result[low_idx] > 0
        assert result[mid_idx] < 0
        assert result[high_idx] > 0


class TestRoundtrip:
    def test_roundtrip_flat_stays_flat(self):
        bands, _ = graphic_to_parametric(FLAT_31)
        back = parametric_to_graphic(bands)
        assert back == pytest.approx(FLAT_31, abs=3.0)

    def test_roundtrip_preserves_broad_shape(self):
        bands, _ = graphic_to_parametric(ROCK_GRAPHIC)
        back = parametric_to_graphic(bands)
        corr = np.corrcoef(ROCK_GRAPHIC, back)[0, 1]
        assert corr > 0.2

    def test_roundtrip_jazz_shape_preserved(self):
        bands, _ = graphic_to_parametric(JAZZ_GRAPHIC)
        back = parametric_to_graphic(bands)
        corr = np.corrcoef(JAZZ_GRAPHIC, back)[0, 1]
        assert corr > 0.15

    def test_roundtrip_low_freq_trend_preserved(self):
        low_boost = [3.0] * 10 + [0.0] * 21
        bands, _ = graphic_to_parametric(low_boost)
        back = parametric_to_graphic(bands)
        assert np.mean(back[:10]) > np.mean(back[20:])

    def test_roundtrip_high_freq_trend_preserved(self):
        high_boost = [0.0] * 21 + [4.0] * 10
        bands, _ = graphic_to_parametric(high_boost)
        back = parametric_to_graphic(bands)
        assert np.mean(back[20:]) > np.mean(back[:10])


class TestEmptyAndFlat:
    def test_empty_graphic_returns_empty(self):
        with pytest.raises(AssertionError):
            graphic_to_parametric([])

    def test_empty_parametric_returns_flat(self):
        result = parametric_to_graphic([])
        assert all(abs(v) < 0.1 for v in result)

    def test_near_flat_graphic_returns_few_bands(self):
        almost_flat = [0.2] * 31
        bands, _ = graphic_to_parametric(almost_flat)
        assert len(bands) <= 3

    def test_graphic_zero_low_end_no_shelf(self):
        zero_low = [0.0] * 10 + [3.0] * 21
        bands, _ = graphic_to_parametric(zero_low)
        low_shelves = [b for b in bands if b["type"] == "LowShelf"]
        if low_shelves:
            assert abs(low_shelves[0]["gain"]) < 0.5

    def test_graphic_zero_high_end_no_shelf(self):
        zero_high = [3.0] * 21 + [0.0] * 10
        bands, _ = graphic_to_parametric(zero_high)
        high_shelves = [b for b in bands if b["type"] == "HighShelf"]
        if high_shelves:
            assert abs(high_shelves[0]["gain"]) < 0.5
