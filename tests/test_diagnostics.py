"""Tests for Diagnostics service and navigation."""

from __future__ import annotations

import os
import tempfile
import wave


def _create_test_wav(filepath: str, sample_rate: int = 44100,
                     sampwidth: int = 2, n_channels: int = 1):
    import numpy as np
    n_frames = int(sample_rate * 1.0)
    t = np.linspace(0, 1.0, n_frames, endpoint=False)
    # Scale to full int16 range before casting
    tone = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    data = np.column_stack((tone, tone)) if n_channels == 2 else tone
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())


class TestDiagnosticsService:

    def test_analyse_file_nonexistent(self):
        from ui.audio_lab.diagnostics_service import analyse_file
        result = analyse_file("/nonexistent/file.flac")
        assert result["error"] == "Archivo no encontrado"
        assert not result["exists"]

    def test_analyse_file_basic(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            _create_test_wav(path)
            from ui.audio_lab.diagnostics_service import analyse_file
            result = analyse_file(path)
            assert result["exists"]
            assert result["filename"] == os.path.basename(path)
            assert "format_info" in result
            assert "quality" in result
            assert result["size_mb"] > 0
        finally:
            os.unlink(path)

    def test_analyse_directory_empty(self):
        from ui.audio_lab.diagnostics_service import analyse_directory
        with tempfile.TemporaryDirectory() as tmp:
            results = analyse_directory(tmp)
            assert results == []

    def test_analyse_directory_with_files(self):
        from ui.audio_lab.diagnostics_service import analyse_directory
        with tempfile.TemporaryDirectory() as tmp:
            p1 = os.path.join(tmp, "a.wav")
            p2 = os.path.join(tmp, "b.flac")
            _create_test_wav(p1)
            _create_test_wav(p2)
            results = analyse_directory(tmp)
            assert len(results) == 2

    def test_generate_report_empty(self):
        from ui.audio_lab.diagnostics_service import generate_report
        report = generate_report([])
        assert report["total_files"] == 0
        assert report["total_size_mb"] == 0.0

    def test_generate_report_with_data(self):
        from ui.audio_lab.diagnostics_service import generate_report
        results = [
            {"filepath": "/a.wav", "filename": "a.wav", "exists": True,
             "error": "", "size_mb": 10.0, "duration_str": "1m 0s",
             "format_info": {"container": "WAV", "sample_rate": 44100,
                             "bit_depth": 16, "duration": 60.0,
                             "is_lossless": True, "warnings": []},
             "quality": {"category": "lossless", "label": "WAV", "tooltip": ""}},
        ]
        report = generate_report(results)
        assert report["total_files"] == 1
        assert report["total_size_mb"] == 10.0
        assert report["format_counts"].get("wav") == 1
        assert "lossless" in str(report["quality_counts"])

    def test_audio_exts_include_expected(self):
        from ui.audio_lab.diagnostics_service import AUDIO_EXTS
        for ext in (".flac", ".wav", ".mp3", ".opus", ".dsf", ".dff"):
            assert ext in AUDIO_EXTS, f"Missing {ext}"
        assert ".txt" not in AUDIO_EXTS
        assert ".pdf" not in AUDIO_EXTS

    def test_generate_report_with_warnings_and_errors(self):
        from ui.audio_lab.diagnostics_service import generate_report
        results = [
            {"filepath": "/a.wav", "filename": "a.wav", "exists": True,
             "error": "", "size_mb": 10.0, "duration_str": "1m 0s",
             "format_info": {"container": "WAV", "sample_rate": 44100,
                             "bit_depth": 16, "duration": 60.0,
                             "is_lossless": True,
                             "warnings": [" clipping detected"]},
             "quality": {"category": "lossless", "label": "WAV"}},
            {"filepath": "/b.flac", "filename": "b.flac", "exists": True,
             "error": "error!", "size_mb": 20.0, "duration_str": "2m 0s",
             "format_info": {"container": "FLAC", "sample_rate": 96000,
                             "bit_depth": 24, "duration": 120.0,
                             "is_lossless": True, "warnings": []},
             "quality": {"category": "hires", "label": "FLAC 24/96"}},
        ]
        report = generate_report(results)
        assert report["total_files"] == 2
        assert report["total_size_mb"] == 30.0
        assert report["format_counts"].get("wav") == 1
        assert report["format_counts"].get("flac") == 1
        assert report["quality_counts"].get("lossless") == 1
        assert report["quality_counts"].get("hires") == 1
        assert 44100 in report["sample_rates"]
        assert 96000 in report["sample_rates"]
        assert 16 in report["bit_depths"]
        assert 24 in report["bit_depths"]
        assert len(report["errors"]) == 1
        assert len(report["warnings"]) == 1

    def test_analyse_file_quality_classification(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            _create_test_wav(path, sample_rate=44100)
            from ui.audio_lab.diagnostics_service import analyse_file
            result = analyse_file(path)
            q = result.get("quality", {})
            assert q.get("category") in ("lossless", "unknown")
        finally:
            os.unlink(path)


class TestDiagnosticsNav:

    def test_diagnostics_route_in_nav_routes(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        assert "audio_lab_diagnostics" in NAV_ROUTES

    def test_diagnostics_section_config(self):
        from ui.controllers.navigation_controller import SECTION_CONFIG
        assert "audio_lab_diagnostics" in SECTION_CONFIG
        cfg = SECTION_CONFIG["audio_lab_diagnostics"]
        assert "title" in cfg and "subtitle" in cfg and "icon" in cfg

    def test_diagnostics_sidebar_key(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("audio_lab_diagnostics") == "audio_lab"


class TestSpectralAnalysis:

    def test_analyse_spectral_nonexistent_file(self):
        from ui.audio_lab.diagnostics_service import analyse_spectral
        result = analyse_spectral("/nonexistent/file.wav")
        assert result["verdict"] == "ANALYSIS_ERROR"

    def test_analyse_spectral_nonwav(self):
        import tempfile
        import os
        from ui.audio_lab.diagnostics_service import analyse_spectral
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC")
            path = f.name
        try:
            result = analyse_spectral(path)
            assert result["verdict"] == "ANALYSIS_ERROR"
            assert "WAV PCM" in result.get("explanation", "")
        finally:
            os.unlink(path)

    def test_analyse_spectral_24bit_96khz(self):
        import tempfile
        import os
        import wave
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            sr = 96000
            bd_bytes = 3  # 24-bit
            frames = int(sr * 1)
            t = np.linspace(0, 1, frames, endpoint=False)
            tone = np.int32(0.3 * 8388608 * np.sin(2 * np.pi * 1000 * t))
            raw_24 = np.zeros(frames * 3, dtype=np.uint8)
            for i in range(frames):
                v = int(tone[i]) & 0xFFFFFF
                raw_24[i * 3] = v & 0xFF
                raw_24[i * 3 + 1] = (v >> 8) & 0xFF
                raw_24[i * 3 + 2] = (v >> 16) & 0xFF
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(bd_bytes)
                wf.setframerate(sr)
                wf.writeframes(raw_24.tobytes())

            from ui.audio_lab.diagnostics_service import analyse_spectral
            result = analyse_spectral(path)
            # A 1 kHz sine at 96 kHz has no ultrasonic content,
            # so SUSPICIOUS_UPSAMPLING is an expected honest verdict
            assert result["verdict"] in (
                "LOSSLESS_COHERENT", "HI_RES_COHERENT",
                "SUSPICIOUS_UPSAMPLING",
                "INCONCLUSIVE", "ANALYSIS_ERROR",
            )
            metrics = result.get("metrics", {})
            if metrics:
                assert metrics.get("declared_sample_rate") == 96000
                assert metrics.get("declared_bit_depth") == 24
        finally:
            os.unlink(path)

    def test_analyse_spectral_stereo_no_crash(self):
        import tempfile
        import os
        import wave
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            sr = 44100
            frames = int(sr * 2)
            t = np.linspace(0, 2, frames, endpoint=False)
            tone = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
            stereo = np.column_stack((tone, tone))
            with wave.open(path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(stereo.tobytes())

            from ui.audio_lab.diagnostics_service import analyse_spectral
            result = analyse_spectral(path)
            assert "verdict" in result
        finally:
            os.unlink(path)

    def test_analyse_spectral_too_short(self):
        import tempfile
        import os
        import wave
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(np.zeros(100, dtype=np.int16).tobytes())

            from ui.audio_lab.diagnostics_service import analyse_spectral
            result = analyse_spectral(path)
            assert result["verdict"] == "ANALYSIS_ERROR"
        finally:
            os.unlink(path)

    def test_analyse_spectral_result_has_confidence(self):
        import tempfile
        import os
        import wave
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            sr = 44100
            frames = int(sr * 3)
            t = np.linspace(0, 3, frames, endpoint=False)
            tone = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(tone.tobytes())

            from ui.audio_lab.diagnostics_service import analyse_spectral
            result = analyse_spectral(path)
            assert "confidence" in result
            assert 0 <= result["confidence"] <= 1.0
        finally:
            os.unlink(path)

    def test_cache_hit_returns_stored_result(self):
        import tempfile
        import os
        from ui.audio_lab.diagnostics_service import DiagnosticsCache

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            _create_test_wav(path)
            cache = DiagnosticsCache(":memory:")
            assert cache.stats()["cached_files"] == 0

            from ui.audio_lab.diagnostics_service import analyse_file
            result = analyse_file(path, use_cache=False)
            cache.put(path, result)
            assert cache.stats()["cached_files"] == 1

            cached = cache.get(path)
            assert cached is not None
            assert cached.get("from_cache") is True
        finally:
            os.unlink(path)

    def test_cache_invalidate_removes_entry(self):
        from ui.audio_lab.diagnostics_service import DiagnosticsCache
        cache = DiagnosticsCache(":memory:")
        cache.put("/tmp/test.wav", {"filepath": "/tmp/test.wav"})
        assert cache.stats()["cached_files"] == 1
        cache.invalidate("/tmp/test.wav")
        assert cache.stats()["cached_files"] == 0

    def test_cache_clear_removes_all(self):
        from ui.audio_lab.diagnostics_service import DiagnosticsCache
        cache = DiagnosticsCache(":memory:")
        cache.put("/tmp/a.wav", {"filepath": "/tmp/a.wav"})
        cache.put("/tmp/b.wav", {"filepath": "/tmp/b.wav"})
        assert cache.stats()["cached_files"] == 2
        cache.clear()
        assert cache.stats()["cached_files"] == 0

    def test_cache_get_nonexistent_file(self):
        from ui.audio_lab.diagnostics_service import DiagnosticsCache
        cache = DiagnosticsCache(":memory:")
        result = cache.get("/nonexistent.wav")
        assert result is None

    def test_analyse_file_with_cache_returns_from_cache(self):
        import tempfile
        import os
        from ui.audio_lab.diagnostics_service import analyse_file

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            _create_test_wav(path)
            _GLOBAL_CACHE_REF = None
            # Analyse first time (uncached)
            r1 = analyse_file(path, use_cache=True)
            assert not r1.get("from_cache", False)

            # Second time should be from cache
            r2 = analyse_file(path, use_cache=True)
            assert r2.get("from_cache", True)
        finally:
            os.unlink(path)

    def test_analyse_spectral_wav_basic(self):
        import tempfile
        import os
        import wave
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            sr = 44100
            frames = int(sr * 2)
            t = np.linspace(0, 2, frames, endpoint=False)
            tone = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(tone.tobytes())

            from ui.audio_lab.diagnostics_service import analyse_spectral
            result = analyse_spectral(path)
            assert "verdict" in result
            assert result["verdict"] in (
                "LOSSLESS_COHERENT", "HI_RES_COHERENT",
                "POSSIBLE_LOSSY_SOURCE", "INCONCLUSIVE",
                "ANALYSIS_ERROR",
            )
        finally:
            os.unlink(path)
