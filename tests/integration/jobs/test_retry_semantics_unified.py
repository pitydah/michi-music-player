"""Fase Jobs: JobBridge.retryJob and NotificationActionService.retry must go
through the SAME service method (job_service.retry_job) with identical
semantics: validate, preserve the original payload, transition to QUEUED,
start immediately when capacity allows, emit, persist, read back the real
state. The bridge must NOT re-invoke runJob with empty params."""
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


@pytest.fixture
def job_env(tmp_path):
    from core.jobs.job_service import DurableJobService
    from core.worker_manager import WorkerManager

    wm = WorkerManager()
    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"),
                            worker_manager=wm)
    attempts = {"count": 0}

    def flaky_handler(job, ctx):
        ctx.report_progress(0.5, "working")
        attempts["count"] += 1
        if attempts["count"] % 2 == 1:  # odd invocations fail, even succeed
            raise RuntimeError("TRANSIENT_FAILURE")
        payload = job.payload or {}
        return {"ok": True, "applied": len(payload.get("files", []))}

    svc.register_handler("flaky_batch", flaky_handler)
    yield svc, attempts
    wm.shutdown()


def _make_failed_job(app, svc, tag: str) -> str:
    from core.jobs.job_service import JobState
    job_id = svc.create_job(
        "flaky_batch", owner="metadata_bridge",
        payload={"files": [f"{tag}_a.flac", f"{tag}_b.flac"]},
        retryable=True,
    )
    assert svc.start_job(job_id) is True
    deadline = time.time() + 10
    while time.time() < deadline:
        app.processEvents()
        if svc.get_job(job_id).state == JobState.FAILED:
            break
        time.sleep(0.02)
    assert svc.get_job(job_id).state == JobState.FAILED
    return job_id


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


def test_bridge_retry_and_notification_retry_share_one_service_method(
    app, job_env,
):
    from unittest.mock import patch

    from core.jobs.job_service import JobState
    from core.notification_action_service import NotificationActionService
    from ui_qml_bridge.job_bridge import JobBridge

    svc, attempts = job_env

    # Path 1: JobBridge.retryJob.
    bridge = JobBridge(job_service=svc)
    job_a = _make_failed_job(app, svc, "bridge")
    with patch.object(svc, "retry_job", wraps=svc.retry_job) as spy:
        result = bridge.retryJob(job_a)
        assert spy.call_count == 1, "bridge retry must go through retry_job"
    assert result["ok"] is True, result
    assert result["job_id"] == job_a
    assert result["state"] == JobState.RUNNING.value
    assert _wait_terminal(app, svc, job_a) == JobState.SUCCEEDED.value
    assert svc.get_job(job_a).payload["files"] == [
        "bridge_a.flac", "bridge_b.flac",
    ], "payload must be preserved"

    # Path 2: NotificationActionService.retry.
    actions = NotificationActionService(job_service=svc)
    job_b = _make_failed_job(app, svc, "notif")
    with patch.object(svc, "retry_job", wraps=svc.retry_job) as spy:
        result = actions.route("retry", {"job_id": job_b})
        assert spy.call_count == 1, (
            "notification retry must go through retry_job"
        )
    assert result["ok"] is True, result
    assert result["job_id"] == job_b
    assert result["payload_preserved"] is True
    assert _wait_terminal(app, svc, job_b) == JobState.SUCCEEDED.value
    assert svc.get_job(job_b).payload["files"] == [
        "notif_a.flac", "notif_b.flac",
    ]

    # Exactly two retries consumed: one per path.
    assert attempts["count"] == 4  # 2 initial failures + 2 successful retries
    jobs = svc.list_jobs(job_type="flaky_batch")
    assert len(jobs) == 2, "retry must never duplicate a job"
