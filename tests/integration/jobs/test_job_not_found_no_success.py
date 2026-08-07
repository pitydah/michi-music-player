"""Fase Jobs: cancel/retry on a NONEXISTENT job id must return an explicit
error — never {"ok": True}."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.isolation


def test_cancel_and_retry_on_nonexistent_job_never_succeed(tmp_path):
    from core.jobs.job_service import DurableJobService
    from core.notification_action_service import NotificationActionService
    from ui_qml_bridge.job_bridge import JobBridge

    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))

    # Service level.
    assert svc.cancel_job("does_not_exist") is False
    assert svc.retry_job("does_not_exist") is False
    assert svc.get_job("does_not_exist") is None

    # JobBridge level.
    bridge = JobBridge(job_service=svc)
    cancel_result = bridge.cancelJob("does_not_exist")
    assert cancel_result["ok"] is False, cancel_result
    assert cancel_result["error"] == "NOT_FOUND"
    retry_result = bridge.retryJob("does_not_exist")
    assert retry_result["ok"] is False, retry_result
    assert retry_result["error"] == "NOT_FOUND"

    # Notification action level.
    actions = NotificationActionService(job_service=svc)
    action_result = actions.route("retry", {"job_id": "does_not_exist"})
    assert action_result["ok"] is False, action_result
    assert action_result["status"] == "ACTION_NOT_FOUND"


def test_cancel_of_terminal_job_is_not_a_false_success(tmp_path):
    """Cancelling an already-terminal job is NOT ok=True: it is an explicit
    NOT_CANCELLABLE error from the bridge (never 'already': True)."""
    from core.jobs.job_service import DurableJobService, JobState
    from ui_qml_bridge.job_bridge import JobBridge

    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))
    job_id = svc.create_job("some_type", owner="test")
    assert svc.cancel_job(job_id) is True
    assert svc.get_job(job_id).state == JobState.CANCELLED

    bridge = JobBridge(job_service=svc)
    result = bridge.cancelJob(job_id)
    assert result["ok"] is False, result
    assert result["error"] == "NOT_CANCELLABLE"
    assert "already" not in result
