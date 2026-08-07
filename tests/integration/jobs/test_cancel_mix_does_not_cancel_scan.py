"""Fase Jobs: cancelling the Mix generation must cancel ONLY the mix job id —
a concurrent library_scan RUNNING job is untouched. Architecture: no
`cancel_all(` in mix_bridge/metadata_bridge/notification_action_service."""
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


def test_mix_cancel_only_cancels_mix_job_scan_keeps_running(app, tmp_path):
    from core.jobs.job_service import DurableJobService, JobState
    from core.worker_manager import WorkerManager
    from ui_qml_bridge.mix_bridge import MixBridge

    db_path = str(tmp_path / "jobs.db")
    release = threading.Event()

    wm = WorkerManager()
    try:
        svc = DurableJobService(db_path=db_path, worker_manager=wm)
        svc.register_handler("library_scan", _blocking_handler(release))
        svc.register_handler("mix_generation", _blocking_handler(release))

        # A library scan owned by another domain is RUNNING.
        scan_id = svc.create_job("library_scan", owner="job_bridge",
                                 payload={"folder_path": "/music/a"})
        assert svc.start_job(scan_id) is True

        # Mix generates its own durable job (current job id on the bridge).
        mix_id = svc.create_job("mix_generation", owner="mix_bridge",
                                payload={"mix_id": "daily_mix"})
        assert svc.start_job(mix_id) is True
        assert svc.get_job(mix_id).state == JobState.RUNNING

        bridge = MixBridge(mix_service=None, job_service=svc)
        bridge._job_id = mix_id  # the bridge tracks its own current job id

        result = bridge.cancelGeneration()
        assert result["ok"] is True
        assert "cancelled" in result  # pre-increment generation (bridge contract)

        # The mix job is cancelled...
        mix_state = _wait_state(
            app, svc, mix_id, (JobState.CANCELLED,), timeout=10.0)
        assert mix_state == JobState.CANCELLED.value

        # ...and the scan job keeps RUNNING: cancel_all is gone.
        assert svc.get_job(scan_id).state == JobState.RUNNING

        release.set()
        scan_state = _wait_state(
            app, svc, scan_id,
            (JobState.SUCCEEDED, JobState.FAILED,
             JobState.PARTIAL_SUCCESS), timeout=10.0)
        assert scan_state == JobState.SUCCEEDED.value
    finally:
        release.set()
        wm.shutdown()


def test_no_cancel_all_in_job_consumers_productive_code() -> None:
    """Architecture: no `cancel_all(` in mix_bridge, metadata_bridge or
    notification_action_service (scoped cancellation only)."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent.parent
    files = (
        "ui_qml_bridge/mix_bridge.py",
        "ui_qml_bridge/metadata_bridge.py",
        "core/notification_action_service.py",
    )
    for relative in files:
        source = (root / relative).read_text(encoding="utf-8")
        assert "cancel_all(" not in source, (
            f"{relative} must never call cancel_all()"
        )
