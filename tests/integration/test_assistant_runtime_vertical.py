"""FASE 9 — vertical slice through the SINGLE assistant_runtime.

Real composition (create_assistant_composition) + real services on a tmp DB.
The engine facade delegates to the runtime; the runtime governs the full
pipeline: intent → plan → validate → confirm (runtime confirmation policy)
→ execute (runtime executor) → readback.

Guards the F9 contracts:
- destructive tools require confirmation via the runtime confirmation policy
- validator rejection surfaces as outer ok=False
- expired confirmations never execute
- tool failure propagates as outer ok=False (S4 contract, runtime path)
- context assembly consumes the real S11 ContextService data
- container registers assistant_runtime + michi_ai_service (one runtime)
- two consecutive process_message calls share ONE planner/executor
"""
from __future__ import annotations

from unittest.mock import MagicMock

from core.ai.intent_router import IntentResult
from core.assistant_initializer import create_assistant_composition
from core.context.context_service import ContextService
from core.playlist_service import PlaylistService
from library.library_db import LibraryDB
from michi_ai.v2.core.models import PlanValidationResult
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2

TRACKS = [
    ("/m/one.flac", "one.flac", "/m", ".flac", "One", "Artist A", "Album A", "album-a", "uid-1"),
    ("/m/two.flac", "two.flac", "/m", ".flac", "Two", "Artist A", "Album A", "album-a", "uid-2"),
    ("/m/three.flac", "three.flac", "/m", ".flac", "Three", "Artist B", "Album B", "album-b", "uid-3"),
]


def _make_db() -> LibraryDB:
    db = LibraryDB(":memory:")
    db.conn.executemany(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album, "
        "album_key, track_uid) VALUES (?, ?, ?, ?, 'audio', ?, ?, ?, ?, ?)",
        TRACKS,
    )
    db.conn.commit()
    return db


def _router(intent_id: str, entities: dict | None = None) -> MagicMock:
    router = MagicMock()
    router.detect.side_effect = lambda text, context=None: IntentResult(
        intent_id=intent_id,
        confidence=0.9,
        entities=entities or {},
        needs_llm=False,
        raw_text=text,
    )
    return router


def _stack(
    router: MagicMock | None = None,
    confirmation_policy: ConfirmationPolicyV2 | None = None,
    context_service: ContextService | None = None,
) -> tuple[LibraryDB, PlaylistService, object]:
    db = _make_db()
    playlist_service = PlaylistService(db=db)
    comp = create_assistant_composition(
        library_db=db,
        playlist_service=playlist_service,
        intent_router=router,
        confirmation_policy=confirmation_policy,
        context_service=context_service,
    )
    return db, playlist_service, comp


def test_destructive_confirmation() -> None:
    db = _make_db()
    playlist_service = PlaylistService(db=db)
    created = playlist_service.create("Para Borrar")
    pid = int(created["id"])
    comp = create_assistant_composition(
        library_db=db,
        playlist_service=playlist_service,
        intent_router=_router("delete_playlist", {"playlist_id": str(pid)}),
    )

    result = comp.core_service.process_message("borra la playlist Para Borrar")

    assert result["ok"] is True
    assert result["requires_confirmation"] is True
    assert result["plan_id"]
    assert result["plan"]["tool"] == "delete_playlist"
    assert result["plan"]["destructive"] is True
    assert result["tool_result"] is None
    # Without approval the tool never ran.
    assert playlist_service.get_detail(pid)["ok"] is True

    confirmed = comp.core_service.confirm_plan(result["plan_id"])

    assert confirmed["ok"] is True
    assert confirmed["plan_id"] == result["plan_id"]
    detail = playlist_service.get_detail(pid)
    assert detail.get("ok") is False, "playlist still exists after confirmed delete"


def test_plan_rejection(monkeypatch) -> None:
    _db, playlist_service, comp = _stack(
        router=_router("delete_playlist", {"playlist_id": "1"}),
    )
    monkeypatch.setattr(
        comp.runtime.validator, "validate",
        lambda plan: PlanValidationResult(status="INVALID", errors=("boom",)),
    )

    result = comp.core_service.process_message("borra la playlist X")

    assert result["ok"] is False
    assert result["error"] == "PLAN_INVALID"
    assert result["tool_result"]["code"] == "PLAN_INVALID"
    assert playlist_service.list() == []


def test_plan_expiration() -> None:
    db = _make_db()
    playlist_service = PlaylistService(db=db)
    created = playlist_service.create("Para Borrar")
    pid = int(created["id"])
    comp = create_assistant_composition(
        library_db=db,
        playlist_service=playlist_service,
        intent_router=_router("delete_playlist", {"playlist_id": str(pid)}),
        confirmation_policy=ConfirmationPolicyV2(ttl_seconds=-1),
    )

    result = comp.core_service.process_message("borra la playlist Para Borrar")
    assert result["requires_confirmation"] is True

    confirmed = comp.core_service.confirm_plan(result["plan_id"])

    assert confirmed["ok"] is False
    assert confirmed["error"] == "CONFIRMATION_EXPIRED"
    assert playlist_service.get_detail(pid)["ok"] is True, (
        "expired confirmation must never execute the tool"
    )


def test_tool_failure_outer_ok_false() -> None:
    # Real failure through the runtime path: set_volume has NO backing player
    # service, so capability evidence blocks it at execution time and the
    # tool failure must surface as outer ok=False with an error (S4).
    _db, playlist_service, comp = _stack(
        router=_router("playback_volume", {"volume": "50"}),
    )

    result = comp.core_service.process_message("sube el volumen")

    assert result["ok"] is False, "tool failure must NOT be reported as ok"
    assert result["error"], "tool failure must carry an error"
    assert result["tool_result"]["code"] == "CAPABILITY_UNAVAILABLE"
    assert playlist_service.list() == [], "failed tool must not mutate data"


def test_context_provider_real() -> None:
    db = _make_db()
    context_service = ContextService(db=db)
    _db, _playlist_service, comp = _stack(context_service=context_service)

    snapshot = comp.runtime.context_assembler.assemble()

    library = snapshot.library or {}
    assert library.get("track_count") == 3, (
        f"context library section must come from the real DB, got {library}"
    )


def test_runtime_registered_full(monkeypatch) -> None:
    from core import assistant_initializer
    from core.composition import intelligence
    from core.service_container import ServiceContainer

    captured: dict[str, object] = {}
    real_builder = assistant_initializer.create_assistant_composition

    def spy_builder(**kwargs):
        comp = real_builder(**kwargs)
        captured["comp"] = comp
        return comp

    monkeypatch.setattr(assistant_initializer, "create_assistant_composition", spy_builder)
    container = ServiceContainer()
    intelligence.build(container)

    comp = captured["comp"]
    assert container.get("assistant_runtime") is comp.runtime
    assert container.get("michi_ai_service") is comp.core_service
    assert container.contains("assistant_runtime")
    assert container.contains("michi_ai_service")

    # Engine delegates: a runtime planner call happens through the engine.
    rt = comp.runtime
    router = _router("delete_playlist", {"playlist_id": "1"})
    calls = {"n": 0}
    original = rt.planner.build_plan

    def spy_build_plan(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(rt.planner, "build_plan", spy_build_plan)
    monkeypatch.setattr(rt, "_intent_router", router)
    comp.core_service.process_message("borra la playlist X")
    assert calls["n"] >= 1, "engine.process_message did not go through runtime planner"


def test_single_planner_executor(monkeypatch) -> None:
    _db, _playlist_service, comp = _stack()
    rt = comp.runtime
    planner = rt.planner
    executor = rt.executor
    resolver = rt.capability_resolver
    registry = rt.tool_registry

    router = MagicMock()
    router.detect.side_effect = lambda text, context=None: IntentResult(
        intent_id="search_library", confidence=0.9,
        entities={"query": "jazz"}, needs_llm=False, raw_text=text,
    )
    monkeypatch.setattr(rt, "_intent_router", router)

    comp.core_service.process_message("busca jazz")
    comp.core_service.process_message("busca jazz")

    assert comp.core_service.runtime.planner is planner
    assert comp.core_service.runtime.executor is executor
    assert comp.core_service.runtime.capability_resolver is resolver
    assert comp.core_service.runtime.tool_registry is registry
