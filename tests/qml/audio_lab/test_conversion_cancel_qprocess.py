"""Tests for AV — Conversión cancelable con QProcess."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestConversionCancelQProcess:
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
    def svc(self, app, db, wm):
        from core.audio_lab.audio_conversion_service import AudioConversionService
        return AudioConversionService(db=db, wm=wm)

    @pytest.fixture
    def sample_wav(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00")
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_conversion_service_creates(self, svc):
        assert svc is not None

    def test_conversion_preview_missing(self, svc):
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format="FLAC")
        result = svc.preview("/nonexistent.flac", profile)
        assert not result["ok"]
        assert "SOURCE_NOT_FOUND" in result["error"]

    def test_conversion_preview_unsupported(self, svc, sample_wav):
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format="AVI")
        result = svc.preview(sample_wav, profile)
        assert not result["ok"]
        assert "UNSUPPORTED_FORMAT" in result["error"]

    def test_conversion_preview_valid(self, svc, sample_wav):
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format="FLAC")
        result = svc.preview(sample_wav, profile)
        assert result["ok"]

    def test_conversion_preview_collision(self, svc, sample_wav):
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format="WAV")
        result = svc.preview(sample_wav, profile)
        assert "collision" in result

    def test_conversion_job_id_generated(self, svc, sample_wav):
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format="WAV", output_dir=tempfile.gettempdir())
        job_id = svc.convert(sample_wav, profile)
        assert job_id.startswith("conv_")

    def test_conversion_cancel_pending(self, svc, sample_wav):
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format="WAV", output_dir=tempfile.gettempdir())
        job_id = svc.convert(sample_wav, profile)
        result = svc.cancel(job_id)
        assert result is True

    def test_conversion_cancel_nonexistent(self, svc):
        assert svc.cancel("nonexistent") is False

    def test_conversion_signal_connectivity(self, svc):
        signals = []
        svc.conversionStarted.connect(lambda j: signals.append(("start", j)))
        svc.conversionCompleted.connect(lambda j, t: signals.append(("complete", j, t)))
        svc.conversionFailed.connect(lambda j, e: signals.append(("fail", j, e)))
        svc.conversionCancelled.connect(lambda j: signals.append(("cancel", j)))
        svc.conversionStarted.emit("test")
        svc.conversionCompleted.emit("test", "/out.wav")
        svc.conversionFailed.emit("test", "error")
        svc.conversionCancelled.emit("test")
        _process_events(0.2)
        assert len(signals) == 4

    def test_conversion_cancel_lifecycle(self, svc, sample_wav):
        from core.audio_lab.audio_conversion_service import ConversionProfile, STATUS_CANCELLED
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        profile = ConversionProfile(format="FLAC", output_dir=tempfile.gettempdir())
        job_id = svc.convert(sample_wav, profile)
        svc.cancel(job_id)
        job = svc._active_jobs.get(job_id)
        if job:
            assert job.status == STATUS_CANCELLED
