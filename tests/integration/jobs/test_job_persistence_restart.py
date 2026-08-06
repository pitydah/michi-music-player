"""Restart recovery of DurableJobService (audit §7 / bug 19).

On a fresh service over the same DB: RUNNING -> INTERRUPTED and QUEUED jobs
are re-enqueued and visible in list_jobs.
"""
from __future__ import annotations

import json
import os
import sqlite3

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.isolation

_JOB_COLUMNS = (
    "id, type, owner, state, created_at, started_at, finished_at, "
    "progress, current, total, message, warnings, errors, "
    "cancellable, pausable, retryable, payload, result, process_id"
)


def _insert_row(db_path: str, job_id: str, state: str, payload: dict):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS durable_jobs (
            id TEXT PRIMARY KEY, type TEXT, owner TEXT, state TEXT,
            created_at TEXT, started_at TEXT, finished_at TEXT,
            progress REAL, current INTEGER, total INTEGER,
            message TEXT, warnings TEXT, errors TEXT,
            cancellable INTEGER, pausable INTEGER, retryable INTEGER,
            payload TEXT, result TEXT, process_id TEXT
        )"""
    )
    conn.execute(
        f"INSERT OR REPLACE INTO durable_jobs ({_JOB_COLUMNS}) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            job_id, "wait_type", "test", state,
            "2026-08-01T10:00:00", "2026-08-01T10:00:05", "",
            0.5, 0, 10, "trabajando", "[]", "[]",
            1, 1, 1, json.dumps(payload), "{}", "",
        ),
    )
    conn.commit()
    conn.close()


def test_restart_recovery_interrupts_running_and_reloads_queued(tmp_path):
    """A crashed process leaves RUNNING rows; restart must flip them to
    INTERRUPTED and reload persisted QUEUED jobs into the live registry."""
    from core.jobs.job_service import DurableJobService, JobState

    db_path = str(tmp_path / "jobs.db")

    # Phase 1: a real service persists a QUEUED job (create_job -> DB row).
    svc = DurableJobService(db_path=db_path)
    queued_id = svc.create_job("wait_type", owner="test", payload={"k": "v"})
    assert svc.get_job(queued_id).state == JobState.QUEUED
    del svc

    # Crash artifact: the RUNNING row the process persisted at start_job time
    # before dying mid-execution (the handler never got to finalize it).
    running_id = "crash-run-0001"
    _insert_row(db_path, running_id, JobState.RUNNING.value, {"folder": "/x"})

    # Phase 2: restart on the same DB.
    svc2 = DurableJobService(db_path=db_path)

    interrupted = svc2.get_job(running_id)
    assert interrupted is not None, "RUNNING job must be recovered"
    assert interrupted.state == JobState.INTERRUPTED, (
        f"RUNNING must flip to INTERRUPTED, got {interrupted.state}"
    )
    assert interrupted.message == "Interrumpido por reinicio"

    queued = svc2.get_job(queued_id)
    assert queued is not None, "QUEUED job must be reloaded"
    assert queued.state == JobState.QUEUED, (
        f"QUEUED must stay QUEUED, got {queued.state}"
    )
    assert queued.payload.get("k") == "v"

    listed = {d["id"] for d in svc2.list_jobs()}
    assert queued_id in listed, "reloaded QUEUED job must be in list_jobs"
    assert running_id in listed

    # Recovered jobs are retryable: retry re-queues with the ORIGINAL payload
    # and starts immediately (Fase Jobs: unified retry semantics). The
    # handler runs inline (no WorkerManager in this test) and completes.
    def ok_handler(job, ctx):
        return {"ok": True, "recovered": True}

    svc2.register_handler("wait_type", ok_handler)

    assert svc2.retry_job(running_id) is True
    retried = svc2.get_job(running_id)
    assert retried.state == JobState.SUCCEEDED, (
        f"retry must start the job, got {retried.state}"
    )
    assert retried.payload.get("folder") == "/x", (
        "retry must preserve the original payload"
    )
    assert retried.result.get("recovered") is True

    assert svc2.retry_job(queued_id) is False, (
        "a job already QUEUED has nothing to retry"
    )


def test_restart_recovery_only_restores_active_states(tmp_path):
    """Terminal rows (SUCCEEDED) stay terminal after restart and are not
    re-enqueued into the live registry."""
    from core.jobs.job_service import DurableJobService, JobState

    db_path = str(tmp_path / "jobs.db")
    _insert_row(db_path, "done-0001", JobState.SUCCEEDED.value, {})

    svc = DurableJobService(db_path=db_path)
    assert svc.get_job("done-0001") is None, (
        "terminal jobs are not loaded into the live registry"
    )
