"""history_export durable job: filters payload, atomic file write, manifest,
cancellation without partial artifacts."""
from __future__ import annotations

import json
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
def db_with_history(tmp_path):
    from library.library_db import LibraryDB

    db = LibraryDB(str(tmp_path / "library.db"))
    now = time.time()
    for idx, days_ago in enumerate((1, 5, 30)):
        db.conn.execute(
            "INSERT INTO play_history (track_id, device, played_at) VALUES (?, ?, ?)",
            (f"/music/track{idx}.flac", "desktop", now - days_ago * 86400),
        )
    db.conn.commit()
    return db


@pytest.fixture
def container(db_with_history):
    from core.service_container import ServiceContainer

    c = ServiceContainer()
    c.register("database", db_with_history)
    return c


@pytest.fixture
def job_service(tmp_path, container):
    from core.composition.jobs import register_production_job_handlers
    from core.jobs.job_service import DurableJobService
    from core.worker_manager import WorkerManager

    wm = WorkerManager()
    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"), worker_manager=wm)
    register_production_job_handlers(svc, container)
    yield svc
    wm.shutdown()


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


def test_history_export_json_writes_manifest_with_filters(app, job_service,
                                                         tmp_path):
    output = str(tmp_path / "history.json")
    job_id = job_service.create_job(
        "history_export", owner="test",
        payload={"filepath": output, "fmt": "json",
                 "filters": {"date_from": "2020-01-01"}},
    )
    assert job_service.start_job(job_id) is True

    state = _wait_terminal(app, job_service, job_id)
    from core.jobs.job_service import JobState
    assert state == JobState.SUCCEEDED, (
        f"export job failed: {job_service.get_job(job_id).message}"
    )

    assert os.path.exists(output), "export file must exist"
    with open(output, encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["schema_version"] == 1
    assert manifest["generated_at"]
    assert manifest["filters"] == {"date_from": "2020-01-01"}
    assert manifest["row_count"] == 3
    assert len(manifest["rows"]) == 3

    persisted = job_service.get_job(job_id)
    assert persisted.payload["filepath"] == output
    assert persisted.result["count"] == 3


def test_history_export_csv_writes_rows_and_sidecar_manifest(app, job_service,
                                                             tmp_path):
    output = str(tmp_path / "history.csv")
    job_id = job_service.create_job(
        "history_export", owner="test",
        payload={"filepath": output, "fmt": "csv",
                 "filters": {"date_from": "2020-01-01"}},
    )
    assert job_service.start_job(job_id) is True

    from core.jobs.job_service import JobState
    assert _wait_terminal(app, job_service, job_id) == JobState.SUCCEEDED

    assert os.path.exists(output)
    with open(output, encoding="utf-8") as f:
        lines = [line for line in f.read().splitlines() if line]
    assert lines[0].startswith("track_id,")
    assert len(lines) == 4  # header + 3 rows

    manifest_path = output + ".manifest.json"
    assert os.path.exists(manifest_path)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["schema_version"] == 1
    assert manifest["row_count"] == 3
    assert manifest["filters"] == {"date_from": "2020-01-01"}


def test_history_export_date_range_filters_rows(app, job_service, tmp_path):
    output = str(tmp_path / "recent.json")
    job_id = job_service.create_job(
        "history_export", owner="test",
        payload={"filepath": output, "fmt": "json",
                 "filters": {"date_from": "2026-07-20",
                             "date_to": "2026-08-10"}},
    )
    assert job_service.start_job(job_id) is True

    from core.jobs.job_service import JobState
    assert _wait_terminal(app, job_service, job_id) == JobState.SUCCEEDED

    with open(output, encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["row_count"] == 2  # 1 and 5 days ago; 30 days ago excluded


def test_cancelled_queued_export_leaves_no_partial_file(app, job_service,
                                                        tmp_path):
    output = str(tmp_path / "never.json")
    job_id = job_service.create_job(
        "history_export", owner="test",
        payload={"filepath": output, "fmt": "json",
                 "filters": {"date_from": "2020-01-01"}},
    )
    assert job_service.cancel_job(job_id) is True

    from core.jobs.job_service import JobState
    assert job_service.get_job(job_id).state == JobState.CANCELLED
    assert not os.path.exists(output), (
        "cancelled export must not create a partial file"
    )
