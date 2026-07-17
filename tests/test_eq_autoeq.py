"""Tests for AutoEQ headphone preset search and loading."""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from audio.eq_autoeq import search_headphone, load_headphone_preset


FAKE_PRESET = {
    "preamp": -3.5,
    "filters": [
        {"type": "Peak", "frequency": 60, "gain": 4.0, "Q": 0.7},
        {"type": "Peak", "frequency": 1000, "gain": -2.0, "Q": 1.41},
        {"type": "Peak", "frequency": 8000, "gain": 3.5, "Q": 1.0},
    ],
}

FAKE_MODEL_NAMES = [
    "HD 600.json",
    "HD 650.json",
    "HD 800 S.json",
    "DT 770 Pro.json",
    "DT 990 Pro.json",
]


class TestSearchHeadphone:
    def test_search_headphone_found(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        for name in FAKE_MODEL_NAMES:
            (cache_dir / name).write_text("{}")
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("hd 600")
        assert results == ["HD 600"]

    def test_search_headphone_found_partial(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        for name in FAKE_MODEL_NAMES:
            (cache_dir / name).write_text("{}")
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("dt")
        assert len(results) == 2
        assert "DT 770 Pro" in results
        assert "DT 990 Pro" in results

    def test_search_headphone_not_found(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        for name in FAKE_MODEL_NAMES:
            (cache_dir / name).write_text("{}")
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("K 701")
        assert results == []

    def test_search_headphone_empty_cache(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("hd")
        assert results == []

    def test_search_headphone_cache_missing_dir(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("hd")
        assert results == []

    def test_search_headphone_case_insensitive(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "My Headphone.json").write_text("{}")
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("my headphone")
        assert results == ["My Headphone"]

    def test_search_headphone_max_results(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        for i in range(30):
            (cache_dir / f"Model {i}.json").write_text("{}")
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("model")
        assert len(results) == 20

    def test_search_headphone_sorted(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        for name in ["Z Model.json", "A Model.json", "M Model.json"]:
            (cache_dir / name).write_text("{}")
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            results = search_headphone("model")
        assert results == ["A Model", "M Model", "Z Model"]


class TestLoadHeadphonePreset:
    def test_load_headphone_preset_exists(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "HD_600.json").write_text(json.dumps(FAKE_PRESET))
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            bands = load_headphone_preset("HD 600")
        assert len(bands) == 3
        assert bands[0]["freq"] == 60
        assert bands[0]["gain"] == 4.0
        assert bands[0]["Q"] == 0.7
        assert bands[1]["freq"] == 1000
        assert bands[1]["gain"] == -2.0
        assert bands[1]["Q"] == 1.41

    def test_load_headphone_preset_fallback_Q(self, tmp_path):
        data = {
            "filters": [
                {"type": "Peak", "frequency": 1000, "gain": 2.0, "q": 0.5},
            ]
        }
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "Test.json").write_text(json.dumps(data))
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            bands = load_headphone_preset("Test")
        assert bands[0]["Q"] == 0.5
        assert bands[0]["gain"] == 2.0

    def test_load_headphone_preset_fallback_type(self, tmp_path):
        data = {
            "filters": [
                {"frequency": 1000, "gain": 2.0},
            ]
        }
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "Test.json").write_text(json.dumps(data))
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            bands = load_headphone_preset("Test")
        assert bands[0]["type"] == "Peak"

    def test_load_headphone_preset_no_filters(self, tmp_path):
        data = {"preamp": -2.0, "filters": []}
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "Flat.json").write_text(json.dumps(data))
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            bands = load_headphone_preset("Flat")
        assert bands == []

    def test_load_headphone_preset_missing(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            with pytest.raises(FileNotFoundError):
                load_headphone_preset("Nonexistent Model")

    def test_load_headphone_preset_slash_in_name(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "AKG_K_701.json").write_text(json.dumps(FAKE_PRESET))
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            bands = load_headphone_preset("AKG K 701")
        assert len(bands) == 3

    def test_load_headphone_preset_all_band_keys(self, tmp_path):
        cache_dir = tmp_path / "autoeq"
        cache_dir.mkdir()
        (cache_dir / "HD_600.json").write_text(json.dumps(FAKE_PRESET))
        with patch("audio.eq_autoeq.CACHE_DIR", str(cache_dir)):
            bands = load_headphone_preset("HD 600")
        for band in bands:
            assert "type" in band
            assert "freq" in band
            assert "gain" in band
            assert "Q" in band
