"""AudioLabJobAdapter delegates to the durable job service (ADR-004).

When a job_service is provided (production path), submit_* create durable
jobs on it instead of keeping an in-memory registry.
"""
from __future__ import annotations

import pytest

from core.audio_lab.audio_lab_contracts import AudioLabOperation
from core.jobs.job_service import DurableJobService

pytestmark = pytest.mark.isolation


class _FakeContainer:
    def get(self, _name):
        return None


class _SlowHandler:
    def __init__(self):
        self.cancelled = False

    def __call__(self, job, ctx):
        return {"ok": True, "probed": ctx.task_id}


def test_adapter_submits_durable_jobs_when_job_service_provided() -> None:
    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter

    svc = DurableJobService(db_path=":memory:")
    svc.register_handler(AudioLabOperation.PROBE.value, _SlowHandler())
    adapter = AudioLabJobAdapter(job_service=svc)
    job_id = adapter.submit_probe("/music/test.flac")

    assert job_id
    job = svc.get_job(job_id)
    assert job is not None, "submit_probe must create a durable job"
    assert job.type == AudioLabOperation.PROBE.value
    assert job.owner == "audio_lab"
    payload = job.payload.get("request") or {}
    assert payload.get("filepath") == "/music/test.flac"

    listed = svc.list_jobs(owner="audio_lab")
    assert any(d["id"] == job_id for d in listed), (
        "durable job must be visible in the job service"
    )

    public = adapter.get(job_id)
    assert public is not None
    assert public["id"] == job_id
    assert public["request"]["filepath"] == "/music/test.flac"

    cancelled = adapter.cancel(job_id)
    assert isinstance(cancelled, bool)


def test_adapter_durable_path_is_not_the_in_memory_registry() -> None:
    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter

    svc = DurableJobService(db_path=":memory:")
    svc.register_handler(AudioLabOperation.ANALYSIS.value, _SlowHandler())
    adapter = AudioLabJobAdapter(job_service=svc)
    job_id = adapter.submit_analysis("/music/test.flac")

    assert job_id not in adapter._jobs, (
        "durable submissions must not land in the in-memory registry"
    )
    assert adapter.list() and adapter.get(job_id) is not None


def test_adapter_without_job_service_rejects_infrastructure_unavailable() -> None:
    from unittest.mock import MagicMock

    from core.audio_lab.audio_lab_contracts import AudioLabErrorCode
    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter

    probe = MagicMock()
    adapter = AudioLabJobAdapter(probe=probe)
    job = adapter.get(adapter.submit_probe("/music/test.flac"))
    assert job is not None
    assert job["status"] == "failed"
    assert job["error_code"] == AudioLabErrorCode.INFRASTRUCTURE_UNAVAILABLE.value
    probe.probe.assert_not_called()


def test_analysis_handler_registered_before_resume_pending_jobs() -> None:
    """Analysis handler must be in _handlers before resume_pending_jobs runs."""
    from unittest.mock import MagicMock

    from core.composition.jobs import register_production_job_handlers

    svc = DurableJobService(db_path=":memory:")

    job_id = svc.create_job(
        "analysis", owner="audio_lab",
        payload={"request": {"filepath": "/tracks/foo.flac"}},
    )

    analysis_service = MagicMock()
    analysis_service.analysis = MagicMock()
    analysis_service.analysis.analyze_file.return_value = {"status": "ok"}

    class _TestContainer:
        def get(self, name):
            if name == "audio_lab_service":
                return analysis_service
            return None

    container = _TestContainer()

    register_production_job_handlers(svc, container)

    assert "analysis" in svc._handlers, (
        "analysis handler must be registered BEFORE resume_pending_jobs"
    )

    stats = svc.resume_pending_jobs()
    assert stats["handler_unavailable"] == 0, (
        f"QUEUED analysis job must NOT fail with HANDLER_UNAVAILABLE: {stats}"
    )
    assert stats["resumed"] >= 0

    job = svc.get_job(job_id)
    assert job is not None
    assert job.state.value != "FAILED", (
        "QUEUED analysis job must NOT be FAILED when handler is registered"
    )


def test_analysis_never_enters_bridge_local_active_jobs(tmp_path):
    """startAnalysis creates a durable job, never pushes into _active_jobs."""
    from core.jobs.job_service import DurableJobService
    from core.jobs.handlers import make_analysis_handler
    from unittest.mock import MagicMock

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    svc = DurableJobService(db_path=str(tmp_path / "no_local.db"))
    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed"}
    svc.register_handler("analysis", make_analysis_handler(port))

    bridge = AudioLabBridge(job_service=svc)

    # Snapshot local registry before.
    before_ids = set(bridge._active_jobs.keys())

    bridge.startAnalysis("/tracks/foo.flac")

    # No new entries in the local registry.
    after_ids = set(bridge._active_jobs.keys())
    assert after_ids == before_ids, (
        "Analysis must NOT enter bridge._active_jobs — durable path only"
    )


def test_analysis_never_creates_local_thread(tmp_path):
    """startAnalysis must NOT call _start_background_job or threading.Thread."""
    from core.jobs.job_service import DurableJobService
    from core.jobs.handlers import make_analysis_handler
    from unittest.mock import MagicMock, patch

    from ui_qml_bridge.audio_lab_bridge import AudioLabBridge

    svc = DurableJobService(db_path=str(tmp_path / "no_thread.db"))
    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed"}
    svc.register_handler("analysis", make_analysis_handler(port))

    bridge = AudioLabBridge(job_service=svc)

    with patch("threading.Thread") as mock_thread:
        bridge.startAnalysis("/tracks/foo.flac")
        mock_thread.assert_not_called()
