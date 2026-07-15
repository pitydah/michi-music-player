"""Macrofase F — 13.1: AudioLabService orchestration tests."""
from __future__ import annotations

import time
import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestAudioLabService:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT)")
        return conn

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    def test_service_creates(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=db, worker_manager=wm)
        assert svc is not None

    def test_service_setup(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=db, worker_manager=wm)
        svc.setup()
        caps = svc.capability_map()
        assert "probe" in caps
        assert "analysis" in caps
        assert "conversion" in caps
        assert "normalization" in caps
        assert "replaygain" in caps
        assert "integrity" in caps
        assert "comparison" in caps
        assert "batch" in caps
        assert "profiles" in caps

    def test_service_status(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=db, worker_manager=wm)
        svc.setup()
        status = svc.status()
        assert "capabilities" in status
        assert "available" in status

    def test_service_properties(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=db, worker_manager=wm)
        svc.setup()
        assert svc.probe is not None
        assert svc.analysis is not None
        assert svc.conversion is not None

    def test_service_signal_connectivity(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=db, worker_manager=wm)
        signals = []
        svc.stateChanged.connect(lambda s, d: signals.append((s, d)))
        svc.stateChanged.emit("test", {"ok": True})
        _process_events(0.2)
        assert len(signals) >= 1

    def test_service_no_crash_without_deps(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        svc = AudioLabService(db=None, worker_manager=None)
        svc.setup()
        status = svc.status()
        assert isinstance(status["available"], bool)
        assert "capabilities" in status

    def test_probe_service_independent(self, app, db, wm):
        from core.audio_lab.audio_probe_service import AudioProbeService
        svc = AudioProbeService()
        result = svc.probe("/nonexistent/file.flac")
        assert result.decode_status == "not_found"
        assert "FILE_NOT_FOUND" in result.inconsistencies

    def test_integrity_service_independent(self, app, db, wm):
        from core.audio_lab.audio_integrity_service import AudioIntegrityService
        svc = AudioIntegrityService()
        result = svc.check("/nonexistent/file.flac")
        from core.audio_lab.audio_integrity_service import IntegrityStatus
        assert result.status == IntegrityStatus.ERROR
        assert not result.is_valid

    def test_comparison_service_independent(self, app, db, wm):
        from core.audio_lab.audio_comparison_service import AudioComparisonService
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        svc = AudioComparisonService()
        result = svc.compare("/nonexistent/a.flac", "/nonexistent/b.flac")
        assert "FILE_NOT_FOUND" in result.error
