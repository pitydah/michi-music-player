from __future__ import annotations
"""MF-MK: Audio jobs integration — job_service integration with AudioLabBridge."""

import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from core.job_service import JobService, JobState


class TestAudioJobsIntegration:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT)")
        return conn

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def audio_lab_svc(self, app, db, wm):
        from core.audio_lab.audio_lab_service import AudioLabService
        s = AudioLabService(db=db, worker_manager=wm)
        s.setup()
        return s

    @pytest.fixture
    def job_svc(self, tmp_path):
        return JobService(db_path=str(tmp_path / "jobs.db"))

    @pytest.fixture
    def bridge(self, audio_lab_svc, job_svc):
        return AudioLabBridge(
            audio_lab_service=audio_lab_svc,
            job_service=job_svc,
        )

    def test_job_service_injected(self, bridge, job_svc):
        assert bridge._jobs is job_svc

    def test_job_service_creates_job(self, job_svc):
        job_id = job_svc.create_job("conversion", payload={"file": "/test.flac"})
        job = job_svc.get_job(job_id)
        assert job is not None
        assert job.type == "conversion"
        assert job.state == JobState.QUEUED

    def test_job_service_cancel(self, job_svc):
        job_id = job_svc.create_job("conversion", payload={"file": "/test.flac"})
        result = job_svc.cancel_job(job_id)
        assert result is True
        assert job_svc.get_job(job_id).state == JobState.CANCELLED

    def test_job_service_cancel_real(self, job_svc):
        """Cancel is REAL — reaches service."""
        job_id = job_svc.create_job("conversion", payload={"file": "/test.flac"})
        job_svc.cancel_job(job_id)
        updated = job_svc.get_job(job_id)
        assert updated.state == JobState.CANCELLED
        assert updated.finishedAt

    def test_job_service_double_cancel(self, job_svc):
        job_id = job_svc.create_job("conversion", payload={"file": "/test.flac"})
        job_svc.cancel_job(job_id)
        result = job_svc.cancel_job(job_id)
        assert result is False

    def test_job_service_list_active(self, job_svc):
        first = job_svc.create_job("probe", payload={"file": "/a.flac"})
        second = job_svc.create_job("analysis", payload={"file": "/b.flac"})
        job_svc.cancel_job(first)
        active = job_svc.list_jobs(state=JobState.QUEUED)
        assert len(active) == 1
        assert active[0]["id"] == second

    def test_job_service_completed(self, job_svc):
        job_id = job_svc.create_job("conversion", payload={"file": "/test.flac"})
        job_svc.register_handler("conversion", lambda _job, _progress: {})
        assert job_svc.start_job(job_id) is True
        assert job_svc.get_job(job_id).state == JobState.SUCCEEDED

    def test_job_service_clear_completed(self, job_svc):
        first = job_svc.create_job("probe", payload={"file": "/a.flac"})
        second = job_svc.create_job("probe", payload={"file": "/b.flac"})
        job_svc.register_handler("probe", lambda _job, _progress: {})
        job_svc.start_job(first)
        removed = job_svc.clear_terminal()
        assert removed == 1
        assert job_svc.get_job(first) is None
        assert job_svc.get_job(second) is not None

    def test_job_bridge_integration(self, bridge):
        assert bridge._jobs is not None

    def test_job_kind_filter(self, job_svc):
        job_svc.create_job("probe", payload={"file": "/a.flac"})
        job_svc.create_job("conversion", payload={"file": "/b.flac"})
        probes = job_svc.list_jobs(job_type="probe")
        assert len(probes) == 1
        conversions = job_svc.list_jobs(job_type="conversion")
        assert len(conversions) == 1
