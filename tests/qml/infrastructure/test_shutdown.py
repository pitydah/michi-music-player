from __future__ import annotations

from unittest.mock import MagicMock

from ui_qml_bridge.app_bridge import AppBridge


def _make_bridge(services: list | None = None) -> AppBridge:
    bridge = AppBridge()
    if services:
        bridge.receive_services(*services)
    return bridge


class TestAppBridgeShutdown:
    def test_shutdown_sets_phase(self):
        bridge = _make_bridge()
        bridge.quit()
        assert bridge._shutting_down is True

    def test_shutdown_is_idempotent(self):
        bridge = _make_bridge()
        bridge.quit()
        bridge.quit()
        assert bridge._shutdown_executed is True

    def test_shutdown_stops_accepting(self):
        bridge = _make_bridge()
        bridge.quit()
        assert bridge._accepting_new is False

    def test_shutdown_calls_service_shutdown(self):
        svc = MagicMock()
        bridge = _make_bridge([svc])
        bridge.quit()
        svc.shutdown.assert_called()

    def test_shutdown_handles_service_exception(self):
        svc = MagicMock()
        svc.shutdown.side_effect = RuntimeError("fail")
        bridge = _make_bridge([svc])
        bridge.quit()
        assert bridge._shutting_down is True

    def test_shutdown_includes_all_services(self):
        svc1 = MagicMock()
        svc2 = MagicMock()
        bridge = _make_bridge([svc1, svc2])
        bridge.quit()
        svc1.shutdown.assert_called()
        svc2.shutdown.assert_called()

    def test_multiple_quit_idempotent(self):
        bridge = _make_bridge()
        bridge.quit()
        assert bridge._shutdown_executed is True

    def test_shutdown_results_stored(self):
        bridge = _make_bridge()
        bridge.quit()
        assert hasattr(bridge, '_shutdown_results')
        assert len(bridge._shutdown_results) >= 14

    def test_shutdown_steps_have_step_key(self):
        bridge = _make_bridge()
        bridge.quit()
        for r in bridge._shutdown_results:
            assert "step" in r
            assert "ok" in r
            assert "duration_s" in r

    def test_shutdown_sets_phase_stopped(self):
        bridge = _make_bridge()
        bridge.quit()
        assert bridge._phase == AppBridge.STOPPED
