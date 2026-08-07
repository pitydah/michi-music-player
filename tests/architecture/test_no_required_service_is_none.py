"""Required services must never resolve to None."""
from __future__ import annotations

from core.service_container import ServiceContainer


def test_validate_required_present_rejects_none() -> None:
    container = ServiceContainer()
    container.register("database", None)
    missing = container.validate_required_present()
    assert "database" in missing


def test_validate_required_present_rejects_missing() -> None:
    container = ServiceContainer()
    assert "worker_manager" in container.validate_required_present()


def test_validate_reports_required_none_as_error() -> None:
    container = ServiceContainer()
    container.register("event_bus", None)
    errors = container.validate()
    assert any("REQUIRED 'event_bus' is None or missing" in e for e in errors)


def test_start_fails_on_missing_required() -> None:
    from core.service_container import ContainerState

    container = ServiceContainer()
    container.register("connection_factory", object())
    container.start()
    assert container.state == ContainerState.FAILED


def test_optional_none_does_not_block_start() -> None:
    from core.service_container import ContainerState

    container = ServiceContainer()
    container.register("database", object())
    container.register("connection_factory", object())
    container.register("worker_manager", object())
    container.register("query_executor", object())
    container.register("job_service", object())
    container.register("event_bus", object())
    container.register("settings_coordinator", object())
    container.register("settings_service", object())
    container.register("library_query_service", object())
    container.register("library_sources_service", object())
    container.register("library_mutation_service", object())
    container.register("playlist_service", object())
    container.register("history_query_service", object())
    container.register("global_search_service", object())
    container.register("mix_query_service", object())
    container.register("mix_service", object())
    container.register("track_action_service", object())
    container.register("playback_service", object())
    container.register("queue_service", object())
    container.register("metadata_service", object())
    container.register("process_controller", object())
    container.register("runtime_persistence", object())
    container.register("theme_service", object())
    container.register("accessibility_service", object())
    container.register("action_registry", object())
    container.register("confirmation_service", object())
    container.register("notification_service", object())
    container.register("diagnostics_service", object())
    # REQUIRED descriptors declare these dependencies in the manifest; a
    # REQUIRED descriptor with a missing dependency blocks bootstrap.
    container.register("favorite_service", object())
    container.register("search_provider_registry", object())
    container.register("radio_service", None)
    container.start()
    assert container.state in (ContainerState.READY, ContainerState.DEGRADED)
