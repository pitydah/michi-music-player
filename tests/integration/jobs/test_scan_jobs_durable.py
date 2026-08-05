"""Durable jobs integration: async execution, persistence, restart recovery."""
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
def real_db(tmp_path):
    from library.library_db import LibraryDB
    return LibraryDB(str(tmp_path / "library.db"))


def _wait_terminal(app, svc, job_id, timeout=20.0) -> str:
    from core.jobs.job_service import JobState
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        state = svc.get_job(job_id).state
        if state in (JobState.SUCCEEDED, JobState.FAILED,
                     JobState.PARTIAL_SUCCESS, JobState.CANCELLED):
            return state
        time.sleep(0.02)
    return svc.get_job(job_id).state.value


def test_scan_job_runs_async_and_persists_payload(app, real_db, tmp_path):
    """A library_scan job runs off-thread, reaches a terminal state and keeps
    its payload in the durable store (audit §7: start_job must not block)."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.service_container import ServiceContainer
    from core.worker_manager import WorkerManager

    folder = tmp_path / "empty_library"
    folder.mkdir()

    container = ServiceContainer()
    container.register("database", real_db)

    wm = WorkerManager()
    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"),
                            worker_manager=wm)
    try:
        from core.jobs.handlers import register_production_job_handlers
        register_production_job_handlers(svc, container)

        job_id = svc.create_job(
            "library_scan", owner="test",
            payload={"folder_path": str(folder)},
        )
        assert svc.start_job(job_id) is True

        persisted = svc.get_job(job_id)
        assert persisted is not None
        assert persisted.payload["folder_path"] == str(folder)

        state = _wait_terminal(app, svc, job_id)
        assert state in (JobState.SUCCEEDED, JobState.PARTIAL_SUCCESS,
                         JobState.FAILED), f"job stuck in {state}"

        jobs = svc.list_jobs(job_type="library_scan")
        listed = next((d for d in jobs if d["id"] == job_id), None)
        assert listed is not None, "finished job must be visible in list_jobs"
        assert listed["payload"]["folder_path"] == str(folder)
        assert listed["state"] == state
    finally:
        wm.shutdown()


def test_metadata_and_doctor_scan_complete_with_real_db(app, real_db, tmp_path):
    """metadata_scan and doctor_scan execute to a terminal state on a real DB."""
    from core.jobs.job_service import DurableJobService, JobState
    from core.service_container import ServiceContainer
    from core.worker_manager import WorkerManager

    container = ServiceContainer()
    container.register("database", real_db)

    wm = WorkerManager()
    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"),
                            worker_manager=wm)
    try:
        from core.jobs.handlers import register_production_job_handlers
        register_production_job_handlers(svc, container)

        for job_type in ("metadata_scan", "doctor_scan"):
            job_id = svc.create_job(job_type, owner="test")
            assert svc.start_job(job_id) is True
            state = _wait_terminal(app, svc, job_id)
            assert state in (JobState.SUCCEEDED, JobState.FAILED,
                             JobState.PARTIAL_SUCCESS), (
                f"{job_type} stuck in {state}"
            )
    finally:
        wm.shutdown()


def test_cancelled_queued_job_reaches_cancelled(app, tmp_path):
    """Cancelling a queued job lands it in CANCELLED without execution."""
    from core.jobs.job_service import DurableJobService, JobState

    wm = None
    try:
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        svc = DurableJobService(db_path=str(tmp_path / "jobs.db"),
                                worker_manager=wm)
        job_id = svc.create_job("doctor_scan", owner="test", payload={})
        assert svc.cancel_job(job_id) is True
        assert svc.get_job(job_id).state == JobState.CANCELLED
    finally:
        if wm is not None:
            wm.shutdown()
