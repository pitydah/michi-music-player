from __future__ import annotations
"""DW — Durable JobService tests: contract, state machine, lifecycle.
States: QUEUED, RUNNING, PAUSING, PAUSED, CANCELLING, CANCELLED,
        SUCCEEDED, PARTIAL_SUCCESS, FAILED, INTERRUPTED.
On restart, RUNNING -> INTERRUPTED.
"""

import os
import tempfile
import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("job_bridge")]


def _process_events(duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


class TestJobsDurable:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def svc(self, app, db_path):
        from core.jobs.job_service import DurableJobService
        s = DurableJobService(db_path=db_path)
        return s

    def test_contract_has_all_fields(self, svc):
        from core.jobs.job_service import DurableJob
        job = DurableJob()
        assert hasattr(job, "id")
        assert hasattr(job, "type")
        assert hasattr(job, "owner")
        assert hasattr(job, "state")
        assert hasattr(job, "createdAt")
        assert hasattr(job, "startedAt")
        assert hasattr(job, "finishedAt")
        assert hasattr(job, "progress")
        assert hasattr(job, "current")
        assert hasattr(job, "total")
        assert hasattr(job, "message")
        assert hasattr(job, "warnings")
        assert hasattr(job, "errors")
        assert hasattr(job, "cancellable")
        assert hasattr(job, "pausable")
        assert hasattr(job, "retryable")
        assert hasattr(job, "payload")
        assert hasattr(job, "result")
        assert hasattr(job, "processId")

    def test_create_job_returns_id(self, svc):
        job_id = svc.create_job("scan", owner="test")
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_create_job_default_state(self, svc):
        job_id = svc.create_job("conversion")
        job = svc.get_job(job_id)
        assert job is not None
        from core.jobs.job_service import JobState
        assert job.state == JobState.QUEUED

    def test_create_job_stores_payload(self, svc):
        job_id = svc.create_job("analysis", payload={"filepath": "/test.flac"})
        job = svc.get_job(job_id)
        assert job.payload.get("filepath") == "/test.flac"

    def test_start_job_transitions_to_running(self, svc):
        def handler(job, progress_cb):
            return {"ok": True}
        svc.register_handler("test_type", handler)
        job_id = svc.create_job("test_type")
        ok = svc.start_job(job_id)
        assert ok is True
        job = svc.get_job(job_id)
        from core.jobs.job_service import JobState
        assert job.state == JobState.SUCCEEDED

    def test_start_job_fails_no_handler(self, svc):
        job_id = svc.create_job("no_handler")
        svc.start_job(job_id)
        job = svc.get_job(job_id)
        from core.jobs.job_service import JobState
        assert job.state == JobState.FAILED

    def test_pause_job(self, svc):
        job_id = svc.create_job("test_pause", pausable=True)
        ok = svc.pause_job(job_id)
        from core.jobs.job_service import JobState
        assert ok is True
        job = svc.get_job(job_id)
        assert job.state == JobState.PAUSED

    def test_pause_nonpausable_returns_false(self, svc):
        job_id = svc.create_job("test", pausable=False)
        ok = svc.pause_job(job_id)
        assert ok is False

    def test_resume_job(self, svc):
        job_id = svc.create_job("test_resume")
        svc.pause_job(job_id)
        ok = svc.resume_job(job_id)
        assert ok is True
        job = svc.get_job(job_id)
        from core.jobs.job_service import JobState
        assert job.state == JobState.QUEUED

    def test_cancel_queued_job(self, svc):
        job_id = svc.create_job("test_cancel")
        ok = svc.cancel_job(job_id)
        assert ok is True
        job = svc.get_job(job_id)
        from core.jobs.job_service import TERMINAL_STATES
        assert job.state in TERMINAL_STATES

    def test_retry_failed_job(self, svc):
        def handler(job, progress_cb):
            raise RuntimeError("fail")
        svc.register_handler("fail_type", handler)
        job_id = svc.create_job("fail_type", retryable=True)
        svc.start_job(job_id)
        ok = svc.retry_job(job_id)
        assert ok is True
        job = svc.get_job(job_id)
        from core.jobs.job_service import JobState

        assert job.state == JobState.QUEUED

    def test_retry_nonretryable_returns_false(self, svc):
        def handler(job, progress_cb):
            raise RuntimeError("fail")
        svc.register_handler("fail_type2", handler)
        job_id = svc.create_job("fail_type2", retryable=False)
        svc.start_job(job_id)
        ok = svc.retry_job(job_id)
        assert ok is False

    def test_list_jobs_by_state(self, svc):
        svc.create_job("scan_a")
        svc.create_job("scan_b")
        jobs = svc.list_jobs()
        assert len(jobs) >= 2

    def test_list_jobs_by_type(self, svc):
        svc.create_job("import", owner="u1")
        svc.create_job("export", owner="u2")
        exports = svc.list_jobs(job_type="export")
        assert all(j["type"] == "export" for j in exports)

    def test_signal_created_emitted(self, svc):
        received = []
        svc.jobCreated.connect(lambda jid: received.append(jid))
        job_id = svc.create_job("signal_test")
        _process_events(0.2)
        assert job_id in received

    def test_signal_completed_emitted(self, svc):
        def handler(job, progress_cb):
            return {"ok": True}
        svc.register_handler("compl_type", handler)
        received = []
        svc.jobCompleted.connect(lambda jid, res: received.append(jid))
        job_id = svc.create_job("compl_type")
        svc.start_job(job_id)
        _process_events(0.5)
        assert job_id in received

    def test_update_progress(self, svc):
        job_id = svc.create_job("progress_test", total=10)
        svc.update_progress(job_id, 5, 10, "Mitad")
        job = svc.get_job(job_id)
        assert job.current == 5
        assert job.total == 10
        assert job.progress == 0.5
        assert job.message == "Mitad"

    def test_add_warning_and_error(self, svc):
        job_id = svc.create_job("warn_test")
        svc.add_warning(job_id, "cuidado")
        svc.add_error(job_id, "error grave")
        job = svc.get_job(job_id)
        assert len(job.warnings) == 1
        assert len(job.errors) == 1
        assert job.warnings[0] == "cuidado"
        assert job.errors[0] == "error grave"
