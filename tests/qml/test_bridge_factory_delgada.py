"""Tests for BridgeFactory delgada — no _get_* caches, only creates bridges."""

from pathlib import Path
from unittest.mock import MagicMock

from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle

BRIDGE_FACTORY_PATH = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge" / "bridge_factory.py"


def _make_bundle(**overrides) -> ServiceBundle:
    b = ServiceBundle()
    for k, v in {
        "player_service": MagicMock(),
        "db": MagicMock(),
        "db_connection": MagicMock(),
        "search_engine": MagicMock(),
        "radio_manager": MagicMock(),
        "sync_manager": MagicMock(),
        "michi_link_controller": MagicMock(),
        "home_audio_controller": MagicMock(),
        "snapcast_controller": MagicMock(),
        "disc_service": MagicMock(),
        "worker_manager": MagicMock(),
        "metadata_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "queue_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "notification_service": MagicMock(),
        "action_registry": MagicMock(),
        "history_query_service": MagicMock(),
        "global_search_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "job_service": MagicMock(),
    }.items():
        setattr(b, k, overrides.get(k, v))
    return b


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
    def test_factory_does_not_create_services(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        assert f._services is b

    def test_bridges_dict_access(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        assert f.bridges == {}
        f._bridges["test"] = MagicMock()
        assert "test" in f.bridges

    def test_get_returns_none_for_missing(self):
        f = BridgeFactory(_make_bundle())
        assert f.get("nonexistent") is None

    def test_has_returns_false_for_missing(self):
        f = BridgeFactory(_make_bundle())
        assert f.has("nonexistent") is False


class TestBridgeCreation:
    def test_create_navigation_bridge(self):
        f = BridgeFactory(_make_bundle())
        nav = f._create_navigation()
        assert nav is not None
        assert f.has("navigation")

    def test_create_action_registry(self):
        f = BridgeFactory(_make_bundle())
        ar = f._create_action_registry()
        assert ar is not None
        assert f.has("action_registry")

    def test_create_job_bridge(self):
        f = BridgeFactory(_make_bundle())
        jb = f._create_job_bridge()
        assert jb is not None
        assert f.has("job_bridge")

    def test_create_notification_bridge(self):
        f = BridgeFactory(_make_bundle())
        f._create_action_registry()
        f._create_job_bridge()
        nb = f._create_notification()
        assert nb is not None
        assert f.has("notification")

    def test_create_partial_chain(self):
        f = BridgeFactory(_make_bundle())
        f._create_action_registry()
        f._create_navigation()
        f._create_job_bridge()
        f._create_notification()
        assert f.has("action_registry")
        assert f.has("navigation")
        assert f.has("job_bridge")
        assert f.has("notification")


class TestAssertWiringIdentity:
    def test_settings_identity(self):
        f = BridgeFactory(_make_bundle())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = f._bridges["settings"]
        f._assert_wiring()

    def test_settings_identity_fails(self):
        f = BridgeFactory(_make_bundle())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = MagicMock()
        import pytest
        with pytest.raises(AssertionError, match="must be the same"):
            f._assert_wiring()

    def test_assert_wiring_no_crash_with_empty_bridges(self):
        f = BridgeFactory(_make_bundle())
        f._assert_wiring()


class TestAssertWiringServiceConnections:
    def _make_factory_with_bridges(self, bridge_map: dict):
        b = _make_bundle()
        f = BridgeFactory(b)
        for name, svc_name in bridge_map.items():
            if svc_name is None:
                f._bridges[name] = MagicMock()
            else:
                mock = MagicMock()
                prop_name = svc_name
                setattr(mock, prop_name, getattr(b, prop_name.replace("search_service", "global_search_service"), None))
                f._bridges[name] = mock
        return f

    def test_queue_bridge_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_queue = MagicMock()
        mock_queue.queue_service = b.queue_service
        f._bridges["queue"] = mock_queue
        f._assert_wiring()

    def test_app_queue_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_app = MagicMock()
        mock_app.queue_service = b.queue_service
        f._bridges["app"] = mock_app
        f._assert_wiring()

    def test_devices_sync_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_devices = MagicMock()
        mock_devices.device_sync_service = b.device_sync_service
        f._bridges["devices"] = mock_devices
        f._assert_wiring()

    def test_audio_lab_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_al = MagicMock()
        mock_al.audio_lab_service = b.audio_lab_service
        f._bridges["audio_lab"] = mock_al
        f._assert_wiring()

    def test_notification_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_nb = MagicMock()
        mock_nb.notification_service = b.notification_service
        mock_nb.job_service = b.job_service
        f._bridges["notification"] = mock_nb
        f._assert_wiring()

    def test_notification_job_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_nb = MagicMock()
        mock_nb.notification_service = b.notification_service
        mock_nb.job_service = b.job_service
        f._bridges["notification"] = mock_nb
        f._assert_wiring()

    def test_history_query_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_hb = MagicMock()
        mock_hb.history_query_service = b.history_query_service
        f._bridges["history"] = mock_hb
        f._assert_wiring()

    def test_accessibility_settings_service(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_ab = MagicMock()
        mock_ab.settings_service = b.settings_service
        f._bridges["accessibility"] = mock_ab
        f._assert_wiring()

    def test_all_assertions_pass_together(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        mock_app = MagicMock()
        mock_app.queue_service = b.queue_service
        f._bridges["app"] = mock_app
        mock_queue = MagicMock()
        mock_queue.queue_service = b.queue_service
        f._bridges["queue"] = mock_queue
        mock_al = MagicMock()
        mock_al.audio_lab_service = b.audio_lab_service
        f._bridges["audio_lab"] = mock_al
        mock_devices = MagicMock()
        mock_devices.device_sync_service = b.device_sync_service
        f._bridges["devices"] = mock_devices
        mock_nb = MagicMock()
        mock_nb.notification_service = b.notification_service
        mock_nb.job_service = b.job_service
        f._bridges["notification"] = mock_nb
        mock_hb = MagicMock()
        mock_hb.history_query_service = b.history_query_service
        f._bridges["history"] = mock_hb
        mock_ab = MagicMock()
        mock_ab.settings_service = b.settings_service
        f._bridges["accessibility"] = mock_ab
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = f._bridges["settings"]
        f._assert_wiring()


class TestBridgeCreationOrder:
    def test_action_registry_before_notification(self):
        order = [
            "action_registry", "navigation", "job_bridge", "notification",
            "theme", "accessibility", "playback", "queue", "app", "library",
        ]
        assert order.index("action_registry") < order.index("notification")

    def test_diagnostics_before_michi_ai(self):
        from ui_qml_bridge.bridge_factory import BRIDGE_CREATION_ORDER
        assert BRIDGE_CREATION_ORDER.index("diagnostics") < BRIDGE_CREATION_ORDER.index("michi_ai")
