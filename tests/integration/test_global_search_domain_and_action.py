"""Vertical slice (Slice 6): real GlobalSearchService + real QueryExecutor +
WorkerManager over a real DB — domain filtering and explicit result actions.

- ``search(SearchRequest)`` dispatches through the provider registry; domain
  filters are honored (an ALBUM-only request never returns tracks).
- Bridge actions execute through ActionContext → ActionRegistry with explicit
  result references and reach a real QueueService (readback).
"""
from __future__ import annotations

import sqlite3
import time

import pytest
from PySide6.QtCore import QCoreApplication

from core.action_context import ActionContext
from core.global_search_service import GlobalSearchService
from core.query_executor import QueryExecutor
from core.queue_service import QueueService
from core.search.models import SearchDomain, SearchRequest, SearchResponse
from core.search.providers import build_default_registry
from core.worker_manager import WorkerManager
from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.global_search_bridge import GlobalSearchBridge

_TRACKS = [
    ("/m/rock.flac", "Rock Song", "Rock Band", "Rock Album", "ra1"),
    ("/m/jazz.flac", "Jazz Song", "Jazz Trio", "Jazz Night", "ja1"),
    ("/m/pop.flac", "Pop Hit", "Pop Star", "Pop World", "pa1"),
]


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "search.db")
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, track_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radio_stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, url TEXT, codec TEXT, country TEXT
        )
    """)
    for fp, title, artist, album, ak in _TRACKS:
        conn.execute(
            "INSERT INTO media_items (filepath, title, artist, album, album_key) "
            "VALUES (?, ?, ?, ?, ?)",
            (fp, title, artist, album, ak),
        )
    conn.execute(
        "INSERT INTO playlists (name, track_count) VALUES ('Rock Faves', 9)"
    )
    conn.execute(
        "INSERT INTO radio_stations (name, url, codec, country) "
        "VALUES ('Rock FM', 'http://rock.fm', 'MP3', 'US')"
    )
    conn.commit()
    conn.execute(
        "INSERT INTO media_fts (rowid, title, artist, album) "
        "SELECT id, title, artist, album FROM media_items"
    )
    conn.commit()
    conn.close()
    return path


def _wait_until(app, predicate, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def _make_service(db_path: str, wm: WorkerManager | None = None):
    qe = QueryExecutor(worker_manager=wm) if wm else None
    svc = GlobalSearchService(
        db_path=db_path,
        provider_registry=build_default_registry(db_path),
        query_executor=qe,
        worker_manager=wm,
    )
    return svc, qe


class TestDomainFiltering:
    def test_async_track_and_album_domains(self, app, db_path):
        wm = WorkerManager()
        svc, qe = _make_service(db_path, wm)
        try:
            box = []
            svc.search_async(
                SearchRequest(
                    query="Rock",
                    domains=frozenset({SearchDomain.TRACK, SearchDomain.ALBUM}),
                    limit_per_domain=10, total_limit=50,
                    owner="it", request_id="r1",
                ),
                on_result=box.append,
            )
            assert _wait_until(app, lambda: len(box) > 0)
            resp = box[0]
            assert isinstance(resp, SearchResponse)
            assert resp.error == ""
            types = {i.result_type for i in resp.items}
            assert types <= {"track", "album"}
            tracks = [i for i in resp.items if i.result_type == "track"]
            assert any(i.title == "Rock Song" for i in tracks)
            assert all(i.public_ref.startswith("track_") for i in tracks)
            assert resp.status_codes["TRACK"] == "FTS_AVAILABLE"
        finally:
            wm.shutdown()

    def test_album_domain_never_returns_tracks(self, app, db_path):
        wm = WorkerManager()
        svc, qe = _make_service(db_path, wm)
        try:
            box = []
            svc.search_async(
                SearchRequest(
                    query="Rock",
                    domains=frozenset({SearchDomain.ALBUM}),
                    limit_per_domain=10, total_limit=50,
                    owner="it", request_id="r2",
                ),
                on_result=box.append,
            )
            assert _wait_until(app, lambda: len(box) > 0)
            resp = box[0]
            assert all(i.result_type == "album" for i in resp.items)
            assert not any(i.result_type == "track" for i in resp.items)
            assert any(i.title == "Rock Album" for i in resp.items)
            assert "TRACK" not in resp.status_codes
        finally:
            wm.shutdown()

    def test_sync_search_request_domains(self, db_path):
        svc, _qe = _make_service(db_path)
        resp = svc.search_request(SearchRequest(
            query="Rock",
            domains=frozenset({SearchDomain.TRACK, SearchDomain.ALBUM}),
            limit_per_domain=10, total_limit=50,
            owner="it", request_id="r3",
        ))
        types = {i.result_type for i in resp.items}
        assert "track" in types
        assert "album" in types
        assert "playlist" not in types

    def test_legacy_search_still_returns_sections(self, db_path):
        svc, _qe = _make_service(db_path)
        result = svc.search("Rock", owner="it", timeout_ms=10000)
        assert result["ok"]
        assert result["count"] > 0
        sections = {r["section"] for r in result["results"]}
        assert "Canciones" in sections


class TestExplicitResultActions:
    def test_bridge_action_reaches_queue_with_context(self, app, db_path):
        wm = WorkerManager()
        svc, qe = _make_service(db_path, wm)
        queue = QueueService()
        captured: list[ActionContext] = []
        registry = ActionRegistry()

        def enqueue_handler(ctx: ActionContext):
            captured.append(ctx)
            return queue.enqueue([{
                "track_id": int(ctx.entity_id),
                "filepath": f"/m/{ctx.entity_id}.flac",
                "title": "Rock Song", "artist": "Rock Band",
                "album": "Rock Album", "duration": 200,
            }])

        action = registry.get("track_add_to_queue")
        action.handler = enqueue_handler
        bridge = GlobalSearchBridge(
            search_service=svc, query_executor=qe, action_registry=registry,
        )
        try:
            resp = svc.search_request(SearchRequest(
                query="Rock", domains=frozenset({SearchDomain.TRACK}),
                limit_per_domain=10, total_limit=50,
                owner="it", request_id="r7",
            ))
            track = next(i for i in resp.items if i.result_type == "track")
            result = bridge.executeSearchResultAction(
                track.result_id, track.result_type, track.public_ref,
                "track_add_to_queue", "7",
            )
            assert result["ok"]
            assert len(captured) == 1
            ctx = captured[0]
            assert ctx.entity_type == "track"
            assert ctx.entity_id == track.result_id
            assert ctx.public_ref == f"track_{track.result_id}"
            assert ctx.selection_version == 7
            assert ctx.source_route == "search"
            assert ctx.source_component == "global_search"
            assert ctx.selected_ids == (int(track.result_id),)
            # Queue readback: the explicit result reached the real queue.
            items = queue.get_items()
            assert len(items) == 1
            assert str(items[0]["track_id"]) == track.result_id
        finally:
            wm.shutdown()

    def test_bridge_never_uses_global_selection(self, db_path):
        svc, _qe = _make_service(db_path)
        captured = []
        registry = ActionRegistry()
        action = registry.get("track_play_now")
        action.handler = lambda ctx: (captured.append(ctx), {"ok": True})[1]
        bridge = GlobalSearchBridge(
            search_service=svc, action_registry=registry,
        )
        resp = svc.search_request(SearchRequest(
            query="Rock", domains=frozenset({SearchDomain.TRACK}),
            limit_per_domain=10, total_limit=50,
            owner="it", request_id="r8",
        ))
        legacy = GlobalSearchBridge._response_to_legacy(resp, 8)
        bridge._results = legacy["results"]
        bridge._active_request_id = 8
        result = bridge.executeResultAction("1", "play")
        assert result["ok"]
        assert len(captured) == 1
        ctx = captured[0]
        assert ctx.entity_id == "1"
        assert ctx.selection_version == 8
        assert ctx.source_route == "search"

    def test_action_registry_refuses_without_explicit_context(self, db_path):
        """The registry contract: search actions must carry a context."""
        svc, _qe = _make_service(db_path)
        registry = ActionRegistry()
        bridge = GlobalSearchBridge(
            search_service=svc, action_registry=registry,
        )
        result = bridge.executeSearchResultAction(
            "1", "track", "track_1", "track_add_to_queue", "9",
        )
        assert result.get("ok") is False
        assert result.get("error") == "NO_HANDLER"
