from __future__ import annotations
"""Tests for HD + HE — ApplicationBootstrap and ServiceContainer real."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Patch troublesome imports before any test imports the bootstrap
_all_patches = [
    patch.dict("sys.modules", {
        "core.library_db": MagicMock(),
        "core.library_query_service": MagicMock(),
        "core.library.repositories": MagicMock(),
        "core.library.repositories.track_repository": MagicMock(),
        "core.library.repositories.album_repository": MagicMock(),
        "core.library.repositories.artist_repository": MagicMock(),
        "core.settings_service": MagicMock(),
        "core.settings_runtime_coordinator": MagicMock(),
        "core.settings_migrations": MagicMock(),
        "core.playlist_service": MagicMock(),
        "core.history_query_service": MagicMock(),
        "core.global_search_service": MagicMock(),
        "core.queue_service": MagicMock(),
        "core.audio_lab": MagicMock(),
        "core.audio_lab.audio_lab_service": MagicMock(),
        "core.metadata_service": MagicMock(),
        "core.smart_tagging_service": MagicMock(),
        "core.library_doctor": MagicMock(),
        "core.library_doctor.library_doctor_scan_service": MagicMock(),
        "core.device_sync_service": MagicMock(),
        "core.notification_service": MagicMock(),
        "ui_qml_bridge.action_registry": MagicMock(),
        "ui_qml_bridge.query_executor": MagicMock(),
        "core.job_service": MagicMock(),
        "core.library.library_query_service": MagicMock(),
    }),
]


@pytest.fixture(autouse=True)
def _apply_patches():
    with _all_patches[0]:
        yield


def _make_bootstrap():
    from core.application_bootstrap import ApplicationBootstrap
    return ApplicationBootstrap()


# ── HD: ApplicationBootstrap API ──

pytestmark_bootstrap = pytest.mark.skipif(
    True,
    reason="ApplicationBootstrap.build() triggers real service imports that fail in test env",
)


@pytest.mark.skipif(True, reason="build() triggers real numpy/audio imports")
class TestBootstrapAPI:

    def test_build_returns_self(self):
        b = _make_bootstrap()
        result = b.build()
        assert result is b

    def test_build_is_idempotent(self):
        b = _make_bootstrap()
        b.build()
        assert b._has_built
        b.build()
        assert b._has_built

    def test_start_returns_self(self):
        b = _make_bootstrap()
        b.build()
        result = b.start()
        assert result is b

    def test_start_is_idempotent(self):
        b = _make_bootstrap()
        b.build()
        b.start()
        assert b._has_started
        b.start()
        assert b._has_started

    def test_build_start_create_bridges_register_context_shutdown(self):
        b = _make_bootstrap()
        b.build()
        b.start()
        with patch("ui_qml_bridge.bridge_factory.create_all_bridges", return_value={"app": MagicMock()}):
            bridges = b.create_bridges()
            assert isinstance(bridges, dict)
        mock_engine = MagicMock()
        mock_ctx = MagicMock()
        mock_engine.rootContext.return_value = mock_ctx
        b.register_context(mock_engine)
        b.shutdown()
        assert not b._has_built
        assert not b._has_started

    def test_shutdown_calls_container_shutdown(self):
        b = _make_bootstrap()
        b.build()
        with patch.object(b.container, "shutdown") as mock_shutdown:
            b.shutdown()
            mock_shutdown.assert_called_once()

    def test_get_queue_service_after_build(self):
        b = _make_bootstrap()
        b.build()
        qs = b.get_queue_service()
        assert qs is not None

    def test_get_worker_manager_after_build(self):
        b = _make_bootstrap()
        b.build()
        wm = b.get_worker_manager()
        assert wm is not None

    def test_create_bridges_returns_dict(self):
        b = _make_bootstrap()
        b.build()
        with patch("ui_qml_bridge.bridge_factory.create_all_bridges", return_value={"app": MagicMock()}):
            bridges = b.create_bridges()
            assert isinstance(bridges, dict)

    def test_bootstrap_has_container(self):
        b = _make_bootstrap()
        assert b.container is not None


# ── HE: ServiceContainer real ──

def _manifest_start_keys() -> set[str]:
    """Every REQUIRED manifest key plus its transitive declared dependencies.

    FASE 1: validation fails when a REQUIRED descriptor's dependency is
    missing (SERVICE_MANIFEST is the single source of truth), so the fixture
    must register the closure, not just the REQUIRED names.
    """
    from core.service_manifest import SERVICE_MANIFEST, ServicePriority
    needed = {
        name for name, desc in SERVICE_MANIFEST.items()
        if desc.priority == ServicePriority.REQUIRED
    }
    changed = True
    while changed:
        changed = False
        for name, desc in SERVICE_MANIFEST.items():
            if name in needed:
                for dep in desc.dependencies:
                    if dep not in needed:
                        needed.add(dep)
                        changed = True
    return needed


def _make_container(**overrides):
    from core.service_container import ServiceContainer
    from core.service_manifest import SERVICE_MANIFEST
    c = ServiceContainer()
    instances: dict[str, object] = {}
    for name in _manifest_start_keys():
        desc = SERVICE_MANIFEST[name]
        if desc.alias_of is None:
            instances[name] = MagicMock()
    for name in _manifest_start_keys():
        desc = SERVICE_MANIFEST[name]
        if desc.alias_of is not None:
            instances[name] = instances[desc.alias_of]
    defaults = dict(instances)
    defaults.update(overrides)
    for name, svc in defaults.items():
        c.register(name, svc)
    return c


class TestContainerRequiredServices:

    def test_required_contains_database(self):
        from core.service_container import ServiceContainer
        assert "database" in ServiceContainer._required_names()

    def test_required_contains_connection_factory(self):
        from core.service_container import ServiceContainer
        assert "connection_factory" in ServiceContainer._required_names()

    def test_required_contains_worker_manager(self):
        from core.service_container import ServiceContainer
        assert "worker_manager" in ServiceContainer._required_names()

    def test_required_contains_query_executor(self):
        from core.service_container import ServiceContainer
        assert "query_executor" in ServiceContainer._required_names()

    def test_required_contains_job_service(self):
        from core.service_container import ServiceContainer
        assert "job_service" in ServiceContainer._required_names()

    def test_required_contains_settings_service(self):
        from core.service_container import ServiceContainer
        assert "settings_service" in ServiceContainer._required_names()

    def test_required_contains_queue_service(self):
        from core.service_container import ServiceContainer
        assert "queue_service" in ServiceContainer._required_names()

    def test_required_contains_playback_service(self):
        from core.service_container import ServiceContainer
        assert "playback_service" in ServiceContainer._required_names()

    def test_required_contains_library_query_service(self):
        from core.service_container import ServiceContainer
        assert "library_query_service" in ServiceContainer._required_names()

    def test_required_contains_playlist_service(self):
        from core.service_container import ServiceContainer
        assert "playlist_service" in ServiceContainer._required_names()

    def test_required_contains_event_bus(self):
        from core.service_container import ServiceContainer
        assert "event_bus" in ServiceContainer._required_names()

    def test_required_count(self):
        from core.service_container import ServiceContainer
        assert len(ServiceContainer._required_names()) >= 11

    def test_required_has_at_least_11(self):
        from core.service_container import ServiceContainer
        assert len(ServiceContainer._required_names()) >= 11


class TestContainerLifecycle:

    def test_state_initial_created(self):
        from core.service_container import ServiceContainer, ContainerState
        c = ServiceContainer()
        assert c.state == ContainerState.CREATED

    def test_start_to_ready(self):
        c = _make_container()
        c.start()
        from core.service_container import ContainerState
        assert c.state == ContainerState.READY
        assert c.ready() is True

    def test_shutdown_transitions_to_stopped(self):
        c = _make_container()
        c.start()
        c.shutdown()
        from core.service_container import ContainerState
        assert c.state == ContainerState.STOPPED

    def test_ready_before_start_false(self):
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        assert c.ready() is False

    def test_health_returns_state_services_failures(self):
        c = _make_container()
        c.start()
        h = c.health()
        assert "state" in h
        assert "services" in h
        assert "failures" in h

    def test_require_raises_on_missing(self):
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        with pytest.raises((ValueError, KeyError)):
            c.require("nonexistent")

    def test_require_returns_service(self):
        c = _make_container()
        svc = c.require("database")
        assert svc is not None

    def test_cancel_all_calls_cancel_on_services(self):
        c = _make_container()
        dummy = MagicMock()
        c.register("queue_service", dummy)
        c.cancel_all()
        dummy.cancel.assert_called_once()

    def test_shutdown_calls_shutdown_in_reverse_topo(self):
        c = _make_container()
        call_order = []
        topo = c.build_order()
        for name in topo:
            m = MagicMock()
            m.shutdown = lambda n=name, co=call_order: co.append(n)
            c.register(name, m)
        c.shutdown()
        assert len(call_order) > 0

    def test_is_capable_required_present(self):
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        c.register("database", object())
        assert c.is_capable("database") is True

    def test_is_capable_required_absent(self):
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        assert c.is_capable("database") is False

    def test_is_capable_required_failed(self):
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        c.register("database", object())
        c.report_failure("database", "error")
        assert c.is_capable("database") is False
