"""Tests for Diagnostics service and navigation."""

from __future__ import annotations

import os
import tempfile
import wave


def _create_test_wav(filepath: str, sample_rate: int = 44100):
    import numpy as np
    n_frames = int(sample_rate * 1.0)
    t = np.linspace(0, 1.0, n_frames, endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 440 * t)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(tone.astype(np.int16).tobytes())


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
