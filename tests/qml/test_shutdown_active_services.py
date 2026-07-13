"""Test shutdown sequence with actively running services."""
import time
from unittest.mock import MagicMock

from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle


def _make_bundle_with_active_tasks() -> ServiceBundle:
    bundle = ServiceBundle()
    bundle.worker_manager = MagicMock()
    bundle.worker_manager.active_tasks.return_value = [
        {"task_id": "task_1", "state": "running"},
        {"task_id": "task_2", "state": "queued"},
    ]
    bundle.query_executor = MagicMock()
    bundle.query_executor.active_requests.return_value = [1, 2, 3]
    bundle.player_service = MagicMock()
    bundle.player_service.stop = MagicMock()
    bundle.sync_manager = MagicMock()
    bundle.sync_manager.stop = MagicMock()
    bundle.home_audio_controller = MagicMock()
    bundle.home_audio_controller.stop = MagicMock()
    bundle.radio_manager = MagicMock()
    bundle.radio_manager.stop = MagicMock()
    bundle.db = MagicMock()
    bundle.db.close = MagicMock()
    bundle.search_engine = MagicMock()
    bundle.michi_link_controller = MagicMock()
    bundle.snapcast_controller = MagicMock()
    bundle.disc_service = MagicMock()
    bundle.smart_tagging_service = MagicMock()
    bundle.metadata_service = MagicMock()
    bundle.playlist_controller = MagicMock()
    return bundle


def test_shutdown_with_active_queryexecutor_requests():
    qe = MagicMock()
    qe.active_requests.return_value = [1, 2]
    bridge = AppBridge(
        worker_manager=MagicMock(),
        query_executor=qe,
        player_service=MagicMock(),
        queue_bridge=MagicMock(),
        sync_manager=MagicMock(),
        home_audio_controller=MagicMock(),
        radio_manager=MagicMock(),
        discovery=MagicMock(),
        db=MagicMock(),
    )
    bridge.quit()
    qe.shutdown.assert_called_once()


def test_shutdown_cancels_active_worker_tasks():
    wm = MagicMock()
    wm.active_tasks.return_value = [
        {"task_id": "scan_1", "state": "running"},
        {"task_id": "meta_2", "state": "queued"},
    ]
    bridge = AppBridge(
        worker_manager=wm,
        query_executor=MagicMock(),
        player_service=MagicMock(),
        queue_bridge=MagicMock(),
        sync_manager=MagicMock(),
        home_audio_controller=MagicMock(),
        radio_manager=MagicMock(),
        discovery=MagicMock(),
        db=MagicMock(),
    )
    bridge.quit()
    wm.cancel_all.assert_called_once()
    wm.shutdown.assert_called_once()


def test_factory_creates_app_bridge_with_lifecycle():
    bundle = _make_bundle_with_active_tasks()
    factory = BridgeFactory(bundle)
    factory.create_navigation_bridge()
    factory.create_queue_bridge()
    bridge = factory.create_app_bridge()
    assert bridge is not None
    assert hasattr(bridge, 'phase')
    assert hasattr(bridge, 'setReady')
    assert hasattr(bridge, 'quit')


def test_factory_app_bridge_has_debug_info():
    bundle = _make_bundle_with_active_tasks()
    factory = BridgeFactory(bundle)
    factory.create_navigation_bridge()
    factory.create_queue_bridge()
    bridge = factory.create_app_bridge()
    info = bridge.appScore()
    assert "score" in info
    assert "has_worker_manager" in info
    assert "has_query_executor" in info


def test_full_shutdown_through_factory():
    bundle = _make_bundle_with_active_tasks()
    factory = BridgeFactory(bundle)
    factory.create_navigation_bridge()
    factory.create_queue_bridge()
    bridge = factory.create_app_bridge()
    bridge.setReady()
    assert bridge.ready
    bridge.quit()
    assert bridge._shutting_down
    assert not bridge._accepting_new


def test_shutdown_with_timing():
    wm = MagicMock()
    # Simulate slow shutdown
    def slow_shutdown(ms):
        time.sleep(0.01)
    wm.shutdown.side_effect = slow_shutdown
    bridge = AppBridge(
        worker_manager=wm,
        query_executor=MagicMock(),
        player_service=MagicMock(),
        queue_bridge=MagicMock(),
        sync_manager=MagicMock(),
        home_audio_controller=MagicMock(),
        radio_manager=MagicMock(),
        discovery=MagicMock(),
        db=MagicMock(),
    )
    import time as t
    start = t.time()
    bridge.quit()
    elapsed = t.time() - start
    assert elapsed < 5.0, "Shutdown took too long"
    wm.shutdown.assert_called_once()
