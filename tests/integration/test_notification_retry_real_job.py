"""Notification retry must re-run the ORIGINAL durable job with its original
payload (never duplicate the notification), and the job must reach a terminal
state. Uses the real DurableJobService (synchronous path) + the canonical
NotificationActionService.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def job_env(tmp_path):
    from core.jobs.job_service import DurableJobService
    from core.notification_action_service import NotificationActionService
    from core.notification_service import NotificationService

    js = DurableJobService(db_path=str(tmp_path / "jobs.db"))
    attempts = {"count": 0}

    def flaky_handler(job, ctx):
        ctx.report_progress(0.5, "working")
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("TRANSIENT_FAILURE")
        payload = job.payload or {}
        return {"ok": True, "applied": len(payload.get("files", []))}

    js.register_handler("flaky_batch", flaky_handler)
    ns = NotificationService(persistence_path=str(tmp_path / "notif.json"))
    action_svc = NotificationActionService(job_service=js)
    return js, ns, action_svc, attempts


class TestNotificationRetryRealJob:
    def test_retry_reruns_original_payload_until_success(self, job_env):
        js, ns, action_svc, attempts = job_env

        job_id = js.create_job(
            "flaky_batch", owner="metadata_bridge",
            payload={"files": ["a.flac", "b.flac"]},
            retryable=True,
        )
        assert js.start_job(job_id) is True
        job = js.get_job(job_id)
        assert job.state.value == "FAILED"
        assert job.errors == ["TRANSIENT_FAILURE"]

        from core.notification_service import Notification, NotificationType

        notif = ns.notify(Notification(
            type=NotificationType.ERROR, title="Lote falló",
            message="Intento fallido", job_id=job_id,
            actions=["retry"], persistent=True,
        ))
        assert notif.job_id == job_id

        result = action_svc.route("retry", {"job_id": job_id})
        assert result["ok"] is True, result
        assert result["job_id"] == job_id
        assert result["payload_preserved"] is True

        job = js.get_job(job_id)
        assert job.state.value == "SUCCEEDED"
        assert job.result.get("applied") == 2
        assert attempts["count"] == 2

        jobs = js.list_jobs(job_type="flaky_batch")
        assert len(jobs) == 1, "retry must NOT duplicate the job"

    def test_retry_unknown_job_is_action_not_found(self, job_env):
        _js, _ns, action_svc, _attempts = job_env
        result = action_svc.route("retry", {"job_id": "does_not_exist"})
        assert result["ok"] is False
        assert result["status"] == "ACTION_NOT_FOUND"

    def test_retry_without_job_id_is_target_unavailable(self, job_env):
        _js, _ns, action_svc, _attempts = job_env
        result = action_svc.route("retry", {})
        assert result["ok"] is False
        assert result["status"] == "TARGET_UNAVAILABLE"

    def test_unknown_action_is_action_not_found(self, job_env):
        _js, _ns, action_svc, _attempts = job_env
        result = action_svc.route("no_such_action", {})
        assert result["ok"] is False
        assert result["status"] == "ACTION_NOT_FOUND"

    def test_unwired_services_are_capability_unavailable(self):
        from core.notification_action_service import NotificationActionService

        bare = NotificationActionService()
        result = bare.route("retry", {"job_id": "x"})
        assert result["status"] == "CAPABILITY_UNAVAILABLE"
        result = bare.route("undo", {"operation_id": "x"})
        assert result["status"] == "CAPABILITY_UNAVAILABLE"
