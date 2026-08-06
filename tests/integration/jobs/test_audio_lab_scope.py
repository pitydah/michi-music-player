"""Fase Jobs: Audio Lab cancellation is owner/job-id scoped — cancelling an
audio lab job never touches device sync jobs (or any other domain's jobs)."""
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


def _blocking_handler(event: threading.Event):
    def handler(job, ctx):
        while not event.is_set():
            ctx.token.raise_if_cancelled()
            time.sleep(0.01)
        return {"ok": True, "finished": True}

    return handler


def _wait_state(app, svc, job_id, target_states, timeout=20.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        job = svc.get_job(job_id)
        if job is None:
            return "GONE"
        if job.state in target_states:
            return job.state.value
        time.sleep(0.02)
    return svc.get_job(job_id).state.value


def test_audio_lab_cancel_does_not_cancel_device_sync(app, tmp_path):
    from core.audio_lab.audio_lab_contracts import AudioLabOperation
    from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
    from core.jobs.job_service import DurableJobService, JobState
    from core.worker_manager import WorkerManager

    db_path = str(tmp_path / "jobs.db")
    release = threading.Event()

    wm = WorkerManager()
    try:
        svc = DurableJobService(db_path=db_path, worker_manager=wm)
        svc.register_handler("device_sync", _blocking_handler(release))
        svc.register_handler(AudioLabOperation.PROBE.value,
                             _blocking_handler(release))

        # A device sync job from another domain is RUNNING.
        sync_id = svc.create_job("device_sync", owner="device_sync",
                                 payload={"device_id": "s9"})
        assert svc.start_job(sync_id) is True

        # Audio Lab submits its own durable job.
        adapter = AudioLabJobAdapter(job_service=svc)
        probe_id = adapter.submit_probe("/music/test.flac")
        assert svc.get_job(probe_id).state == JobState.RUNNING

        # Cancelling the audio lab job (by its own id) leaves device sync
        # untouched.
        assert adapter.cancel(probe_id) is True
        probe_state = _wait_state(
            app, svc, probe_id, (JobState.CANCELLED,), timeout=10.0)
        assert probe_state == JobState.CANCELLED.value
        assert svc.get_job(sync_id).state == JobState.RUNNING

        release.set()
        sync_state = _wait_state(
            app, svc, sync_id,
            (JobState.SUCCEEDED, JobState.FAILED,
             JobState.PARTIAL_SUCCESS), timeout=10.0)
        assert sync_state == JobState.SUCCEEDED.value
    finally:
        release.set()
        wm.shutdown()
