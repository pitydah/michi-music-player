"""Vertical slice (Slice 6): cancellation and staleness of async global search.

Real QueryExecutor + WorkerManager: a slow provider (threading.Event barrier)
makes the lifecycle observable. Superseding a request finalizes the previous
one as STALE; cancel(request_id) mid-run fires on_cancelled; stale results are
never delivered; a shutdown WorkerManager reports INFRASTRUCTURE_UNAVAILABLE.
"""
from __future__ import annotations

import sqlite3
import threading
import time

import pytest
from PySide6.QtCore import QCoreApplication

from core.global_search_service import GlobalSearchService
from core.query_executor import QueryExecutor
from core.search.models import (
    INFRASTRUCTURE_UNAVAILABLE,
    SearchDomain,
    SearchRequest,
    SearchResponse,
)
from core.search.providers import (
    SearchProviderRegistry,
    TrackSearchRepository,
)
from core.worker_manager import WorkerManager


class SlowProvider:
    """Blocks until released; used to make cancellation observable."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.started = threading.Event()
        self.runs = 0

    def __call__(self, request: SearchRequest, limit: int):
        self.runs += 1
        self.started.set()
        self.release.wait(timeout=10.0)
        return [], "OK"


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "cancel.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            year INTEGER DEFAULT 0, deleted_at TEXT, albumartist TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5(
            title, artist, album, albumartist, content=media_items,
            content_rowid=id
        )
    """)
    conn.execute(
        "INSERT INTO media_items (filepath, title, artist, album, album_key) "
        "VALUES (?, ?, ?, ?, ?)",
        ("/m/rock.flac", "Rock Song", "Rock Band", "Rock Album", "ra1"),
    )
    conn.commit()
    conn.execute(
        "INSERT INTO media_fts (rowid, title, artist, album) "
        "SELECT id, title, artist, album FROM media_items"
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def stack(app, db_path):
    slow = SlowProvider()
    registry = SearchProviderRegistry()
    registry.register(SearchDomain.DEVICE, slow)
    registry.register(SearchDomain.TRACK, TrackSearchRepository(db_path))
    wm = WorkerManager()
    qe = QueryExecutor(worker_manager=wm)
    svc = GlobalSearchService(
        db_path=db_path, provider_registry=registry,
        query_executor=qe, worker_manager=wm,
    )
    yield svc, qe, wm, slow
    slow.release.set()
    wm.shutdown()


def _wait_until(app, predicate, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


class TestCancelAndStale:
    def test_second_search_supersedes_first(self, app, stack):
        svc, qe, wm, slow = stack
        first_box: list = []
        second_box: list = []
        rid1 = svc.search_async(
            SearchRequest(query="x", domains=frozenset({SearchDomain.DEVICE}),
                          owner="owner1", request_id="1"),
            on_result=first_box.append,
        )
        assert slow.started.wait(5)
        rid2 = svc.search_async(
            SearchRequest(query="Rock", domains=frozenset({SearchDomain.TRACK}),
                          owner="owner1", request_id="2"),
            on_result=second_box.append,
        )
        slow.release.set()
        assert _wait_until(app, lambda: len(second_box) > 0)
        assert qe.request_state(rid1) in ("stale", "cancelled"), (
            "superseded request must be finalized STALE or CANCELLED"
        )
        assert not first_box, "stale result must never reach the UI callback"
        assert isinstance(second_box[0], SearchResponse)
        assert second_box[0].error == ""
        assert any(i.title == "Rock Song" for i in second_box[0].items)
        assert rid2 != rid1

    def test_cancel_mid_run_fires_on_cancelled(self, app, stack):
        svc, qe, wm, slow = stack
        cancelled: list = []
        delivered: list = []
        rid = qe.submit(
            owner="c1",
            callable_fn=lambda: svc.search_request(SearchRequest(
                query="x", domains=frozenset({SearchDomain.DEVICE}),
                owner="c1", request_id="c1",
            )),
            on_success=delivered.append,
            on_cancelled=lambda: cancelled.append(True),
            supersede=False,
            cancellable=True,
        )
        assert slow.started.wait(5)
        qe.cancel(rid)
        slow.release.set()
        assert _wait_until(app, lambda: len(cancelled) > 0), (
            "cancel(request_id) mid-run must fire on_cancelled"
        )
        assert qe.request_state(rid) == "cancelled"
        assert not delivered

    def test_stale_result_not_delivered_on_cancel(self, app, stack):
        svc, qe, wm, slow = stack
        delivered: list = []
        cancelled: list = []
        rid = qe.submit(
            owner="c2",
            callable_fn=lambda: svc.search_request(SearchRequest(
                query="x", domains=frozenset({SearchDomain.DEVICE}),
                owner="c2", request_id="c2",
            )),
            on_success=delivered.append,
            on_cancelled=lambda: cancelled.append(True),
            supersede=False,
            cancellable=True,
        )
        assert slow.started.wait(5)
        qe.cancel_owner("c2")
        slow.release.set()
        assert _wait_until(app, lambda: len(cancelled) > 0)
        assert not delivered

    def test_wm_shutdown_reports_infrastructure_unavailable(self, app, db_path):
        wm = WorkerManager()
        qe = QueryExecutor(worker_manager=wm)
        svc = GlobalSearchService(
            db_path=db_path, query_executor=qe, worker_manager=wm,
        )
        try:
            assert svc.search_available()["ok"] is True
        finally:
            wm.shutdown()
        info = svc.search_available()
        assert info["ok"] is False
        assert any("operative" in r or "shutdown" in r for r in info["reasons"])
        box = []
        svc.search_async(SearchRequest(
            query="Rock", domains=frozenset({SearchDomain.TRACK}),
            owner="s", request_id="s1",
        ), on_result=box.append)
        assert box and box[0].error == INFRASTRUCTURE_UNAVAILABLE

    def test_search_available_false_without_providers(self, db_path):
        svc = GlobalSearchService(
            db_path=db_path, provider_registry=SearchProviderRegistry(),
        )
        info = svc.search_available()
        assert info["ok"] is False
        assert any("provider" in r for r in info["reasons"])

    def test_search_available_false_without_executor(self, db_path):
        svc = GlobalSearchService(db_path=db_path)
        info = svc.search_available()
        assert info["ok"] is False
        assert any("executor" in r for r in info["reasons"])
