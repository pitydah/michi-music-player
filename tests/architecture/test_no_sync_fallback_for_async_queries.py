"""No synchronous fallback in the production job path (audit §7: start_job
runs handlers inline on the caller thread; JobBridge runs jobs inline)."""
from __future__ import annotations

import re
from pathlib import Path

from tests.architecture._helpers import composition_source

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_container_job_service_has_worker_manager() -> None:
    """The container-registered DurableJobService executes async via WM."""
    source = composition_source()
    assert re.search(r"\bJobService\(\s*worker_manager\s*=\s*wm\)", source), (
        "JobService must be constructed with the shared WorkerManager"
    )


def test_job_bridge_never_executes_synchronously() -> None:
    """JobBridge must not run callables inline anywhere in its runJob path."""
    source = (PROJECT_ROOT / "ui_qml_bridge" / "job_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "run_task" not in source, (
        "JobBridge schedules nothing; DurableJobService owns execution"
    )
    assert "callable_fn()" not in source, (
        "JobBridge must never execute job callables inline"
    )
    assert "INFRASTRUCTURE_UNAVAILABLE" in source


def test_durable_service_submits_async_when_wm_present() -> None:
    """DurableJobService routes execution through WorkerManager when injected."""
    source = (PROJECT_ROOT / "core" / "jobs" / "job_service.py").read_text(
        encoding="utf-8"
    )
    assert "run_task" in source, (
        "DurableJobService must submit handlers via WorkerManager"
    )
    assert "pass_context=True" in source, (
        "Handlers must receive a TaskContext for cooperative cancellation"
    )
    assert "_submit_async" in source
