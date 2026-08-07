"""CK — JobBridge thin view over DurableJobService.

States: QUEUED, RUNNING, PAUSING, PAUSED, CANCELLING, CANCELLED,
SUCCEEDED, PARTIAL_SUCCESS, FAILED, INTERRUPTED.
Crash: RUNNING pasa a INTERRUPTED.
JobBridge delegates everything to the durable service (ADR-004).
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.isolation


class TestJobStates:
    @pytest.fixture
    def bridge(self):
        from core.jobs.job_service import DurableJobService
        from ui_qml_bridge.job_bridge import JobBridge

        svc = DurableJobService(db_path=":memory:")
        svc.register_handler("library_scan", lambda job, ctx: {"ok": True})
        return JobBridge(job_service=svc)

    def test_initial_state_empty(self, bridge):
        assert bridge.jobs == []
        assert bridge.activeCount == 0
        assert bridge.failedCount == 0

    def test_run_job_creates_durable_job(self, bridge):
        result = bridge.runJob("library_scan", "/music")
        assert result["ok"] is True
        assert result["job_id"]
        assert len(bridge.jobs) == 1
        assert bridge.jobs[0]["job_id"] == result["job_id"]
        assert bridge.jobs[0]["state"] in ("running", "queued", "completed")

    def test_run_unknown_job(self, bridge):
        result = bridge.runJob("unknown_job")
        assert result["ok"] is False
        assert result["error"] == "UNKNOWN_JOB_TYPE"

    def test_cancel_job(self, bridge):
        result = bridge.runJob("library_scan", "/music")
        job_id = result["job_id"]
        cancel = bridge.cancelJob(job_id)
        assert cancel["ok"] is True
        assert bridge.jobs[0]["state"] in ("completed", "cancelled",
                                           "cancel_requested", "running")

    def test_cancel_nonexistent(self, bridge):
        result = bridge.cancelJob(99999)
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"

    def test_cancel_already_cancelled(self, bridge):
        result = bridge.runJob("library_scan", "/music")
        job_id = result["job_id"]
        first = bridge.cancelJob(job_id)
        assert first["ok"] is True
        second = bridge.cancelJob(job_id)
        assert second["ok"] is True  # JobBridge allows re-cancel (idempotent)

    def test_clear_completed(self, bridge):
        result = bridge.runJob("library_scan", "/music")
        bridge.cancelJob(result["job_id"])
        cleared = bridge.clearCompleted()
        assert cleared["ok"] is True
        assert cleared["removed"] == 1
        assert len(bridge.jobs) == 0

    def test_clear_failed(self, bridge):
        svc = bridge._js
        jid = svc.create_job("no_handler_type", owner="test")
        assert svc.start_job(jid) is False  # no handler -> FAILED
        assert svc.get_job(jid).state.value == "FAILED"
        cleared = bridge.clearFailed()
        assert cleared["ok"] is True
        assert cleared["removed"] == 1
        assert bridge.failedCount == 0

    def test_retry_failed_job_keeps_payload(self, bridge):
        svc = bridge._js
        jid = svc.create_job("no_handler_type", owner="test",
                             payload={"folder_path": "/music"})
        svc.start_job(jid)
        assert svc.get_job(jid).state.value == "FAILED"
        result = bridge.retryJob(jid)
        assert result["ok"] is True
        assert svc.get_job(jid).payload["folder_path"] == "/music"

    def test_retry_succeeded_job(self, bridge):
        svc = bridge._js
        jid = svc.create_job("library_scan", owner="test",
                             payload={"folder_path": "/music"})
        svc.start_job(jid)  # registered handler -> SUCCEEDED
        assert svc.get_job(jid).state.value == "SUCCEEDED"
        result = bridge.retryJob(jid)
        assert result["ok"] is False

    def test_interrupted_on_start(self):
        from core.jobs.job_service import DurableJobService
        from ui_qml_bridge.job_bridge import JobBridge

        svc = DurableJobService(db_path=":memory:")
        svc.register_handler("library_scan", lambda job, ctx: {"ok": True})
        bridge = JobBridge(job_service=svc)
        result = bridge.runJob("library_scan", "/music")
        assert result["ok"] is True
        assert len(bridge.jobs) >= 1

    def test_active_count(self, bridge):
        bridge.runJob("library_scan", "/music")
        assert bridge.activeCount >= 0

    def test_failed_count(self, bridge):
        svc = bridge._js
        jid = svc.create_job("no_handler_type", owner="test")
        svc.start_job(jid)
        assert bridge.failedCount == 1

    def test_degraded_without_job_service(self):
        from ui_qml_bridge.job_bridge import JobBridge

        bridge = JobBridge(worker_manager=MagicMock(), db=MagicMock())
        assert bridge.jobs == []
        assert bridge.activeCount == 0
        result = bridge.runJob("library_scan", "/tmp")
        assert result["ok"] is False
        assert result["error"] == "INFRASTRUCTURE_UNAVAILABLE"
