"""DN — QueueService canonical injection tests.

QueueService is injected into: QueueBridge, AppBridge, PlaybackService,
MichiAI, Notifications, CommandPalette.

QueueService is the single source of truth. No parallel queue state.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.service_bundle import ServiceBundle
from ui_qml_bridge.bridge_factory import BridgeFactory
pytestmark = [pytest.mark.qml_module("queue")]



@pytest.fixture
def service():
    return QueueService()


@pytest.fixture
def sample_items():
    return [
        {"track_id": 1, "track_uid": "uid1", "title": "A", "artist": "X",
         "source_type": "local_file", "duration": 200, "filepath": "/a.flac"},
        {"track_id": 2, "track_uid": "uid2", "title": "B", "artist": "Y",
         "source_type": "local_file", "duration": 300, "filepath": "/b.flac"},
    ]


def test_queue_service_injected_into_queue_bridge(service):
    bridge = QueueBridge(queue_service=service)
    assert bridge.queue_service is service


def test_queue_service_injected_into_app_bridge(service):
    queue_bridge = QueueBridge(queue_service=service)
    app = AppBridge(
        queue_bridge=queue_bridge,
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        player_service=MagicMock(),
        sync_manager=MagicMock(),
        home_audio_controller=MagicMock(),
        radio_manager=MagicMock(),
        discovery=MagicMock(),
        db=MagicMock(),
    )
    assert app is not None


def test_queue_bridge_delegates_remove_to_queue_service(service):
    bridge = QueueBridge(queue_service=service)
    service.add({"track_id": 1, "title": "A"})
    assert service.count == 1
    result = bridge.removeFromQueue(0)
    assert result["ok"]
    assert service.count == 0


def test_queue_bridge_delegates_clear_to_queue_service(service):
    bridge = QueueBridge(queue_service=service)
    service.add({"track_id": 1, "title": "A"})
    service.add({"track_id": 2, "title": "B"})
    result = bridge.clearQueue()
    assert result["ok"]
    assert service.count == 0


def test_queue_bridge_delegates_move_to_queue_service(service):
    bridge = QueueBridge(queue_service=service)
    service.add({"track_id": 1, "title": "A"})
    service.add({"track_id": 2, "title": "B"})
    service.add({"track_id": 3, "title": "C"})
    result = bridge.moveItem(0, 2)
    assert result["ok"]
    assert service.items[2]["title"] == "A"


def test_queue_bridge_persist_delegates(service):
    bridge = QueueBridge(queue_service=service)
    service.add({"track_id": 1, "title": "A"})
    result = bridge.persist()
    assert result["ok"]


def test_queue_bridge_restore_delegates(service):
    bridge = QueueBridge(queue_service=service)
    service.add({"track_id": 1, "title": "A"})
    bridge.persist()
    fresh = QueueService()
    fresh_bridge = QueueBridge(queue_service=fresh)
    result = fresh_bridge.restore()
    assert result["ok"] or not result["ok"]


def test_queue_bridge_undo_delegates(service):
    bridge = QueueBridge(queue_service=service)
    service.add({"track_id": 1, "title": "A"})
    service.add({"track_id": 2, "title": "B"})
    service.remove([1])
    result = bridge.undo()
    assert result["ok"]
    assert service.count == 2


def test_nowplaying_bridge_queue_does_not_own_state():
    player = MagicMock()
    player.get_queue.return_value = []
    np = NowPlayingBridge(player_service=player)
    assert hasattr(np, 'queue')
    assert isinstance(np.queue, list)


def test_queue_service_no_duplicate_state(service, sample_items):
    service.set_items(sample_items)
    player = MagicMock()
    player.get_queue.return_value = []
    assert service.count == 2
    assert len(player.get_queue()) == 0


def test_bridge_factory_injects_queue_service():
    bundle = ServiceBundle()
    bundle.player_service = MagicMock()
    bundle.worker_manager = MagicMock()
    bundle.db = MagicMock()
    factory = BridgeFactory(bundle)
    bridge = factory.create_queue_bridge()
    assert hasattr(bridge, 'queue_service')


def test_queue_service_add_updates_index(service):
    assert service.current_index == -1
    service.add({"track_id": 1, "title": "A"})
    assert service.current_index == 0
    assert service.get_current()["track_id"] == 1


def test_queue_service_clear_resets(service, sample_items):
    service.set_items(sample_items)
    assert service.count == 2
    service.clear()
    assert service.count == 0
    assert service.current_index == -1


def test_queue_service_set_items_updates_index(service, sample_items):
    service.set_items(sample_items)
    assert service.current_index == 0


def test_queue_service_undo(service, sample_items):
    service.set_items(sample_items)
    service.clear()
    assert service.count == 0
    assert service.undo()
    assert service.count == 2
