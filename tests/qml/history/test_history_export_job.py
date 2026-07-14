"""Test HistoryQueryService export as JobService, cancelExport cancels real job."""
import pytest
import sqlite3
import time
import json

from core.history_query_service import HistoryQueryService
from core.job_service import JobService, JobStatus
from ui_qml_bridge.history_bridge import HistoryBridge


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT NOT NULL,
            played_at REAL NOT NULL,
            device TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            deleted_at TEXT, albumartist TEXT
        )
    """)
    now = time.time()
    for i in range(10):
        conn.execute(
            "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
            (str(i + 1), now - i * 3600, "local")
        )
    for i in range(10):
        conn.execute(
            "INSERT INTO media_items (id, filepath, title, artist, album, album_key, duration) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, f"/path/track_{i}.flac", f"Title {i}", f"Artist {i}", f"Album {i}", f"key_{i}", 200 + i)
        )
    conn.commit()
    return conn


class DbWrap:
    def __init__(self, conn):
        self.conn = conn


@pytest.fixture
def svc(db_conn):
    return HistoryQueryService(db=DbWrap(db_conn))


@pytest.fixture
def job_service():
    return JobService()


@pytest.fixture
def bridge_with_jobs(svc, job_service):
    b = HistoryBridge(history_query_service=svc)
    b._job_service = job_service
    return b


def test_export_json_creates_file(svc, tmp_path):
    out = tmp_path / "export.json"
    result = svc.export_history(str(out), fmt="json")
    assert result["ok"]
    assert result["count"] == 10
    assert out.exists()
    data = json.loads(out.read_text())
    assert len(data) == 10


def test_export_csv_creates_file(svc, tmp_path):
    out = tmp_path / "export.csv"
    result = svc.export_history(str(out), fmt="csv")
    assert result["ok"]
    assert result["count"] == 10
    assert out.exists()


def test_export_empty_path(svc):
    result = svc.export_history("")
    assert not result["ok"]
    assert result["error"] == "EMPTY_PATH"


def test_export_no_db():
    svc = HistoryQueryService(db=None)
    result = svc.export_history("/tmp/test_export.json")
    assert not result["ok"]
    assert result["error"] == "NO_DB"


def test_cancel_export_removes_file(svc, tmp_path):
    out = tmp_path / "to_cancel.json"
    svc.export_history(str(out))
    assert out.exists()
    bridge = HistoryBridge(history_query_service=svc)
    result = bridge.cancelExport("dummy", str(out))
    assert result["ok"]
    assert result["cancelled"] is True
    assert not out.exists()


def test_cancel_export_no_file_still_ok(svc):
    bridge = HistoryBridge(history_query_service=svc)
    result = bridge.cancelExport("dummy", "/tmp/nonexistent_export.json")
    assert result["ok"]


def test_cancel_export_empty_filepath_still_ok(svc):
    bridge = HistoryBridge(history_query_service=svc)
    result = bridge.cancelExport("job_1")
    assert result["ok"]


def test_job_service_tracks_export_job(svc, job_service):
    job = job_service.create("export_history", meta={"path": "/tmp/test.json"})
    assert job.kind == "export_history"
    assert job.status == JobStatus.QUEUED
    job_service.update(job.job_id, status=JobStatus.RUNNING)
    assert job_service.get(job.job_id).status == JobStatus.RUNNING


def test_job_service_cancel_export(svc, job_service):
    job = job_service.create("export_history", meta={"path": "/tmp/test.json"})
    job_service.update(job.job_id, status=JobStatus.RUNNING)
    result = job_service.cancel(job.job_id)
    assert result
    assert job_service.get(job.job_id).status == JobStatus.CANCELLED


def test_cancel_export_via_bridge_uses_job_service(svc, job_service, tmp_path):
    bridge = HistoryBridge(history_query_service=svc)
    bridge._job_service = job_service
    out = tmp_path / "bridge_export.json"
    svc.export_history(str(out), fmt="json")
    job = job_service.create("export_history", meta={"path": str(out)})
    result = bridge.cancelExport(job.job_id, str(out))
    assert result["ok"]
    assert not out.exists()
