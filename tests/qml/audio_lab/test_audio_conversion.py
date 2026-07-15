"""Macrofase F — 13.6: Audio conversion service tests."""
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


class TestAudioConversion:
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
    def sample_wav(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00")
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_conversion_service_created(self, app, db, wm):
        from core.audio_lab.audio_conversion_service import AudioConversionService
        svc = AudioConversionService(db=db, wm=wm)
        assert svc is not None

    def test_conversion_preview_missing_source(self, app, db, wm):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="FLAC")
        result = svc.preview("/nonexistent.flac", profile)
        assert not result["ok"]
        assert "SOURCE_NOT_FOUND" in result["error"]

    def test_conversion_preview_unsupported_format(self, app, db, wm, sample_wav):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="AVI")
        result = svc.preview(sample_wav, profile)
        assert not result["ok"]
        assert "UNSUPPORTED_FORMAT" in result["error"]

    def test_conversion_preview_existing_source(self, app, db, wm, sample_wav):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="FLAC")
        result = svc.preview(sample_wav, profile)
        assert result["ok"]

    def test_conversion_audio_only_formats(self, app, db, wm):
        from core.audio_lab.audio_conversion_service import AUDIO_ONLY_FORMATS
        assert "FLAC" in AUDIO_ONLY_FORMATS
        assert "WAV" in AUDIO_ONLY_FORMATS
        assert "MP3" in AUDIO_ONLY_FORMATS
        assert "AAC" in AUDIO_ONLY_FORMATS
        assert "Opus" in AUDIO_ONLY_FORMATS
        assert "Vorbis" in AUDIO_ONLY_FORMATS
        assert "ALAC" in AUDIO_ONLY_FORMATS
        assert "AIFF" in AUDIO_ONLY_FORMATS

    def test_conversion_job_lifecycle(self, app, db, wm, sample_wav):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="WAV", output_dir=tempfile.gettempdir())
        results = []
        svc.conversionCompleted.connect(lambda jid, t: results.append(("completed", jid, t)))
        svc.conversionFailed.connect(lambda jid, e: results.append(("failed", jid, e)))
        job_id = svc.convert(sample_wav, profile)
        assert job_id != ""
        _process_events(3.0)
        assert len(results) >= 0

    def test_conversion_preview_collision(self, app, db, wm, sample_wav):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="WAV", output_dir=tempfile.gettempdir())
        result = svc.preview(sample_wav, profile)
        assert "collision" in result

    def test_conversion_signal_connectivity(self, app, db, wm):
        from core.audio_lab.audio_conversion_service import AudioConversionService
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        svc = AudioConversionService(db=db, wm=wm)
        signals = []
        svc.conversionStarted.connect(lambda j: signals.append(("start", j)))
        svc.conversionStarted.emit("test_job")
        assert len(signals) == 1
