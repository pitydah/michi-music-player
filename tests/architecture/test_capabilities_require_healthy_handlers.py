"""Capability = evidence, not object existence (ADR-006 rule 2).

A capability is available only when the gateway exists AND its backing
service is present. A gateway object constructed with None services must NOT
advertise its capabilities, and the registry's execution path must block the
tool (capability check happens in ToolRegistryV2.execute with the shared
resolver that carries the gateway evidence).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from core.assistant_gateways import AssistantGateways, ProductionPlaylistGateway
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.register_builtin import register_builtin_tools
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


def _playlist_service_fake():
    svc = MagicMock()
    svc.list.return_value = [{"id": 1, "name": "A", "track_count": 0}]
    svc.create_playlist.return_value = {"ok": True, "id": 9, "name": "N"}
    return svc


def _library_fake():
    db = MagicMock()
    db.get_media_item_by_id.return_value = SimpleNamespace(
        media_id=1, title="T", artist="A", album="Al",
        year=2020, genre="Rock", duration=120, format="flac", bitrate=900,
    )
    return db


def _build(gateways: AssistantGateways) -> tuple[ToolRegistryV2, CapabilityResolver]:
    resolver = CapabilityResolver()
    registry = ToolRegistryV2(capability_resolver=resolver)
    register_builtin_tools(registry, gateways, capabilities=resolver)
    return registry, resolver


def test_unbacked_gateway_object_does_not_advertise_capability() -> None:
    """Object existence is NOT enough: db=None + service=None → unavailable."""
    resolver = CapabilityResolver()
    resolver.register_from_gateways({"playlists": ProductionPlaylistGateway(None, None)})

    assert resolver.resolve("playlist.modify")["playlist.modify"].available is False


def test_backed_gateway_advertises_capability() -> None:
    resolver = CapabilityResolver()
    resolver.register_from_gateways(
        {"playlists": ProductionPlaylistGateway(None, _playlist_service_fake())}
    )

    assert resolver.resolve("playlist.modify")["playlist.modify"].available is True


def test_missing_gateway_is_unavailable() -> None:
    resolver = CapabilityResolver()
    resolver.register_from_gateways({"playlists": None})

    assert resolver.resolve("playlist.modify")["playlist.modify"].available is False


def test_composition_with_services_yields_available_capabilities() -> None:
    from core.assistant_initializer import create_assistant_composition

    comp = create_assistant_composition(
        library_db=_library_fake(),
        playlist_service=_playlist_service_fake(),
    )
    caps = comp.capability_resolver.resolve(["playlist.read", "playlist.modify", "library.read"])
    assert all(c.available for c in caps.values())


def test_composition_without_services_yields_unavailable_capabilities() -> None:
    from core.assistant_initializer import create_assistant_composition

    comp = create_assistant_composition()
    caps = comp.capability_resolver.resolve(["playlist.read", "playlist.modify", "library.read"])
    assert all(c.available is False for c in caps.values())


def test_registry_execution_blocks_unavailable_capability() -> None:
    """Execution-time check: the shared resolver carries gateway evidence and
    ToolRegistryV2.execute consults it before running the handler."""
    registry, _resolver = _build(AssistantGateways(playlists=None))
    result = registry.execute("list_playlists")
    assert result.ok is False
    assert result.code.value == "CAPABILITY_UNAVAILABLE"


def test_registry_execution_allows_backed_capability() -> None:
    gateways = AssistantGateways(
        playlists=ProductionPlaylistGateway(None, _playlist_service_fake()),
    )
    registry, _resolver = _build(gateways)
    result = registry.execute("list_playlists")
    assert result.ok is True
    assert result.data["total"] == 1


def test_capability_preserves_confirmation_contract() -> None:
    """Evidence re-registration must not clobber requires_confirmation."""
    resolver = CapabilityResolver()
    resolver.register("playlist.modify", available=True, requires_confirmation=True)
    resolver.register_from_gateways({"playlists": None})
    cap = resolver.resolve("playlist.modify")["playlist.modify"]
    assert cap.available is False
    assert cap.requires_confirmation is True
