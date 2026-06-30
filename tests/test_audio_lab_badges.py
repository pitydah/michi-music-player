"""Tests for Audio Lab badges — get_badge_for_file, get_spectral_badge, library adapter, filters."""

from __future__ import annotations

import os
import tempfile


class TestLibraryBadgeAdapter:

    def test_get_audio_lab_badge_for_path_flac(self):
        from library.audio_lab_badges import get_audio_lab_badge_for_path
        badge = get_audio_lab_badge_for_path("/path/to/song.flac")
        assert badge["label"] == "FLAC"
        assert badge["kind"] == "lossless"

    def test_get_audio_lab_badge_for_path_mp3(self):
        from library.audio_lab_badges import get_audio_lab_badge_for_path
        badge = get_audio_lab_badge_for_path("/path/to/song.mp3")
        assert badge["kind"] == "lossy"

    def test_get_audio_lab_badge_for_path_dsf(self):
        from library.audio_lab_badges import get_audio_lab_badge_for_path
        badge = get_audio_lab_badge_for_path("/path/to/song.dsf")
        assert badge["kind"] == "dsd"

    def test_get_audio_lab_badges_for_paths(self):
        from library.audio_lab_badges import get_audio_lab_badges_for_paths
        paths = ["/a.flac", "/b.mp3", "/c.dsf"]
        result = get_audio_lab_badges_for_paths(paths)
        assert len(result) == 3
        assert result["/a.flac"]["kind"] == "lossless"
        assert result["/b.mp3"]["kind"] == "lossy"
        assert result["/c.dsf"]["kind"] == "dsd"

    def test_get_audio_lab_badges_for_paths_with_nonexistent(self):
        from library.audio_lab_badges import get_audio_lab_badges_for_paths
        result = get_audio_lab_badges_for_paths(["/nonexistent/file.xyz"])
        assert len(result) == 1
        assert result["/nonexistent/file.xyz"]["kind"] in ("unknown", "error")

    def test_get_quality_filter_value(self):
        from library.audio_lab_badges import get_quality_filter_value
        assert get_quality_filter_value("/a.flac") == "lossless"
        assert get_quality_filter_value("/b.mp3") == "lossy"

    def test_is_analysis_pending_nonexistent(self):
        from library.audio_lab_badges import is_analysis_pending
        assert is_analysis_pending("/nonexistent.flac") is False

    def test_is_analysis_pending_existing_no_cache(self):
        import tempfile
        from library.audio_lab_badges import is_analysis_pending
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            path = f.name
        try:
            assert is_analysis_pending(path) is True
        finally:
            os.unlink(path)

    def test_matches_quality_filter(self):
        from library.audio_lab_badges import matches_quality_filter
        assert matches_quality_filter("/a.flac", "lossless") is True
        assert matches_quality_filter("/a.flac", "lossy") is False
        assert matches_quality_filter("/b.mp3", "lossy") is True

    def test_matches_analysis_filter_pending(self):
        import tempfile
        from library.audio_lab_badges import matches_analysis_filter
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            assert matches_analysis_filter(path, "pending") is True
        finally:
            os.unlink(path)

    def test_matches_analysis_filter_nonexistent(self):
        from library.audio_lab_badges import matches_analysis_filter
        assert matches_analysis_filter("/nonexistent.wav", "pending") is False

    def test_matches_spectral_filter_no_cache(self):
        from library.audio_lab_badges import matches_spectral_filter
        assert matches_spectral_filter("/no/file.wav", "suspicious") is False

    def test_get_spectral_badge_from_result(self):
        from library.audio_lab_badges import get_spectral_badge_from_result
        result = {"verdict": "SUSPICIOUS_UPSAMPLING",
                  "label": "test", "explanation": "test", "confidence": 0.5}
        badge = get_spectral_badge_from_result(result)
        assert badge["kind"] == "warning"


class TestGetBadgeForFile:

    def test_flac_without_cache_returns_lossless(self):
        from core.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.flac")
        assert badge["label"] == "FLAC"
        assert badge["kind"] == "lossless"

    def test_mp3_without_cache_returns_lossy(self):
        from core.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.mp3")
        assert badge["label"] == "MP3"
        assert badge["kind"] == "lossy"

    def test_dsf_without_cache_returns_dsd(self):
        from core.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.dsf")
        assert badge["kind"] == "dsd"

    def test_wav_without_cache_returns_lossless(self):
        from core.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/path/to/song.wav")
        assert badge["kind"] == "lossless"

    def test_cache_hit_produces_badge(self):
        from core.audio_lab.diagnostics_service import (
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
        from core.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "SUSPICIOUS_UPSAMPLING",
                  "label": "Upsampling sospechoso",
                  "explanation": "test", "confidence": 0.5}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "warning"
        assert "Upsampling" in badge["label"]

    def test_possible_lossy_returns_warning(self):
        from core.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "POSSIBLE_LOSSY_SOURCE",
                  "label": "Posible fuente con pérdida",
                  "explanation": "test", "confidence": 0.5}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "warning"

    def test_hires_coherent_returns_success(self):
        from core.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "HI_RES_COHERENT",
                  "label": "Hi-Res coherente",
                  "explanation": "test", "confidence": 0.8}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "success"

    def test_lossless_coherent_returns_success(self):
        from core.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "LOSSLESS_COHERENT",
                  "label": "Lossless coherente",
                  "explanation": "test", "confidence": 0.7}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "success"

    def test_inconclusive_returns_info(self):
        from core.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "INCONCLUSIVE",
                  "label": "No concluyente",
                  "explanation": "test", "confidence": 0.1}
        badge = get_spectral_badge(result)
        assert badge["kind"] == "info"

    def test_confidence_appended_to_tooltip(self):
        from core.audio_lab.diagnostics_service import get_spectral_badge
        result = {"verdict": "HI_RES_COHERENT",
                  "label": "Hi-Res coherente",
                  "explanation": "Espectro normal", "confidence": 0.75}
        badge = get_spectral_badge(result)
        assert "75%" in badge["tooltip"]


class TestAnalysisPending:

    def test_nonexistent_file_returns_pending(self):
        from core.audio_lab.diagnostics_service import get_badge_for_file
        badge = get_badge_for_file("/nonexistent/never.wav")
        assert badge["kind"] in ("unknown", "lossless")
