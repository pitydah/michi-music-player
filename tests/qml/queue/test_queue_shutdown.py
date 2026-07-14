"""Test QueueBridge shutdown restores queue state via QueueService."""
import os
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.queue_bridge import QueueBridge, _queue_state_path
from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_queue = MagicMock(return_value=[
        {"id": 1, "track_uid": "uid1", "title": "T1", "artist": "A",
         "album": "Al", "duration": 200, "filepath": "/p1.flac"},
    ])
    player.play_index = MagicMock()
    player.remove_from_queue = MagicMock()
    return player


def test_queue_bridge_has_queue_service(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    assert hasattr(bridge, 'queue_service')
    assert bridge.queue_service is not None


def test_app_bridge_uses_queue_service_for_shutdown(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    app = AppBridge(
        queue_bridge=bridge,
        worker_manager=MagicMock(),
        query_executor=MagicMock(),
        player_service=mock_player,
        sync_manager=MagicMock(),
        home_audio_controller=MagicMock(),
        radio_manager=MagicMock(),
        discovery=MagicMock(),
        db=MagicMock(),
    )
    app.quit()
    assert os.path.exists(_queue_state_path())
    os.remove(_queue_state_path())


def test_factory_creates_queue_bridge_with_service():
    bundle = ServiceBundle()
    bundle.player_service = MagicMock()
    bundle.worker_manager = MagicMock()
    bundle.db = MagicMock()
    factory = BridgeFactory(bundle)
    bridge = factory.create_queue_bridge()
    assert bridge is not None
    assert hasattr(bridge, 'queue_service')


def test_shutdown_with_queue_persistence(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    bridge.queue_service.shutdown()
    assert os.path.exists(_queue_state_path())
    os.remove(_queue_state_path())


def test_queue_service_closes_cleanly(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    bridge.queue_service.shutdown()
    assert os.path.exists(_queue_state_path())
    os.remove(_queue_state_path())
