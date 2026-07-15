"""Test JobService canónico — core/job_service.py re-exports DurableJobService."""
from unittest.mock import MagicMock, patch

from core.job_service import JobService, DurableJobService


# ── Re-export integrity ──


def test_job_service_is_durable_job_service():
    assert JobService is DurableJobService


def test_can_import_from_core_job_service():
    from core.job_service import JobService as JS
    assert JS is DurableJobService


def test_can_import_from_core_jobs_job_service():
    from core.jobs.job_service import DurableJobService
    assert DurableJobService is JobService


# ── DurableJobService 10 states ──


def test_has_10_job_states():
    from core.jobs.job_service import JobState
    expected = {
        "QUEUED", "RUNNING", "PAUSING", "PAUSED",
        "CANCELLING", "CANCELLED",
        "SUCCEEDED", "PARTIAL_SUCCESS", "FAILED", "INTERRUPTED",
    }
    assert set(s.value for s in JobState) == expected


# ── Constructor ──


def test_constructor_defaults():
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService()
    assert svc._jobs == {}
    assert svc._handlers == {}


def test_constructor_with_db_path():
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService(db_path="/tmp/test_jobs.db")
    assert svc._db_path == "/tmp/test_jobs.db"


# ── Job creation ──


def test_create_job_returns_string_id():
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService()
    job_id = svc.create_job("test_type")
    assert isinstance(job_id, str)
    assert len(job_id) > 0


def test_create_job_stores_job():
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService()
    job_id = svc.create_job("test_type", owner="tester", payload={"key": "val"})
    job = svc.get_job(job_id)
    assert job is not None
    assert job.type == "test_type"
    assert job.owner == "tester"
    assert job.payload == {"key": "val"}


# ── Handler registration ──


def test_register_handler():
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService()
    handler = MagicMock()
    svc.register_handler("scan", handler)
    assert "scan" in svc._handlers


# ── Process ID ──


def test_job_has_process_id_field():
    from core.jobs.job_service import DurableJob
    job = DurableJob(processId="proc_123")
    assert job.processId == "proc_123"


# ── Persistence ──


def test_persist_job_creates_table(tmp_path):
    db_path = str(tmp_path / "test_jobs.db")
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService(db_path=db_path)
    job_id = svc.create_job("scan")
    job = svc.get_job(job_id)
    assert job is not None


# ── QueueChanged signal ──


def test_create_job_emits_queue_changed():
    with patch.object(DurableJobService, '_restore_running_jobs'):
        svc = DurableJobService()
    received = []
    svc.queueChanged.connect(received.append)
    svc.create_job("scan")
    assert len(received) >= 1


# ── Module can be imported cleanly ──


def test_module_importable():
    import core.jobs.job_service
    import core.job_service
    assert core.job_service.JobService is core.jobs.job_service.DurableJobService
