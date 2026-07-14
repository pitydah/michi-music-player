"""Tests for BridgeFactory _assert_wiring — pure assertions, no service creation."""

from unittest.mock import MagicMock

from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle


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
    }.items():
        setattr(b, k, overrides.get(k, v))
    return b


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
    def test_app_queue_service(self):
        b = _make_bundle()
        b.queue_service = MagicMock()
        f = BridgeFactory(b)
        mock_app = MagicMock()
        mock_app.queue_service = b.queue_service
        f._bridges["app"] = mock_app
        f._assert_wiring()

    def test_queue_bridge_service(self):
        b = _make_bundle()
        b.queue_service = MagicMock()
        f = BridgeFactory(b)
        mock_queue = MagicMock()
        mock_queue.queue_service = b.queue_service
        f._bridges["queue"] = mock_queue
        f._assert_wiring()

    def test_audio_lab_service(self):
        b = _make_bundle()
        b.audio_lab_service = MagicMock()
        f = BridgeFactory(b)
        mock_audio_lab = MagicMock()
        mock_audio_lab.audio_lab_service = b.audio_lab_service
        f._bridges["audio_lab"] = mock_audio_lab
        f._assert_wiring()

    def test_devices_sync_service(self):
        b = _make_bundle()
        b.device_sync_service = MagicMock()
        f = BridgeFactory(b)
        mock_devices = MagicMock()
        mock_devices.device_sync_service = b.device_sync_service
        f._bridges["devices"] = mock_devices
        f._assert_wiring()

    def test_notification_service(self):
        b = _make_bundle()
        b.notification_service = MagicMock()
        b.action_registry = MagicMock()
        f = BridgeFactory(b)
        mock_notif = MagicMock()
        mock_notif.notification_service = b.notification_service
        mock_notif.action_registry = b.action_registry
        f._bridges["notification"] = mock_notif
        f._assert_wiring()

    def test_notification_action_registry(self):
        b = _make_bundle()
        b.notification_service = MagicMock()
        b.action_registry = MagicMock()
        f = BridgeFactory(b)
        mock_notif = MagicMock()
        mock_notif.notification_service = b.notification_service
        mock_notif.action_registry = b.action_registry
        f._bridges["notification"] = mock_notif
        f._assert_wiring()

    def test_history_query_service(self):
        b = _make_bundle()
        b.history_query_service = MagicMock()
        f = BridgeFactory(b)
        mock_history = MagicMock()
        mock_history.history_query_service = b.history_query_service
        f._bridges["history"] = mock_history
        f._assert_wiring()

    def test_global_search_service(self):
        b = _make_bundle()
        b.global_search_service = MagicMock()
        f = BridgeFactory(b)
        mock_gs = MagicMock()
        mock_gs.search_service = b.global_search_service
        f._bridges["global_search"] = mock_gs
        f._assert_wiring()

    def test_michi_ai_diagnostics_service(self):
        b = _make_bundle()
        b.diagnostics_service = MagicMock()
        f = BridgeFactory(b)
        mock_michi = MagicMock()
        mock_michi.diagnostics_service = b.diagnostics_service
        f._bridges["michi_ai"] = mock_michi
        f._assert_wiring()

    def test_all_assertions_pass_together(self):
        b = _make_bundle()
        for svc_name in ["queue_service", "audio_lab_service", "device_sync_service",
                         "notification_service", "action_registry", "history_query_service",
                         "global_search_service", "diagnostics_service"]:
            setattr(b, svc_name, MagicMock())
        f = BridgeFactory(b)

        mock_app = MagicMock()
        mock_app.queue_service = b.queue_service
        f._bridges["app"] = mock_app

        mock_queue = MagicMock()
        mock_queue.queue_service = b.queue_service
        f._bridges["queue"] = mock_queue

        mock_audio_lab = MagicMock()
        mock_audio_lab.audio_lab_service = b.audio_lab_service
        f._bridges["audio_lab"] = mock_audio_lab

        mock_devices = MagicMock()
        mock_devices.device_sync_service = b.device_sync_service
        f._bridges["devices"] = mock_devices

        mock_notif = MagicMock()
        mock_notif.notification_service = b.notification_service
        mock_notif.action_registry = b.action_registry
        f._bridges["notification"] = mock_notif

        mock_history = MagicMock()
        mock_history.history_query_service = b.history_query_service
        f._bridges["history"] = mock_history

        mock_gs = MagicMock()
        mock_gs.search_service = b.global_search_service
        f._bridges["global_search"] = mock_gs

        mock_michi = MagicMock()
        mock_michi.diagnostics_service = b.diagnostics_service
        f._bridges["michi_ai"] = mock_michi

        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = f._bridges["settings"]
        f._assert_wiring()
