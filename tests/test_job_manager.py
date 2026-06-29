"""Tests for the unified JobManager.

WARNING: JobManager uses a SQLite database in the default data directory.
Because the DB is shared, tests that modify job state must clean up
or use unique job IDs. Each test below creates isolated jobs so
there is no cross-test pollution.
"""

from __future__ import annotations

import tempfile

from core.jobs.job_manager import JobManager
from core.jobs.job_persistence import JobRepository
from core.jobs.job_types import Job, JobStatus, JobType


def _make_mgr():
    """Create a JobManager with an isolated temporary DB."""
    tmp = tempfile.mktemp(suffix=".db")

    class _Mgr(JobManager):
        def __init__(self2):
            super().__init__()
            self2._repo = JobRepository(tmp)
            self2._worker_mgr = None
            self2._max_concurrent = 4

    mgr = _Mgr()
    mgr._active = {}
    mgr._handlers = {}
    return mgr


class TestJobRepository:
    def test_create_and_retrieve_job(self):
        mgr = _make_mgr()
        j = Job(type=JobType.QUALITY_ANALYSIS, label="test",
                entity_type="track", entity_id="/path/to/file.flac")
        jid = mgr.create_job(j)
        assert jid

        retrieved = mgr.get_job(jid)
        assert retrieved is not None
        assert retrieved.type == JobType.QUALITY_ANALYSIS
        assert retrieved.status == JobStatus.PENDING
        assert retrieved.entity_id == "/path/to/file.flac"

    def test_cancel_pending_job(self):
        mgr = _make_mgr()
        jid = mgr.create_job(Job(type=JobType.CONVERSION, label="test"))
        assert mgr.cancel_job(jid)

        retrieved = mgr.get_job(jid)
        assert retrieved.status == JobStatus.CANCELLED

    def test_list_jobs_by_status(self):
        mgr = _make_mgr()
        mgr.create_job(Job(type=JobType.FEATURE_EXTRACTION, label="a"))
        mgr.create_job(Job(type=JobType.FEATURE_EXTRACTION, label="b"))

        pending = mgr.list_jobs(JobStatus.PENDING)
        assert len(pending) == 2

    def test_pending_count(self):
        mgr = _make_mgr()
        assert mgr.pending_count == 0
        mgr.create_job(Job(type=JobType.LIBRARY_VERIFY, label="test"))
        assert mgr.pending_count == 1

    def test_delete_job(self):
        mgr = _make_mgr()
        jid = mgr.create_job(Job(type=JobType.CONVERSION))
        mgr._repo.delete_job(jid)
        assert mgr.get_job(jid) is None

    def test_handler_execution(self):
        mgr = _make_mgr()
        results = []

        def handler(job, progress_cb):
            progress_cb(0.5)
            results.append("done")
            return {"ok": True}

        mgr.register_handler(JobType.CONVERSION, handler)

        jid = mgr.create_job(Job(type=JobType.CONVERSION, label="handler_test"))
        assert mgr.start_job(jid)

        retrieved = mgr.get_job(jid)
        assert retrieved.status == JobStatus.COMPLETED
        assert results == ["done"]
        assert retrieved.result == {"ok": True}

    def test_handler_failure(self):
        mgr = _make_mgr()

        def handler(job, progress_cb):
            raise ValueError("test error")

        mgr.register_handler(JobType.CONVERSION, handler)
        jid = mgr.create_job(Job(type=JobType.CONVERSION))
        mgr.start_job(jid)

        retrieved = mgr.get_job(jid)
        assert retrieved.status == JobStatus.FAILED
        assert "test error" in retrieved.error

    def test_cancel_before_start_prevents_execution(self):
        mgr = _make_mgr()

        def handler(job, progress_cb):
            raise RuntimeError("should not run")

        mgr.register_handler(JobType.RIPPING, handler)
        jid = mgr.create_job(Job(type=JobType.RIPPING))
        assert mgr.cancel_job(jid)
        retrieved = mgr.get_job(jid)
        assert retrieved.status == JobStatus.CANCELLED

    def test_process_queue_runs_pending_jobs(self):
        mgr = _make_mgr()

        results = []

        def handler(job, progress_cb):
            results.append(job.id)
            progress_cb(1.0)
            return {}

        mgr.register_handler(JobType.QUALITY_ANALYSIS, handler)
        jid1 = mgr.create_job(Job(type=JobType.QUALITY_ANALYSIS))
        jid2 = mgr.create_job(Job(type=JobType.QUALITY_ANALYSIS))

        count = mgr.process_queue(max_jobs=2)
        assert count == 2
        assert len(results) == 2
        assert mgr.get_job(jid1).status == JobStatus.COMPLETED
        assert mgr.get_job(jid2).status == JobStatus.COMPLETED
