"""Single durable job authority: JobBridge is a thin view, DurableJobService
is the only job system in production composition (ADR-004, audit §8)."""
from __future__ import annotations

import re
from pathlib import Path

from tests.architecture._helpers import composition_source

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _source(relative: str) -> str:
    return (PROJECT_ROOT / relative).read_text(encoding="utf-8")


def test_job_bridge_has_no_parallel_registry() -> None:
    """JobBridge must not keep its own job registry or counters."""
    source = _source("ui_qml_bridge/job_bridge.py")
    assert "self._jobs = [" not in source, (
        "JobBridge must not maintain an in-memory job registry"
    )
    assert "self._counter" not in source, (
        "JobBridge must not maintain its own job id counter"
    )
    assert "run_task" not in source, (
        "JobBridge must not schedule tasks itself; it delegates to job_service"
    )


def test_composition_creates_single_durable_job_service() -> None:
    """Production composition instantiates exactly one DurableJobService and
    never a JobManager."""
    source = composition_source()
    count = len(re.findall(r"\bJobService\(", source))
    assert count == 1, (
        f"Expected exactly one DurableJobService instantiation in composition, "
        f"found {count}"
    )
    assert "JobManager(" not in source, (
        "JobManager must never be instantiated in composition builders"
    )


def test_job_service_registered_with_worker_manager() -> None:
    """The container-registered job service must have the real WorkerManager
    injected (no synchronous fallback in the production path)."""
    source = composition_source()
    assert re.search(r"\bJobService\(\s*worker_manager\s*=", source), (
        "JobService must be constructed with worker_manager= in composition"
    )
    assert "register_production_job_handlers" in source, (
        "Production job handlers must be registered in composition"
    )


def test_job_bridge_requires_job_service() -> None:
    """JobBridge degrades explicitly without job_service; it never falls back
    to synchronous execution or a parallel registry."""
    source = _source("ui_qml_bridge/job_bridge.py")
    assert "INFRASTRUCTURE_UNAVAILABLE" in source, (
        "JobBridge must expose an explicit degraded-mode error"
    )
    assert "job_service" in source
