"""Tests for deterministic order in the public BridgeFactory output."""

from unittest.mock import MagicMock

from core.service_container import ServiceContainer
from ui_qml_bridge.bridge_factory import BridgeFactory


def _make_container(**overrides) -> ServiceContainer:
    container = ServiceContainer()
    services = {
        "action_registry": MagicMock(),
        "audio_lab_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "connection_factory": MagicMock(),
        "connection_service": MagicMock(),
        "database": MagicMock(),
        "device_sync_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "disc_lab_service": MagicMock(),
        "folder_service": MagicMock(),
        "global_search_service": MagicMock(),
        "history_query_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "job_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "library_mutation_service": MagicMock(),
        "library_query_service": MagicMock(),
        "library_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "lyrics_service": MagicMock(),
        "metadata_service": MagicMock(),
        "michi_ai_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "mix_service": MagicMock(),
        "mobile_sync_service": MagicMock(),
        "navigation_service": MagicMock(),
        "notification_service": MagicMock(),
        "playback_service": MagicMock(),
        "playlist_service": MagicMock(),
        "process_controller": MagicMock(),
        "query_executor": MagicMock(),
        "queue_service": MagicMock(),
        "radio_service": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "track_action_service": MagicMock(),
        "worker_manager": MagicMock(),
    }
    services.update(overrides)
    for name, service in services.items():
        container.register(name, service)
    return container


def _creation_order() -> list[str]:
    return list(BridgeFactory(_make_container()).create_all())


def _assert_before(order: list[str], earlier: str, later: str) -> None:
    assert earlier in order
    assert later in order
    assert order.index(earlier) < order.index(later)


class TestPublicCreationOrder:
    def test_foundation_bridges_precede_domain_bridges(self):
        order = _creation_order()

        _assert_before(order, "page_state", "navigation")
        _assert_before(order, "navigation", "action_registry")
        _assert_before(order, "action_registry", "playlists")
        _assert_before(order, "job_bridge", "library")
        _assert_before(order, "capability", "playback")

    def test_domain_relative_order(self):
        order = _creation_order()

        _assert_before(order, "playlists", "library")
        _assert_before(order, "library", "library_sources")
        _assert_before(order, "library_sources", "nowplaying")
        _assert_before(order, "nowplaying", "playback")
        _assert_before(order, "playback", "queue")
        _assert_before(order, "history", "global_search")

    def test_aggregate_relative_order(self):
        order = _creation_order()

        _assert_before(order, "action_registry", "notification")
        _assert_before(order, "queue", "app")
        _assert_before(order, "notification", "home")
        _assert_before(order, "home", "app")
        _assert_before(order, "app", "desktop")


class TestOrderInvariants:
    def test_create_all_produces_stable_order(self):
        first = _creation_order()
        second = _creation_order()

        assert first == second

    def test_create_all_has_no_duplicate_keys(self):
        order = _creation_order()

        assert len(order) == len(set(order))

    def test_repeated_create_all_preserves_order(self):
        factory = BridgeFactory(_make_container())

        first = list(factory.create_all())
        second = list(factory.create_all())

        assert first == second
