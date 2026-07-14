"""Macrofase F — 13.5: Audio analysis service tests."""
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


class TestAudioAnalysis:
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

    def test_analysis_file_not_found(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        result = svc.analyze_file("/nonexistent/file.flac")
        assert result["status"] == "error"
        assert result["error"] == "FILE_NOT_FOUND"

    def test_analysis_disabled(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        svc.enabled = False
        result = svc.analyze_file("/dev/null")
        assert result["status"] == "disabled"

    def test_analysis_backend_info(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        info = svc.get_backend_info()
        assert "available" in info
        assert "enabled" in info
        assert "name" in info

    def test_analysis_batch_empty(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        results = svc.analyze_batch([])
        assert results == []

    def test_analysis_batch_with_missing(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        results = svc.analyze_batch(["/missing.flac", "/missing2.flac"])
        assert len(results) == 2
        assert all(r["status"] == "error" for r in results)

    def test_analysis_toggle_enabled(self, app, db, wm):
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        svc = AudioAnalysisService(db=db)
        assert svc.enabled is True
        svc.enabled = False
        assert svc.enabled is False
