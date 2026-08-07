"""Fase Jobs: a QUEUED job whose kind has NO registered handler must be
marked FAILED with a persisted HANDLER_UNAVAILABLE error — it never lingers
silently and the failure survives further restarts."""
from __future__ import annotations

import os
import sqlite3

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.isolation


def _read_row(db_path: str, job_id: str):
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT state, message, errors FROM durable_jobs WHERE id=?",
        (job_id,),
    ).fetchone()
    conn.close()
    return row


def test_handlerless_queued_job_fails_handler_unavailable_persisted(tmp_path):
    from core.jobs.job_service import DurableJobService, JobState

    db_path = str(tmp_path / "jobs.db")

    # Previous process left a QUEUED job for a kind nobody handles.
    svc_a = DurableJobService(db_path=db_path)
    ghost_id = svc_a.create_job(
        "ghost_type", owner="job_bridge", payload={"folder_path": "/x"},
    )
    del svc_a

    # Restart: handlers registered for REAL kinds only; the boot resume must
    # fail the handler-less job explicitly.
    svc_b = DurableJobService(db_path=db_path)

    def ok_handler(job, ctx):
        return {"ok": True}

    svc_b.register_handler("resumable_scan", ok_handler)
    stats = svc_b.resume_pending_jobs()
    assert stats["queued"] == 1
    assert stats["handler_unavailable"] == 1
    assert stats["resumed"] == 0

    ghost = svc_b.get_job(ghost_id)
    assert ghost is not None
    assert ghost.state == JobState.FAILED
    assert ghost.errors == ["HANDLER_UNAVAILABLE: ghost_type"]
    assert "HANDLER_UNAVAILABLE" in ghost.message
    assert ghost.finishedAt, "failure must record a finished timestamp"

    # Persisted: a fresh service over the same DB reads the FAILED row.
    row = _read_row(db_path, ghost_id)
    assert row is not None
    assert row[0] == JobState.FAILED.value
    assert "HANDLER_UNAVAILABLE" in row[1]
    assert "HANDLER_UNAVAILABLE" in row[2]

    # And the failure is NOT re-enqueued on a second restart (terminal rows
    # are never loaded into the live registry).
    svc_c = DurableJobService(db_path=db_path)
    assert svc_c.get_job(ghost_id) is None
    stats = svc_c.resume_pending_jobs()
    assert stats["queued"] == 0 and stats["handler_unavailable"] == 0
