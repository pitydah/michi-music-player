"""Fase 5 baseline — real read-only Player → Michi AI vertical slice."""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from michi_ai.integration import (
    HOST_INTEGRATION_API_VERSION,
    LIBRARY_GATEWAY_SCHEMA_VERSION,
    ErrorCode,
    LibraryGateway,
)

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.bootstrap import ApplicationContainer, _build_optional_michi_ai
from michi.domain.library import TrackRef
from michi.domain.library_catalog import MediaAvailability
from michi.integrations.michi_ai import (
    PLAYER_AI_CAPABILITIES,
    PlayerLibraryGateway,
    PlayerMichiAIIntegration,
    build_player_michi_ai,
)


class _Scanner:
    def scan(self, root: Path) -> list[Path]:
        return []

    def fingerprint(self, path: Path) -> tuple[int, int]:
        return (0, 0)


@dataclass
class _Graph:
    library: LibraryService
    track_resolver: LibraryTrackResolver


def _track(
    track_id: str,
    title: str,
    *,
    artist: str = "Pink Floyd",
    album: str = "The Dark Side of the Moon",
) -> TrackRef:
    return TrackRef(
        file_path=Path(f"/private/music/{title}.flac"),
        track_id=track_id,
        title=title,
        artist=artist,
        album=album,
        duration_ms=300_000,
        availability=MediaAvailability.AVAILABLE,
    )


def _real_graph() -> _Graph:
    library = LibraryService(_Scanner())
    library._commit_scan_result(  # test setup through the canonical commit chokepoint
        [
            _track("pf-money", "Money"),
            _track("pf-time", "Time", album="Wish You Were Here"),
            _track("", "Legacy without stable ID"),
        ],
        "/private/music",
    )
    return _Graph(library, LibraryTrackResolver(library))


def test_player_library_gateway_satisfies_public_protocol() -> None:
    graph = _real_graph()

    assert isinstance(
        PlayerLibraryGateway(graph.library, graph.track_resolver),
        LibraryGateway,
    )


def test_player_pins_supported_host_contract_versions() -> None:
    assert HOST_INTEGRATION_API_VERSION == "1.0"
    assert LIBRARY_GATEWAY_SCHEMA_VERSION == 1


def test_search_uses_pure_projection_without_mutating_player_search_state() -> None:
    graph = _real_graph()
    gateway = PlayerLibraryGateway(graph.library, graph.track_resolver)
    before_query = graph.library.state.query
    before_projection = graph.library.state.search_projection

    result = gateway.search("Pink Floyd")

    assert result.ok is True
    assert [track["track_id"] for track in result.data] == ["pf-money", "pf-time"]
    assert graph.library.state.query == before_query
    assert graph.library.state.search_projection is before_projection
    serialized = repr(result.data)
    assert "/private/music" not in serialized
    assert "file_path" not in serialized
    assert "media_file_id" not in serialized


def test_get_track_returns_path_free_v1_schema_and_effective_availability() -> None:
    graph = _real_graph()
    gateway = PlayerLibraryGateway(graph.library, graph.track_resolver)

    result = gateway.get_track("pf-money")

    assert result.ok is True
    assert result.data == {
        "track_id": "pf-money",
        "title": "Money",
        "artist": "Pink Floyd",
        "album": "The Dark Side of the Moon",
        "duration_ms": 300_000,
        "availability": "available",
    }


def test_get_track_unknown_id_fails_explicitly() -> None:
    graph = _real_graph()
    gateway = PlayerLibraryGateway(graph.library, graph.track_resolver)

    result = gateway.get_track("missing")

    assert result.ok is False
    assert result.code == ErrorCode.NO_MATCH.value
    assert result.data is None


def test_status_projects_canonical_state_without_paths() -> None:
    graph = _real_graph()
    gateway = PlayerLibraryGateway(graph.library, graph.track_resolver)

    result = gateway.get_status()

    assert result.ok is True
    assert result.data == {
        "total_tracks": 3,
        "total_artists": 1,
        "total_albums": 2,
        "available": True,
        "scan_status": "idle",
    }


def test_composition_publishes_only_real_library_capabilities() -> None:
    integration = build_player_michi_ai(_real_graph())

    assert isinstance(integration, PlayerMichiAIIntegration)
    assert integration.get_capabilities() == tuple(sorted(PLAYER_AI_CAPABILITIES))
    assert integration.get_capabilities() == ("library.read", "library.search")


def test_application_composition_root_owns_optional_ai_runtime() -> None:
    integration = _build_optional_michi_ai(_real_graph())
    container = ApplicationContainer()

    assert isinstance(integration, PlayerMichiAIIntegration)
    assert container._michi_ai_runtime is None


def test_optional_composition_tolerates_only_absent_top_level_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def import_without_michi_ai(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "michi.integrations.michi_ai":
            raise ModuleNotFoundError("No module named 'michi_ai'", name="michi_ai")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_michi_ai)

    assert _build_optional_michi_ai(_real_graph()) is None


def test_optional_composition_surfaces_incompatible_host_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def import_with_broken_contract(
        name, globals=None, locals=None, fromlist=(), level=0
    ):
        if name == "michi.integrations.michi_ai":
            raise ModuleNotFoundError(
                "No module named 'michi_ai.integration'",
                name="michi_ai.integration",
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_broken_contract)

    with pytest.raises(ModuleNotFoundError, match="michi_ai.integration"):
        _build_optional_michi_ai(_real_graph())


def test_real_vertical_slice_searches_player_library_through_michi_ai() -> None:
    integration = build_player_michi_ai(_real_graph())

    outcome = integration.process("busca Pink Floyd")

    assert outcome.result.ok is True
    assert outcome.backend == "calico"
    assert outcome.tool_name == "search_library"
    assert [track["track_id"] for track in outcome.result.data] == [
        "pf-money",
        "pf-time",
    ]


def test_unpublished_capability_is_rejected_before_gateway_fabrication() -> None:
    integration = build_player_michi_ai(_real_graph())

    outcome = integration.process("estado del link")

    assert outcome.result.ok is False
    assert outcome.result.code == ErrorCode.CAPABILITY_UNAVAILABLE.value


def test_lifecycle_methods_delegate_and_shutdown_is_idempotent() -> None:
    integration = build_player_michi_ai(_real_graph())

    assert integration.confirm("missing").code == ErrorCode.PLAN_NOT_FOUND.value
    assert integration.reject("missing").code == ErrorCode.PLAN_NOT_FOUND.value
    assert integration.cancel("missing").code == ErrorCode.PLAN_NOT_FOUND.value

    integration.shutdown()
    integration.shutdown()
    assert integration.is_shutdown is True


def test_shutdown_converges_and_cancels_remaining_plans_after_failure() -> None:
    class _FailingRuntime:
        def __init__(self) -> None:
            self.cancelled: list[str] = []

        def get_pending_plans(self):
            return (SimpleNamespace(plan_id="first"), SimpleNamespace(plan_id="second"))

        def cancel(self, plan_id: str) -> None:
            self.cancelled.append(plan_id)
            if plan_id == "first":
                raise RuntimeError("cancel failed")

    runtime = _FailingRuntime()
    integration = PlayerMichiAIIntegration(runtime)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="cancel failed"):
        integration.shutdown()

    assert runtime.cancelled == ["first", "second"]
    assert integration.is_shutdown is True
    integration.shutdown()
