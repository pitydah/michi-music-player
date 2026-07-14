"""DV — AudioLab advanced analysis: codec, format, sample rate, bit depth,
channels, bitrate, loudness, peak, clipping, silence, checksum, decode."""
from __future__ import annotations

import os
import tempfile
import sqlite3
import time

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


class TestAudioLabAnalysisV2:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        return sqlite3.connect(":memory:")

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def sample_flac(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def svc(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        return AudioAnalysisService(db=db, wm=wm)

    def test_analysis_returns_codec(self, svc, sample_flac):
        result = svc.analyze_file(sample_flac)
        assert "codec" in result

    def test_analysis_returns_format(self, svc, sample_flac):
        result = svc.analyze_file(sample_flac)
        assert "format" in result

    def test_analysis_returns_sample_rate(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert result["status"] == "error"
        assert result["sample_rate"] == 0

    def test_analysis_returns_bit_depth(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "bit_depth" in result

    def test_analysis_returns_channels(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "channels" in result

    def test_analysis_returns_bitrate(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "bitrate" in result

    def test_analysis_returns_loudness(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "loudness" in result

    def test_analysis_returns_peak(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "peak" in result

    def test_analysis_returns_clipping(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "clipping" in result
        assert result["clipping"] is False

    def test_analysis_returns_silence(self, svc, sample_flac):
        result = svc.analyze_file(sample_flac)
        assert "silence" in result

    def test_analysis_returns_checksum(self, svc, sample_flac):
        result = svc.analyze_file(sample_flac)
        assert "checksum" in result

    def test_analysis_returns_decode_status(self, svc):
        result = svc.analyze_file("/nonexistent.flac")
        assert "decode_status" in result

    def test_analysis_batch_produces_list(self, svc):
        results = svc.analyze_batch(["/a.flac", "/b.flac"])
        assert isinstance(results, list)
        assert len(results) == 2
