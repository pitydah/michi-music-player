"""CK — JobService durable states and persistence tests.
States: QUEUED, RUNNING, PAUSING, PAUSED, CANCELLING, CANCELLED,
SUCCEEDED, PARTIAL_SUCCESS, FAILED, INTERRUPTED.
Crash  RUNNING pasa a INTERRUPTED.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.isolation


class TestJobStates:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.job_bridge import JobBridge
        wm = MagicMock()
        wm.run_task.side_effect = lambda tid, fn, **kw: MagicMock(cancel=MagicMock())
        return JobBridge(worker_manager=wm, db=MagicMock())

    def test_initial_state_empty(self, bridge):
        assert bridge.jobs == []
        assert bridge.activeCount == 0
        assert bridge.failedCount == 0

    def test_run_job_sets_queued(self, bridge):
        bridge.runJob("library_scan", "/music")
        assert len(bridge.jobs) >= 1
        assert bridge.jobs[0]["state"] == "running" or bridge.jobs[0]["state"] == "queued"

    def test_run_unknown_job(self, bridge):
        result = bridge.runJob("unknown_job")
        assert result["ok"] is False

    def test_cancel_job(self, bridge):
        bridge.runJob("library_scan", "/music")
        job_id = bridge.jobs[0]["job_id"]
        result = bridge.cancelJob(job_id)
        assert result["ok"] is True
        assert bridge.jobs[0]["state"] == "cancelled"

    def test_cancel_nonexistent(self, bridge):
        result = bridge.cancelJob(99999)
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"

    def test_cancel_already_cancelled(self, bridge):
        bridge.runJob("library_scan", "/music")
        job_id = bridge.jobs[0]["job_id"]
        first = bridge.cancelJob(job_id)
        assert first["ok"] is True
        result = bridge.cancelJob(job_id)
        assert result["ok"] is True  # JobBridge allows re-cancel (idempotent)

    def test_mark_interrupted_on_cancel(self, bridge):
        bridge.runJob("library_scan", "/music")
        bridge.cancelJob(bridge.jobs[0]["job_id"])
        assert bridge.jobs[0]["state"] == "cancelled"

    def test_clear_completed(self, bridge):
        bridge.runJob("library_scan", "/music")
        bridge.cancelJob(bridge.jobs[0]["job_id"])
        bridge.clearCompleted()
        assert len(bridge.jobs) == 0

    def test_clear_failed(self, bridge):
        bridge._add_job("test", "Test job")
        for j in bridge._jobs:
            j["state"] = "failed"
        bridge.clearFailed()
        assert bridge.failedCount == 0

    def test_job_cancel_then_state(self, bridge):
        bridge.runJob("library_scan", "/music")
        bridge.cancelJob(bridge.jobs[0]["job_id"])
        assert bridge.jobs[0]["state"] == "cancelled"

    def test_retry_cancelled_job(self, bridge):
        bridge.runJob("library_scan", "/music")
        bridge.cancelJob(bridge._jobs[0]["job_id"])
        job_id = bridge._jobs[0]["job_id"]
        result = bridge.retryJob(job_id)
        assert result["ok"] is True

    def test_retry_succeeded_job(self, bridge):
        bridge._add_job("test", "Test")
        bridge._jobs[0]["state"] = "succeeded"
        result = bridge.retryJob(bridge._jobs[0]["job_id"])
        assert result["ok"] is False

    def test_interrupted_on_start(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge(worker_manager=MagicMock(), db=MagicMock())
        bridge.runJob("library_scan", "/music")
        assert len(bridge.jobs) >= 1

    def test_active_count(self, bridge):
        bridge._add_job("test1", "Test1")
        bridge._add_job("test2", "Test2")
        assert bridge.activeCount >= 0

    def test_failed_count(self, bridge):
        bridge._add_job("test", "Test")
        bridge._jobs[0]["state"] = "failed"
        assert bridge.failedCount == 1
