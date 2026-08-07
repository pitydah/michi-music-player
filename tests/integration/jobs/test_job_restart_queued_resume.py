"""Fase Jobs: QUEUED jobs restored after restart must be resumed by the boot
policy (resume_pending_jobs after handlers are registered) — never left
silently stopped. Handler-less QUEUED jobs are covered in
test_missing_handler_persisted_failure.py."""
from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

pytestmark = pytest.mark.isolation


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


def _fast_handler(job, ctx):
    return {"ok": True, "type": job.type}


def _wait_terminal(app, svc, job_id, timeout=20.0) -> str:
    from core.jobs.job_service import JobState
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        job = svc.get_job(job_id)
        if job is None:
            return "GONE"
        if job.state in (JobState.SUCCEEDED, JobState.FAILED,
                         JobState.PARTIAL_SUCCESS, JobState.CANCELLED):
            return job.state.value
        time.sleep(0.02)
    return svc.get_job(job_id).state.value


def test_queued_job_auto_resumed_at_boot_after_handlers_registered(app, tmp_path):
    from core.jobs.job_service import DurableJobService, JobState
    from core.worker_manager import WorkerManager

    db_path = str(tmp_path / "jobs.db")

    # Phase 1: a QUEUED job is persisted (previous process crashed before
    # the queue was processed).
    svc_a = DurableJobService(db_path=db_path)
    queued_id = svc_a.create_job(
        "resumable_scan", owner="job_bridge",
        payload={"folder_path": "/music/boot"},
    )
    assert svc_a.get_job(queued_id).state == JobState.QUEUED
    del svc_a

    # Phase 2: restart — handlers registered BEFORE the boot resume runs.
    wm = WorkerManager()
    try:
        svc_b = DurableJobService(db_path=db_path, worker_manager=wm)
        svc_b.register_handler("resumable_scan", _fast_handler)

        stats = svc_b.resume_pending_jobs()
        assert stats["queued"] == 1
        assert stats["handler_unavailable"] == 0
        assert stats["resumed"] == 1

        state = _wait_terminal(app, svc_b, queued_id)
        assert state == JobState.SUCCEEDED.value, f"job stuck in {state}"
        readback = svc_b.get_job(queued_id)
        assert readback.payload["folder_path"] == "/music/boot"
        assert readback.result["type"] == "resumable_scan"
    finally:
        wm.shutdown()
