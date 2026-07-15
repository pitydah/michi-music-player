"""Macrofase F — 13.11: Audio Lab job adapter tests."""
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


class TestAudioLabJobs:
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
    def adapter(self, app, db, wm):
        from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
        from core.audio_lab.audio_probe_service import AudioProbeService
        from core.audio_lab.audio_analysis_service import AudioAnalysisService
        from core.audio_lab.audio_integrity_service import AudioIntegrityService
        from core.audio_lab.audio_comparison_service import AudioComparisonService
        from core.audio_lab.replaygain_service import ReplayGainService
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        return AudioLabJobAdapter(
            db=db, wm=wm,
            probe=AudioProbeService(),
            analysis=AudioAnalysisService(db=db, wm=wm),
            integrity=AudioIntegrityService(),
            comparison=AudioComparisonService(),
            replaygain=ReplayGainService(),
        )

    def test_submit_probe(self, adapter):
        job_id = adapter.submit_probe("/nonexistent.flac")
        assert job_id.startswith("probe_")
        _process_events(1.0)
        job = adapter.get(job_id)
        assert job is not None

    def test_submit_analysis(self, adapter):
        job_id = adapter.submit_analysis("/nonexistent.flac")
        assert job_id.startswith("analysis_")
        _process_events(1.0)

    def test_submit_replaygain(self, adapter):
        job_id = adapter.submit_replaygain("/nonexistent.flac")
        assert job_id.startswith("rg_")

    def test_submit_integrity(self, adapter):
        job_id = adapter.submit_integrity("/nonexistent.flac")
        assert job_id.startswith("integrity_")

    def test_submit_comparison(self, adapter):
        job_id = adapter.submit_comparison("/a.flac", "/b.flac")
        assert job_id.startswith("compare_")

    def test_cancel_job(self, adapter):
        job_id = adapter.submit_probe("/nonexistent.flac")
        result = adapter.cancel(job_id)
        assert result is True

    def test_cancel_nonexistent(self, adapter):
        result = adapter.cancel("nonexistent")
        assert result is False

    def test_list_jobs(self, adapter):
        adapter.submit_probe("/a.flac")
        adapter.submit_analysis("/b.flac")
        jobs = adapter.list()
        assert len(jobs) >= 2
