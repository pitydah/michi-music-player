"""Fase Jobs: a RUNNING job from a crashed process must be recovered as
INTERRUPTED, VISIBLE in list_jobs, retryable, and retry_job must re-queue it
with the ORIGINAL payload and start it (real WorkerManager)."""
from __future__ import annotations

import os
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

pytestmark = pytest.mark.isolation


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


def _blocking_handler(event: threading.Event, cancelled_holder: list):
    """Handler that runs until *event* is set or the token is cancelled."""

    def handler(job, ctx):
        while not event.is_set():
            ctx.token.raise_if_cancelled()
            time.sleep(0.01)
        cancelled_holder.append(job.payload or {})
        return {"ok": True, "finished": True}

    return handler


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


def test_restart_running_job_interrupted_visible_retryable_and_starts(
    app, tmp_path,
):
    """Simulated crash: RUNNING row survives; a fresh service marks it
    INTERRUPTED (in list_jobs), retry_job re-queues with the original payload
    and the job RUNS to a terminal state on the real WorkerManager."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.worker_manager import WorkerManager

    db_path = str(tmp_path / "jobs.db")
    release = threading.Event()
    seen: list = []

    wm_a = WorkerManager()
    svc_a = DurableJobService(db_path=db_path, worker_manager=wm_a)
    svc_a.register_handler("library_scan", _blocking_handler(release, seen))
    job_id = svc_a.create_job(
        "library_scan", owner="job_bridge",
        payload={"folder_path": "/music/original", "note": "keep-me"},
        total=10,
    )
    assert svc_a.start_job(job_id) is True
    job_a = svc_a.get_job(job_id)
    assert job_a.state == JobState.RUNNING
    # RUNNING state is persisted before the handler runs (crash artifact).
    del svc_a

    # Simulated restart: fresh service over the same DB (no handlers yet).
    wm_b = WorkerManager()
    try:
        svc_b = DurableJobService(db_path=db_path, worker_manager=wm_b)
        recovered = svc_b.get_job(job_id)
        assert recovered is not None, "RUNNING job must be recovered"
        assert recovered.state == JobState.INTERRUPTED
        assert recovered.message == "Interrumpido por reinicio"

        listed = {d["id"] for d in svc_b.list_jobs()}
        assert job_id in listed, (
            "recovered INTERRUPTED job must be visible in list_jobs"
        )
        assert recovered.payload["note"] == "keep-me"

        # Register the handler on the new instance, then retry.
        svc_b.register_handler("library_scan", _blocking_handler(release, seen))
        assert svc_b.retry_job(job_id) is True, "recovered job must be retryable"
        retried = svc_b.get_job(job_id)
        assert retried.state == JobState.QUEUED or retried.state == JobState.RUNNING
        assert retried.payload["folder_path"] == "/music/original", (
            "retry must preserve the original payload"
        )

        release.set()
        state = _wait_terminal(app, svc_b, job_id)
        assert state == JobState.SUCCEEDED.value, f"job stuck in {state}"
        readback = svc_b.get_job(job_id)
        assert readback.state == JobState.SUCCEEDED
        assert readback.result.get("finished") is True
        assert readback.payload["note"] == "keep-me"
    finally:
        release.set()
        wm_b.shutdown()
        wm_a.shutdown()
