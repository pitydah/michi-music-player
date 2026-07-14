"""Macrofase F — 13.8: ReplayGain service tests."""
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


class TestReplayGain:
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

    def test_replaygain_service_created(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        assert svc is not None

    def test_replaygain_track_missing(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        result = svc.analyze_track("/nonexistent.flac")
        assert result.status == "error"
        assert result.error == "FILE_NOT_FOUND"

    def test_replaygain_album_empty(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        results = svc.analyze_album([])
        assert results == []

    def test_replaygain_remove_tags_missing(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        result = svc.remove_tags("/nonexistent.flac")
        assert result is False

    def test_replaygain_signal_connectivity(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        signals = []
        svc.analysisCompleted.connect(lambda fp, r: signals.append((fp, r)))
        svc.analysisCompleted.emit("test.flac", {"gain": -5.0})
        _process_events(0.2)
        assert len(signals) == 1

    def test_replaygain_write_tags_signal(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        signals = []
        svc.tagsWritten.connect(lambda fp, ok: signals.append((fp, ok)))
        svc.tagsWritten.emit("test.flac", True)
        _process_events(0.2)
        assert len(signals) == 1

    def test_replaygain_result_dataclass(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainResult
        r = ReplayGainResult(filepath="test.flac", status="completed", track_gain=-5.2, track_peak=0.8)
        assert r.filepath == "test.flac"
        assert r.track_gain == -5.2
        assert r.track_peak == 0.8
        assert r.reference_loudness == -18.0

    def test_replaygain_album_computation(self, app, db, wm):
        from core.audio_lab.replaygain_service import ReplayGainService
        svc = ReplayGainService(db=db, wm=wm)
        results = svc.analyze_album(["/missing1.flac", "/missing2.flac"])
        assert len(results) == 2
        assert all(r.status == "error" for r in results)
