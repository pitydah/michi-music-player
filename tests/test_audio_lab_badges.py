"""Tests for Audio Lab badges — get_badge_for_file, get_spectral_badge, is_analysis_pending."""

from __future__ import annotations

import os
import tempfile


class TestGetBadgeForFile:

    def test_flac_without_cache_returns_lossless(self):
        from ui.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.flac")
        assert badge["label"] == "FLAC"
        assert badge["kind"] == "lossless"

    def test_mp3_without_cache_returns_lossy(self):
        from ui.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.mp3")
        assert badge["label"] == "MP3"
        assert badge["kind"] == "lossy"

    def test_dsf_without_cache_returns_dsd(self):
        from ui.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.dsf")
        assert badge["kind"] == "dsd"

    def test_wav_without_cache_returns_lossless(self):
        from ui.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.wav")
        assert badge["kind"] == "lossless"

    def test_cache_hit_produces_badge(self):
        from ui.audio_lab.diagnostics_service import (
            get_badge_for_file, reset_global_cache_for_tests,
            close_global_cache, _get_cache,
        )
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            tmp_path = f.name
        try:
            reset_global_cache_for_tests(":memory:")
            cache = _get_cache()
            assert cache is not None
            cache.put(tmp_path, {
                "filepath": tmp_path,
                "format_info": {
                    "container": "FLAC", "codec": "flac",
                    "sample_rate": 96000, "bit_depth": 24,
                },
                "quality": {"category": "hires", "label": "FLAC 24/96"},
            })
            badge = get_badge_for_file(tmp_path)
            assert badge["label"] == "FLAC 24/96"
            assert badge["kind"] == "hires"
            assert "coherente" in badge["tooltip"]
        finally:
            os.unlink(tmp_path)
            close_global_cache()


class TestGetSpectralBadge:

    def test_suspicious_upsampling_returns_warning(self):
        from ui.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "SUSPICIOUS_UPSAMPLING",
                  "label": "Upsampling sospechoso",
                  "explanation": "test", "confidence": 0.5}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "warning"
        assert "Upsampling" in badge["label"]

    def test_possible_lossy_returns_warning(self):
        from ui.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "POSSIBLE_LOSSY_SOURCE",
                  "label": "Posible fuente con pérdida",
                  "explanation": "test", "confidence": 0.5}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "warning"

    def test_hires_coherent_returns_success(self):
        from ui.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "HI_RES_COHERENT",
                  "label": "Hi-Res coherente",
                  "explanation": "test", "confidence": 0.8}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "success"

    def test_lossless_coherent_returns_success(self):
        from ui.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "LOSSLESS_COHERENT",
                  "label": "Lossless coherente",
                  "explanation": "test", "confidence": 0.7}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "success"

    def test_inconclusive_returns_info(self):
        from ui.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "INCONCLUSIVE",
                  "label": "No concluyente",
                  "explanation": "test", "confidence": 0.1}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "info"

    def test_confidence_appended_to_tooltip(self):
        from ui.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "HI_RES_COHERENT",
                  "label": "Hi-Res coherente",
                  "explanation": "Espectro normal", "confidence": 0.75}
        badge = get_spectral_badge(result)
        assert "75%" in badge["tooltip"]


class TestAnalysisPending:

    def test_nonexistent_file_returns_pending(self):
        from ui.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/nonexistent/never.wav")
        assert badge["kind"] in ("unknown", "lossless")
