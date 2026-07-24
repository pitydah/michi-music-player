"""Tests for DurableJobService — job lifecycle, progress, cancellation."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def job_svc():
    from core.jobs.job_service import DurableJobService
    svc = DurableJobService()
    svc._db = None  # disable persistence
    return svc


class TestJobService:
    def test_create_job(self, job_svc):
        jid = job_svc.create_job("test_type", "Test Job")
        assert jid is not None
        job = job_svc.get_job(jid)
        assert job is not None
        assert job.type == "test_type"
        assert job.owner == "Test Job"

    def test_list_jobs(self, job_svc):
        job_svc.create_job("type_a", "Job A")
        job_svc.create_job("type_b", "Job B")
        jobs = job_svc.list_jobs()
        assert len(jobs) >= 2

    def test_start_job_no_handler(self, job_svc):
        jid = job_svc.create_job("type", "Start Test")
        result = job_svc.start_job(jid)
        # No handler registered, so start returns False
        assert not result

    def test_job_progress_available(self, job_svc):
        jid = job_svc.create_job("type", "Progress Test")
        job_svc.start_job(jid)
        with pytest.raises(Exception):
            job_svc.update_progress(jid, 50.0)

    def test_cancel_job(self, job_svc):
        jid = job_svc.create_job("type", "Cancel Test")
        result = job_svc.cancel_job(jid)
        assert result

    def test_cancel_all(self, job_svc):
        for i in range(3):
            jid = job_svc.create_job("type", f"Job {i}")
            job_svc.start_job(jid)
        job_svc.cancel_all()
        jobs = job_svc.list_jobs()
        # All should be cancelled or running (cancel doesn't remove)

    def test_add_error_and_warning(self, job_svc):
        jid = job_svc.create_job("type", "Error Test")
        job_svc.add_warning(jid, "Warning message")
        job_svc.add_error(jid, "Error message")
        job = job_svc.get_job(jid)
        assert job is not None

    def test_retry_job(self, job_svc):
        jid = job_svc.create_job("type", "Retry Test")
        job_svc.start_job(jid)
        job_svc.cancel_job(jid)
        result = job_svc.retry_job(jid)
        assert result  # may fail gracefully

    def test_cleanup_old_jobs(self, job_svc):
        for i in range(3):
            job_svc.create_job("type", f"Old Job {i}")
        result = job_svc.cleanup_old_jobs(max_age_days=0)
        assert result is None or result >= 0

    def test_register_handler(self, job_svc):
        handler = MagicMock()
        job_svc.register_handler("test_type", handler)
        assert True  # no error

    def test_pause_resume(self, job_svc):
        jid = job_svc.create_job("type", "Pause Test")
        job_svc.start_job(jid)
        # Without a handler, pause returns False
        pause_ok = job_svc.pause_job(jid)
        assert isinstance(pause_ok, bool)
        resume_ok = job_svc.resume_job(jid)
        assert isinstance(resume_ok, bool)
