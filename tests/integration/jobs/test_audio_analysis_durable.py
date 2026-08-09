"""Phase 2 tests: Bridge creates and manages durable analysis jobs.

RED phase tests (2.1) validate startAnalysis contract.
GREEN phase tests (2.4) validate lifecycle: cancel, retry, cleanup, status.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QCoreApplication  # noqa: E402

pytestmark = pytest.mark.isolation


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


@pytest.fixture
def job_service(tmp_path):
    from core.jobs.handlers import make_analysis_handler
    from core.jobs.job_service import DurableJobService

    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))
    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed", "features": {"bpm": 120}}
    svc.register_handler("analysis", make_analysis_handler(port))
    return svc


# ── 2.1: startAnalysis contract ──


def test_start_analysis_creates_and_starts_durable_job(app, job_service):
    """startAnalysis creates a durable job of type 'analysis' with owner 'audio_lab'."""
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    result = bridge.startAnalysis("/tracks/foo.flac")

    assert result.get("ok") is True, f"Expected ok=True, got {result}"
    job_id = result.get("job_id")
    assert job_id, "startAnalysis must return a job_id"

    durable = job_service.get_job(job_id)
    assert durable is not None, (
        f"Expected durable job {job_id} to exist in job_service, "
        "but it was not found — startAnalysis must use create_job"
    )
    assert durable.type == "analysis"
    assert durable.owner == "audio_lab"
    payload = durable.payload.get("request") or {}
    assert payload.get("filepath") == "/tracks/foo.flac"


def test_start_analysis_returns_service_unavailable_when_job_service_is_none(app):
    """startAnalysis returns SERVICE_UNAVAILABLE when self._jobs is None."""
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=None)
    result = bridge.startAnalysis("/tracks/foo.flac")

    assert result.get("ok") is False
    assert result.get("error_code") == "SERVICE_UNAVAILABLE"


def test_start_analysis_fails_when_no_handler_registered(app, tmp_path):
    """start_job returns False when no handler registered for 'analysis'."""
    from core.jobs.job_service import DurableJobService
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    svc = DurableJobService(db_path=str(tmp_path / "no_handler.db"))
    bridge = AudioLabBridge(job_service=svc)
    result = bridge.startAnalysis("/tracks/foo.flac")

    assert result.get("ok") is False
    error = result.get("error") or ""
    assert ("handler" in error.lower()) or ("HANDLER_UNAVAILABLE" in str(result.get("error_code", "")))


# ── 2.4: cancelJob, retryJob, cleanupCompleted, jobStatus, activeJobs ──


def test_cancel_job_delegates_to_durable_service(app, job_service):
    """cancelJob calls cancel_job on the durable service for analysis jobs."""
    from core.jobs.job_service import JobState
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = result["job_id"]

    durable = job_service.get_job(job_id)
    durable.state = JobState.RUNNING

    cancel_result = bridge.cancelJob(job_id)
    assert cancel_result.get("ok") is True, f"Expected ok=True, got {cancel_result}"
    assert cancel_result.get("job_id") == job_id

    durable = job_service.get_job(job_id)
    assert durable is not None
    assert durable.state in (JobState.CANCELLED, JobState.CANCELLING)


def test_cancel_job_returns_not_found_for_unknown_id(app, job_service):
    """cancelJob returns JOB_NOT_FOUND for unknown job_id."""
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    result = bridge.cancelJob("nonexistent")

    assert result.get("ok") is False
    assert result.get("error_code") == "JOB_NOT_FOUND"


def test_retry_job_reuses_same_id(app, job_service):
    """retryJob reuses the same job_id (not a new one)."""
    from core.jobs.job_service import JobState
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    original_id = start_result["job_id"]

    durable = job_service.get_job(original_id)
    durable.state = JobState.FAILED
    durable.retryable = True

    retry_result = bridge.retryJob(original_id)
    assert retry_result.get("ok") is True
    assert retry_result.get("job_id") == original_id

    retried = job_service.get_job(original_id)
    assert retried is not None


def test_cleanup_completed_deletes_terminal_audio_lab_jobs(app, tmp_path):
    """cleanupCompleted deletes terminal audio_lab-owned jobs only."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.jobs.handlers import make_analysis_handler
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    svc = DurableJobService(db_path=str(tmp_path / "cleanup.db"))
    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed"}
    svc.register_handler("analysis", make_analysis_handler(port))

    bridge = AudioLabBridge(job_service=svc)
    r1 = bridge.startAnalysis("/tracks/a.flac")
    r2 = bridge.startAnalysis("/tracks/b.flac")

    svc.get_job(r1["job_id"]).state = JobState.SUCCEEDED
    svc.get_job(r2["job_id"]).state = JobState.FAILED

    result = bridge.cleanupCompleted()
    assert result.get("ok") is True
    assert result.get("cleaned", 0) >= 2


def test_job_status_reads_from_durable_store(app, job_service):
    """jobStatus reads from the durable job store."""
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = start_result["job_id"]

    status = bridge.jobStatus(job_id)
    assert status.get("ok") is True
    assert "state" in status
    assert status.get("type") == "analysis"


def test_job_status_returns_not_found(app, job_service):
    """jobStatus returns JOB_NOT_FOUND for unknown job_id."""
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    status = bridge.jobStatus("nonexistent")

    assert status.get("ok") is False
    assert status.get("error_code") == "JOB_NOT_FOUND"


def test_active_jobs_includes_durable_jobs(app, job_service):
    """activeJobs property includes durable analysis jobs in active states."""
    from core.jobs.job_service import JobState
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = start_result["job_id"]

    # The synchronous path completes immediately (SUCCEEDED), so force
    # RUNNING to simulate an in-flight job visible in activeJobs.
    durable = job_service.get_job(job_id)
    assert durable is not None
    durable.state = JobState.RUNNING

    jobs = bridge.activeJobs()
    job_ids = [j.get("id") for j in jobs]
    assert job_id in job_ids, f"activeJobs must include RUNNING durable job {job_id}"

    # Terminal states must NOT appear in activeJobs.
    durable.state = JobState.SUCCEEDED
    jobs = bridge.activeJobs()
    job_ids = [j.get("id") for j in jobs]
    assert job_id not in job_ids, (
        f"SUCCEEDED job {job_id} must NOT appear in activeJobs"
    )


def test_durable_signal_reemission_filtered_by_owner_and_type(app, job_service):
    """Durable signals are re-emitted only for owner='audio_lab' and type='analysis'."""
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    spy = MagicMock()
    bridge.jobProgress.connect(spy)

    bridge._on_durable_progress("some_id", 0.5)
    spy.assert_not_called()

    bridge._on_durable_progress("some_id", 0.7)
    spy.assert_not_called()


def test_non_analysis_signals_not_reemitted(app, job_service):
    """Non-analysis job signals are NOT re-emitted through durable path."""
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    spy_progress = MagicMock()
    spy_completed = MagicMock()
    spy_failed = MagicMock()
    bridge.jobProgress.connect(spy_progress)
    bridge.jobCompleted.connect(spy_completed)
    bridge.jobFailed.connect(spy_failed)

    bridge._on_durable_progress("conv_abc", 0.5)
    bridge._on_durable_completed("conv_abc", {"ok": True})
    bridge._on_durable_failed("conv_abc", "error")

    spy_progress.assert_not_called()
    spy_completed.assert_not_called()
    spy_failed.assert_not_called()


# ── 3.1: Adapter creates analysis jobs as retryable ──


@pytest.mark.skip(reason="M1.3: adapter alignment (retryable=True, handler pre-check)")
def test_adapter_submit_analysis_creates_retryable_job(tmp_path):
    """AudioLabJobAdapter._submit sets retryable=True for analysis operation."""
    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
    from core.jobs.job_service import DurableJobService

    svc = DurableJobService(db_path=str(tmp_path / "adapter_retryable.db"))
    adapter = AudioLabJobAdapter(job_service=svc, analysis=None)

    jid = adapter.submit_analysis("/tracks/foo.flac")
    durable = svc.get_job(jid)
    assert durable is not None
    assert durable.retryable is True


@pytest.mark.skip(reason="M1.3: adapter alignment (retryable=True, handler pre-check)")
def test_adapter_submit_probe_creates_non_retryable_job(tmp_path):
    """AudioLabJobAdapter._submit keeps retryable=False for non-analysis operations."""
    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
    from core.jobs.job_service import DurableJobService

    svc = DurableJobService(db_path=str(tmp_path / "adapter_not_retryable.db"))
    adapter = AudioLabJobAdapter(job_service=svc, probe=None)

    jid = adapter.submit_probe("/tracks/foo.flac")
    durable = svc.get_job(jid)
    assert durable is not None
    assert durable.retryable is False


@pytest.mark.skip(reason="M1.3: adapter alignment (handler pre-check)")
def test_adapter_submit_skips_start_when_handler_missing(tmp_path):
    """Adapter logs warning and skips start_job when handler is not registered."""
    from unittest.mock import patch

    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
    from core.jobs.job_service import DurableJobService, JobState

    svc = DurableJobService(db_path=str(tmp_path / "no_handler_adapter.db"))
    adapter = AudioLabJobAdapter(job_service=svc, analysis=None)

    with patch("core.audio_lab.audio_lab_job_adapter.logger.warning") as mock_warn:
        jid = adapter.submit_analysis("/tracks/foo.flac")

    durable = svc.get_job(jid)
    assert durable is not None
    assert durable.state == JobState.QUEUED
    mock_warn.assert_called_once()
    call_args = mock_warn.call_args[0]
    assert "handler" in str(call_args).lower() or "analysis" in str(call_args).lower()


# ── 4.1: Restart persistence ──


def test_queued_analysis_job_resumes_on_restart_when_handler_registered(tmp_path):
    """QUEUED analysis job is resumed when a new process boots with the handler registered."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.jobs.handlers import make_analysis_handler
    from unittest.mock import MagicMock

    db_path = str(tmp_path / "restart_resume.db")

    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed", "features": {"bpm": 120}}

    svc1 = DurableJobService(db_path=db_path)
    svc1.register_handler("analysis", make_analysis_handler(port))
    jid = svc1.create_job("analysis", owner="audio_lab",
                          payload={"request": {"filepath": "/tracks/foo.flac"}})
    del svc1

    svc2 = DurableJobService(db_path=db_path)
    assert svc2.get_job(jid) is not None
    assert svc2.get_job(jid).state == JobState.QUEUED

    svc2.register_handler("analysis", make_analysis_handler(port))
    stats = svc2.resume_pending_jobs()

    restored = svc2.get_job(jid)
    assert restored is not None
    assert restored.state in (JobState.SUCCEEDED, JobState.RUNNING)
    assert stats["queued"] >= 1
    assert stats["resumed"] >= 1
    assert stats["handler_unavailable"] == 0


def test_queued_analysis_job_fails_handler_unavailable_on_restart(tmp_path):
    """QUEUED analysis job is marked FAILED when handler is NOT registered on boot."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.jobs.handlers import make_analysis_handler
    from unittest.mock import MagicMock

    db_path = str(tmp_path / "restart_no_handler.db")

    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed", "features": {"bpm": 120}}

    svc1 = DurableJobService(db_path=db_path)
    svc1.register_handler("analysis", make_analysis_handler(port))
    jid = svc1.create_job("analysis", owner="audio_lab",
                          payload={"request": {"filepath": "/tracks/foo.flac"}})
    del svc1

    svc2 = DurableJobService(db_path=db_path)
    assert svc2.get_job(jid) is not None
    assert svc2.get_job(jid).state == JobState.QUEUED

    stats = svc2.resume_pending_jobs()

    restored = svc2.get_job(jid)
    assert restored is not None
    assert restored.state == JobState.FAILED
    error_text = restored.errors[0] if restored.errors else ""
    assert "HANDLER_UNAVAILABLE" in error_text
    assert stats["handler_unavailable"] >= 1


# ── 5.1: Signal positive tests ──


def test_durable_progress_signal_reemitted_for_analysis(app, job_service):
    """jobProgress from DurableJobService is re-emitted by AudioLabBridge."""
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = start_result["job_id"]

    spy = MagicMock()
    bridge.jobProgress.connect(spy)

    # Simulate a real progress signal from the durable service.
    job_service.jobProgress.emit(job_id, 0.65)
    spy.assert_called_once_with(job_id, "analysis", 0.65)


def test_durable_completed_signal_reemitted_for_analysis(app, job_service):
    """jobCompleted from DurableJobService is re-emitted by AudioLabBridge."""
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = start_result["job_id"]

    spy = MagicMock()
    bridge.jobCompleted.connect(spy)

    result = {"ok": True, "status": "completed"}
    job_service.jobCompleted.emit(job_id, result)
    spy.assert_called_once_with(job_id, "analysis", result)


def test_durable_failed_signal_reemitted_for_analysis(app, job_service):
    """jobFailed from DurableJobService is re-emitted by AudioLabBridge."""
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = start_result["job_id"]

    spy = MagicMock()
    bridge.jobFailed.connect(spy)

    job_service.jobFailed.emit(job_id, "test error")
    spy.assert_called_once_with(job_id, "test error")


# ── 5.2: Cancel → CANCELLING readback ──


def test_cancel_running_job_returns_cancelling(app, job_service):
    """cancelJob on a RUNNING job returns CANCELLING (not cancelled)."""
    from core.jobs.job_service import JobState
    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    bridge = AudioLabBridge(job_service=job_service)
    start_result = bridge.startAnalysis("/tracks/foo.flac")
    job_id = start_result["job_id"]

    # Force RUNNING so cancel produces CANCELLING.
    durable = job_service.get_job(job_id)
    durable.state = JobState.RUNNING

    result = bridge.cancelJob(job_id)
    assert result.get("ok") is True
    assert result.get("status") in ("cancelling", "cancelled"), (
        f"Expected cancelling/cancelled, got {result.get('status')}"
    )


# ── 5.3: Queue-capacity → QUEUED (not HANDLER_UNAVAILABLE) ──


def test_start_analysis_queued_when_capacity_full(app, tmp_path):
    """startAnalysis returns status=queued when max_concurrent is exhausted."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.jobs.handlers import make_analysis_handler
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    svc = DurableJobService(db_path=str(tmp_path / "capacity_bridge.db"))
    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed"}
    svc.register_handler("analysis", make_analysis_handler(port))
    svc._max_concurrent = 0  # simulate full capacity

    bridge = AudioLabBridge(job_service=svc)
    result = bridge.startAnalysis("/tracks/foo.flac")

    assert result.get("ok") is True, (
        f"Expected ok=True for queued job, got {result}"
    )
    # The job should be QUEUED (capacity), not FAILED (handler unavailable).
    assert result.get("status") in ("queued",), (
        f"Expected queued, got {result.get('status')}"
    )
    assert result.get("error_code") != "HANDLER_UNAVAILABLE", (
        "Capacity exhaustion must NOT be reported as HANDLER_UNAVAILABLE"
    )
    job = svc.get_job(result["job_id"])
    assert job is not None
    assert job.state == JobState.QUEUED
