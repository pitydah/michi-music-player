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


# ── Global Search (Slice 6) ────────────────────────────────────────────────


def test_global_search_service_has_no_qimer_singleshot() -> None:
    """Global search must never be pseudo-async on the QML thread."""
    source = (PROJECT_ROOT / "core" / "global_search_service.py").read_text(
        encoding="utf-8"
    )
    assert "QTimer" not in source, (
        "GlobalSearchService must not use QTimer (pseudo-async on UI thread)"
    )
    assert "singleShot" not in source


def test_global_search_bridge_has_no_sync_execution_fallback() -> None:
    """The bridge must never run a search inline when the executor is absent."""
    source = (PROJECT_ROOT / "ui_qml_bridge" / "global_search_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "QTimer" not in source
    assert "singleShot" not in source
    assert "INFRASTRUCTURE_UNAVAILABLE" in source, (
        "Bridge must report INFRASTRUCTURE_UNAVAILABLE instead of executing inline"
    )
    assert "callable_fn" in source, (
        "Bridge must submit work to the QueryExecutor"
    )


def test_global_search_service_never_executes_inline_when_executor_missing() -> None:
    """search_async without an operative executor returns
    INFRASTRUCTURE_UNAVAILABLE and never runs the query."""
    from core.global_search_service import GlobalSearchService
    from core.search.models import (
        INFRASTRUCTURE_UNAVAILABLE,
        SearchDomain,
        SearchRequest,
    )

    calls = []

    def exploding_provider(request, limit):
        calls.append(request)
        raise AssertionError("provider must never run without an executor")

    from core.search.providers import SearchProviderRegistry
    registry = SearchProviderRegistry()
    registry.register(SearchDomain.TRACK, exploding_provider)

    svc = GlobalSearchService(
        db_path="", provider_registry=registry, query_executor=None
    )
    box = []
    svc.search_async(
        SearchRequest(query="x", domains=frozenset({SearchDomain.TRACK}),
                      request_id="1"),
        on_result=box.append,
    )
    assert calls == [], "sync fallback executed the query on the caller thread"
    assert len(box) == 1
    assert box[0].error == INFRASTRUCTURE_UNAVAILABLE


def test_global_search_service_checks_executor_operative_before_submit() -> None:
    """A QueryExecutor without a WorkerManager (sync fallback) is rejected."""
    from core.global_search_service import GlobalSearchService
    from core.query_executor import QueryExecutor
    from core.search.models import (
        INFRASTRUCTURE_UNAVAILABLE,
        SearchDomain,
        SearchRequest,
    )

    qe = QueryExecutor(worker_manager=None)  # sync-fallback executor
    svc = GlobalSearchService(db_path="", query_executor=qe)
    box = []
    svc.search_async(
        SearchRequest(query="x", domains=frozenset({SearchDomain.TRACK}),
                      request_id="1"),
        on_result=box.append,
    )
    assert len(box) == 1
    assert box[0].error == INFRASTRUCTURE_UNAVAILABLE
