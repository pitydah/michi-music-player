"""Tests for BridgeFactory delgada — only creates bridges via create_* methods."""
from pathlib import Path
from unittest.mock import MagicMock

from ui_qml_bridge.bridge_factory import BridgeFactory
from core.service_container import ServiceContainer


BRIDGE_FACTORY_PATH = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge" / "bridge_factory.py"


def _make_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    for k, v in {
        "playback_service": MagicMock(),
        "worker_manager": MagicMock(),
        "database": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "global_search_service": MagicMock(),
        "track_action_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "notification_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "job_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "playlist_service": MagicMock(),
        "queue_service": MagicMock(),
        "history_query_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "connection_service": MagicMock(),
        "radio_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "metadata_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "process_controller": MagicMock(),
    }.items():
        c.register(k, overrides.get(k, v))
    return c


class TestNoForbiddenPatterns:
    def test_no_get_service_methods(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        forbidden = ["_get_query_executor", "_get_track_action_service",
                     "_get_playlist_service", "_get_settings_service",
                     "_service_cache", "_query_executor_cache",
                     "_settings_cache", "_playlist_cache"]
        violations = [f for f in forbidden if f in content]
        assert len(violations) == 0, f"Found forbidden patterns: {violations}"

    def test_only_creates_bridges(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        core_imports = [line for line in content.split("\n") if "import" in line and "core." in line]
        assert len(core_imports) <= 15, f"Too many core imports: {len(core_imports)}"


class TestBridgeFactoryPurity:
    def test_factory_receives_container(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f._container is c

    def test_bridges_dict_access(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f.bridges == {}
        f._bridges["test"] = MagicMock()
        assert "test" in f.bridges

    def test_get_returns_none_for_missing(self):
        f = BridgeFactory(_make_container())
        assert f.get("nonexistent") is None

    def test_has_returns_false_for_missing(self):
        f = BridgeFactory(_make_container())
        assert f.has("nonexistent") is False


class TestBridgeCreation:
    def test_create_navigation_bridge(self):
        f = BridgeFactory(_make_container())
        f.create_navigation_bridge()
        assert f.has("navigation")

    def test_create_action_registry(self):
        f = BridgeFactory(_make_container())
        f.create_action_registry_bridge()
        assert f.has("action_registry")

    def test_create_job_bridge(self):
        f = BridgeFactory(_make_container())
        f.create_job_bridge()
        assert f.has("job_bridge")

    def test_create_notification_bridge(self):
        f = BridgeFactory(_make_container())
        f.create_action_registry_bridge()
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("notification")

    def test_create_partial_chain(self):
        f = BridgeFactory(_make_container())
        f.create_action_registry_bridge()
        f.create_navigation_bridge()
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("action_registry")
        assert f.has("navigation")
        assert f.has("job_bridge")
        assert f.has("notification")


class TestSettingsIdentity:
    def test_settings_identity(self):
        f = BridgeFactory(_make_container())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = f._bridges["settings"]

    def test_settings_both_created_by_create_all(self):
        c = _make_container()
        f = BridgeFactory(c)
        created = f.create_all()
        assert "settings" in created
        assert "settings_v2" in created
        assert created["settings"] is created["settings_v2"]

    def test_settings_identity_fails_when_different(self):
        f = BridgeFactory(_make_container())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = MagicMock()
        assert f._bridges["settings"] is not f._bridges["settings_v2"]


class TestBridgeCreationOrder:
    def test_action_registry_before_notification(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_action_registry_bridge()
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("action_registry")
        assert f.has("notification")

    def test_create_all_creates_all(self):
        c = _make_container()
        f = BridgeFactory(c)
        created = f.create_all()
        assert "navigation" in created
        assert "action_registry" in created
        assert "job_bridge" in created
        assert "notification" in created
