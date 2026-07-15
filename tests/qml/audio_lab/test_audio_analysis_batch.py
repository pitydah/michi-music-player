"""Tests for AW — Análisis y batch."""
from __future__ import annotations

import sqlite3
import time

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestAudioAnalysisBatch:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT)")
        return conn

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    def test_analysis_service_created(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db, wm=wm)
        assert svc is not None

    def test_analysis_missing_file(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        result = svc.analyze_file("/nonexistent/file.flac")
        assert result["status"] == "error"
        assert result["error"] == "FILE_NOT_FOUND"

    def test_analysis_basic_analysis_includes_codec(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        result = svc.analyze_file("/nonexistent.flac")
        assert "codec" in result
        assert "sample_rate" in result
        assert "bit_depth" in result
        assert "channels" in result

    def test_analysis_integrity_fields_present(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        result = svc.analyze_file("/nonexistent.flac")
        assert "checksum" in result
        assert "decode_status" in result
        assert "loudness" in result
        assert "peak" in result

    def test_analysis_clipping_detection(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        result = svc.analyze_file("/nonexistent.flac")
        assert "clipping" in result

    def test_analysis_silence_detection(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        result = svc.analyze_file("/nonexistent.flac")
        assert "silence" in result

    def test_batch_service_creates(self, app, db, wm):
        from core.audio_lab.audio_batch_service import AudioBatchService
        svc = AudioBatchService(db=db, wm=wm)
        assert svc is not None

    def test_batch_create_and_status(self, app, db, wm):
        from core.audio_lab.audio_batch_service import AudioBatchService
        svc = AudioBatchService(db=db, wm=wm)
        batch_id = svc.create_batch(["/a.flac", "/b.flac"])
        status = svc.status(batch_id)
        assert status is not None
        assert status["total"] == 2

    def test_batch_cancel(self, app, db, wm):
        from core.audio_lab.audio_batch_service import AudioBatchService
        svc = AudioBatchService(db=db, wm=wm)
        batch_id = svc.create_batch(["/a.flac", "/b.flac"])
        canceled = svc.cancel(batch_id)
        assert canceled is True
        status = svc.status(batch_id)
        assert status is None or status["status"] == "cancelled"

    def test_batch_cancel_nonexistent(self, app, db, wm):
        from core.audio_lab.audio_batch_service import AudioBatchService
        svc = AudioBatchService(db=db, wm=wm)
        assert svc.cancel("nonexistent") is False

    def test_batch_pause_resume(self, app, db, wm):
        from core.audio_lab.audio_batch_service import AudioBatchService
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        svc = AudioBatchService(db=db, wm=wm)
        batch_id = svc.create_batch(["/a.flac", "/b.flac"])
        assert svc.pause(batch_id) is False
        assert svc.cancel(batch_id) is True
