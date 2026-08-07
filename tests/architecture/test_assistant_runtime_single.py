"""FASE 9 — exactly ONE assistant runtime composition (single authority).

The productive runtime registers a SINGLE ``assistant_runtime`` object that
contains and governs every internal subsystem (intent resolution, capability
resolution, context assembly, plan builder, plan validation, confirmation
policy, plan execution, tool registry, conversation service, trace recorder,
backend selection). ``MichiAIEngine`` delegates to it and does NOT construct
its own planner/executor/resolver/registry — no duplicate pipelines.

Capability resolution additionally consults container health per backing
service (F9 full health gate): gateway evidence + registered service +
healthy service + method exists.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.assistant_initializer import create_assistant_composition
from core.assistant_gateways import ProductionPlaylistGateway
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.register_builtin import register_builtin_tools
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _source(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_engine_does_not_construct_its_own_planner_or_executor() -> None:
    """The facade must delegate; no duplicate pipelines in ai_engine.py."""
    engine_source = _source("core/ai_engine.py")
    for forbidden in (
        "PlanBuilderV2(",
        "PlanExecutorV2(",
        "PlanValidator(",
        "CapabilityResolver(",
        "ConfirmationPolicyV2(",
        "ToolRegistryV2(",
    ):
        assert forbidden not in engine_source, (
            f"MichiAIEngine constructs '{forbidden}' directly — must delegate "
            "to assistant_runtime"
        )


def test_composition_constructs_runtime_exactly_once() -> None:
    init_source = _source("core/assistant_initializer.py")
    constructions = re.findall(r"AssistantRuntime\(", init_source)
    assert len(constructions) == 1, (
        f"Expected exactly ONE AssistantRuntime construction, found {len(constructions)}"
    )


def test_runtime_subsystems_are_the_composition_subsystems() -> None:
    """Composition fields are the runtime's controlled instances (identity)."""
    comp = create_assistant_composition()
    rt = comp.runtime
    assert comp.tool_registry is rt.tool_registry
    assert comp.capability_resolver is rt.capability_resolver
    assert comp.planner is rt.planner
    assert comp.validator is rt.validator
    assert comp.executor is rt.executor
    assert comp.context_assembler is rt.context_assembler
    assert comp.conversation_service is rt.conversation_service
    assert comp.confirmation_policy is rt.confirmation_policy
    assert comp.trace_recorder is rt.trace_recorder
    assert comp.backend_selector is rt.backend_selector
    assert comp.core_service.tool_registry is rt.tool_registry


def test_runtime_exposes_all_controlled_interfaces() -> None:
    rt = create_assistant_composition().runtime
    for attr in (
        "tool_registry", "capability_resolver", "planner", "validator",
        "executor", "context_assembler", "conversation_service",
        "confirmation_policy", "trace_recorder", "backend_selector",
    ):
        assert hasattr(rt, attr), f"assistant_runtime missing controlled interface '{attr}'"


def _playlist_service_fake():
    svc = MagicMock()
    svc.list.return_value = [{"id": 1, "name": "A", "track_count": 0}]
    svc.create_playlist.return_value = {"ok": True, "id": 9, "name": "N"}
    return svc


def _composition_with_health(healthy: bool) -> tuple[ToolRegistryV2, CapabilityResolver]:
    gateways = SimpleNamespace(
        playlists=ProductionPlaylistGateway(None, _playlist_service_fake()),
        queue=None, library=None, settings=None, audio_lab=None, devices=None,
        diagnostics=None, mix=None, jobs=None, navigation=None, radio=None,
        metadata=None, playback=None, lyrics=None, library_doctor=None,
        connections=None, home_audio=None,
    )
    gateways.to_dict = lambda: {
        "playlists": gateways.playlists,
    }
    resolver = CapabilityResolver(health_provider=lambda service_key: healthy)
    registry = ToolRegistryV2(capability_resolver=resolver)
    register_builtin_tools(registry, gateways, capabilities=resolver)
    return registry, resolver


def test_tool_without_backend_not_available() -> None:
    """Gateway object present but backing service absent/unhealthy → tool
    must NOT be available (F9 full health gate)."""
    registry, resolver = _composition_with_health(healthy=False)
    caps = resolver.resolve("playlist.modify")
    assert caps["playlist.modify"].available is False
    result = registry.execute("list_playlists")
    assert result.ok is False
    assert result.code.value == "CAPABILITY_UNAVAILABLE"


def test_tool_with_failed_service_not_available() -> None:
    """Service present but container health reports failed → unavailable."""
    calls: list[str] = []

    def _health_provider(service_key: str) -> bool:
        calls.append(service_key)
        return False

    resolver = CapabilityResolver(health_provider=_health_provider)
    resolver.register("playlist.modify", available=True)
    cap = resolver.resolve("playlist.modify")["playlist.modify"]
    assert cap.available is False
    assert cap.reason == "service_unhealthy:playlist_service"
    assert "playlist_service" in calls


def test_healthy_backing_service_keeps_capability_available() -> None:
    registry, resolver = _composition_with_health(healthy=True)
    caps = resolver.resolve("playlist.modify")
    assert caps["playlist.modify"].available is True
    result = registry.execute("list_playlists")
    assert result.ok is True


def test_resolver_without_health_provider_is_evidence_only() -> None:
    """No container wired (tests/standalone): gateway evidence decides."""
    resolver = CapabilityResolver()
    resolver.register_from_gateways(
        {"playlists": ProductionPlaylistGateway(None, _playlist_service_fake())}
    )
    assert resolver.resolve("playlist.modify")["playlist.modify"].available is True
