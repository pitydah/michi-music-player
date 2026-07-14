"""Tests for ApplicationBootstrap productive lifecycle."""
from __future__ import annotations

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
        "core.library_doctor.repositories": MagicMock(),
        "core.library_doctor.repositories.scan_repository": MagicMock(),
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


def _make_app_bootstrap():
    from core.application_bootstrap import ApplicationBootstrap
    return ApplicationBootstrap()


class TestApplicationBootstrapBuild:
    def test_build_returns_self(self):
        bootstrap = _make_app_bootstrap()
        result = bootstrap.build()
        assert result is bootstrap

    def test_build_is_idempotent(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        assert bootstrap._has_built
        bootstrap.build()
        assert bootstrap._has_built

    def test_start_returns_self(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        result = bootstrap.start()
        assert result is bootstrap

    def test_start_is_idempotent(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        bootstrap.start()
        assert bootstrap._has_started
        bootstrap.start()
        assert bootstrap._has_started

    def test_shutdown_resets_state(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        bootstrap.start()
        bootstrap.shutdown()
        assert not bootstrap._has_built
        assert not bootstrap._has_started

    def test_full_lifecycle(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        bootstrap.start()
        assert bootstrap.container.ready()
        bootstrap.shutdown()

    @patch("ui_qml_bridge.bridge_factory.create_all_bridges", return_value={"app": MagicMock(), "navigation": MagicMock()})
    def test_register_qml_creates_context_properties(self, mock_create):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        bridges = bootstrap.create_bridges()
        assert "app" in bridges
        bootstrap.start()
        mock_engine = MagicMock()
        mock_engine.rootContext().contextProperty.return_value = None
        bootstrap.register_qml(mock_engine)
        assert mock_engine.rootContext().setContextProperty.called

    @patch("ui_qml_bridge.bridge_factory.create_all_bridges", return_value={"app": MagicMock(), "navigation": MagicMock()})
    def test_create_bridges_returns_dict(self, mock_create):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        bridges = bootstrap.create_bridges()
        assert isinstance(bridges, dict)

    def test_get_queue_service_after_build(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        qs = bootstrap.get_queue_service()
        assert qs is not None

    def test_get_worker_manager_after_build(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        wm = bootstrap.get_worker_manager()
        assert wm is not None

    def test_get_query_executor_after_build(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        qe = bootstrap.get_query_executor()
        assert qe is not None

    @patch("ui_qml_bridge.bridge_factory.create_all_bridges", return_value={})
    def test_run_full_flow(self, mock_create):
        bootstrap = _make_app_bootstrap()
        with patch.object(bootstrap, "register_qml"):
            bootstrap.run()
            assert bootstrap._has_built
            assert bootstrap._has_started

    @patch("ui_qml_bridge.bridge_factory.create_all_bridges", return_value={"app": MagicMock(), "navigation": MagicMock(), "theme": MagicMock(), "library": MagicMock()})
    def test_create_bridges_registers_bridge_objects(self, mock_create):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        bridges = bootstrap.create_bridges()
        for name in ("app", "navigation", "theme", "library"):
            assert name in bridges, f"Missing bridge: {name}"

    def test_shutdown_calls_container_shutdown(self):
        bootstrap = _make_app_bootstrap()
        bootstrap.build()
        with patch.object(bootstrap.container, "shutdown") as mock_shutdown:
            bootstrap.shutdown()
            mock_shutdown.assert_called_once()


class TestApplicationBootstrapBuildSteps:
    def test_build_config_registers_settings_manager(self):
        bootstrap = _make_app_bootstrap()
        bootstrap._build_config()
        assert bootstrap.container.get("settings_manager") is not None

    def test_build_workers_registers_worker_manager(self):
        bootstrap = _make_app_bootstrap()
        bootstrap._build_workers()
        assert bootstrap.container.get("worker_manager") is not None

    def test_build_action_registry_actions(self):
        bootstrap = _make_app_bootstrap()
        bootstrap._build_workers()
        bootstrap._build_domain_services()
        bootstrap._build_action_registry()
        ar = bootstrap.container.get("action_registry")
        assert ar is not None

    def test_build_domain_services_registers_queue(self):
        bootstrap = _make_app_bootstrap()
        bootstrap._build_workers()
        bootstrap._build_domain_services()
        assert bootstrap.container.get("queue_service") is not None

    def test_build_domain_services_registers_notification(self):
        bootstrap = _make_app_bootstrap()
        bootstrap._build_workers()
        bootstrap._build_domain_services()
        ns = bootstrap.container.get("notification_service")
        assert ns is not None

    def test_build_domain_services_registers_audio_lab(self):
        bootstrap = _make_app_bootstrap()
        bootstrap._build_workers()
        bootstrap._build_domain_services()
        svc = bootstrap.container.get("audio_lab_service")
        assert svc is not None
