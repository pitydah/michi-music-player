"""MF-MK: Audio jobs integration — job_service integration with AudioLabBridge."""
from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from core.job_service import JobService, JobStatus


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
    def job_svc(self):
        return JobService()

    @pytest.fixture
    def bridge(self, audio_lab_svc, job_svc):
        return AudioLabBridge(
            audio_lab_service=audio_lab_svc,
            job_service=job_svc,
        )

    def test_job_service_injected(self, bridge, job_svc):
        assert bridge._job_svc is job_svc

    def test_job_service_creates_job(self, job_svc):
        job = job_svc.create("conversion", {"file": "/test.flac"})
        assert job.job_id is not None
        assert job.kind == "conversion"
        assert job.status == JobStatus.QUEUED

    def test_job_service_cancel(self, job_svc):
        job = job_svc.create("conversion", {"file": "/test.flac"})
        result = job_svc.cancel(job.job_id)
        assert result is True
        assert job_svc.get(job.job_id).status == JobStatus.CANCELLED

    def test_job_service_cancel_real(self, job_svc):
        """Cancel is REAL — reaches service."""
        job = job_svc.create("conversion", {"file": "/test.flac"})
        job_svc.cancel(job.job_id)
        updated = job_svc.get(job.job_id)
        assert updated.status == JobStatus.CANCELLED
        assert updated.finished_at > 0

    def test_job_service_double_cancel(self, job_svc):
        job = job_svc.create("conversion", {"file": "/test.flac"})
        job_svc.cancel(job.job_id)
        result = job_svc.cancel(job.job_id)
        assert result is False

    def test_job_service_list_active(self, job_svc):
        job1 = job_svc.create("probe", {"file": "/a.flac"})
        job2 = job_svc.create("analysis", {"file": "/b.flac"})
        job_svc.cancel(job1.job_id)
        active = job_svc.list_active()
        assert len(active) == 1
        assert active[0].job_id == job2.job_id

    def test_job_service_completed(self, job_svc):
        job = job_svc.create("conversion", {"file": "/test.flac"})
        job_svc.update(job.job_id, status=JobStatus.COMPLETED)
        assert job_svc.get(job.job_id).status == JobStatus.COMPLETED

    def test_job_service_clear_completed(self, job_svc):
        job1 = job_svc.create("probe", {"file": "/a.flac"})
        job2 = job_svc.create("probe", {"file": "/b.flac"})
        job_svc.update(job1.job_id, status=JobStatus.COMPLETED)
        job_svc.clear_completed()
        assert job_svc.get(job1.job_id) is None
        assert job_svc.get(job2.job_id) is not None

    def test_job_bridge_integration(self, bridge):
        assert bridge._job_svc is not None

    def test_job_kind_filter(self, job_svc):
        job_svc.create("probe", {"file": "/a.flac"})
        job_svc.create("conversion", {"file": "/b.flac"})
        probes = job_svc.list_by_kind("probe")
        assert len(probes) == 1
        conversions = job_svc.list_by_kind("conversion")
        assert len(conversions) == 1
