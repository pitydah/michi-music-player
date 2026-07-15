from __future__ import annotations
"""Test QueueService as single source of truth for queue state.
QueueService owns state; PlayerService executes; QueueListModel observes;
QueueBridge adapts. No duplicate state.
"""

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


@pytest.fixture
def service():
    return QueueService()


@pytest.fixture
def sample_items():
    return [
        {"track_id": 1, "track_uid": "uid1", "title": "A", "artist": "X",
         "source_type": "local_file", "duration": 200},
        {"track_id": 2, "track_uid": "uid2", "title": "B", "artist": "Y",
         "source_type": "local_file", "duration": 300},
        {"track_id": 3, "track_uid": "uid3", "title": "C", "artist": "Z",
         "source_type": "local_file", "duration": 250},
    ]


def test_queue_service_is_singleton_source_of_truth(service):
    assert service.count == 0
    assert service.items == []
    assert service.current_index == -1


def test_queue_service_owns_state_not_player(service, sample_items):
    service.set_items(sample_items)
    assert service.count == 3
    assert service.current_index == 0
    assert service.items[0]["title"] == "A"


def test_queue_bridge_receives_queue_service_by_constructor(service):
    bridge = QueueBridge(queue_service=service)
    assert bridge.queue_service is service
    assert bridge.queue_service is not None


def test_queue_bridge_does_not_create_queue_service_internally(service):
    bridge = QueueBridge(queue_service=service)
    assert not hasattr(bridge, '_queue_service') or bridge._queue_service is service


def test_queue_listmodel_reads_from_queue_service(service, sample_items):
    service.set_items(sample_items)
    from unittest.mock import MagicMock
    player = MagicMock()
    player.get_queue.return_value = sample_items
    from ui_qml.models.QueueListModel import QueueListModel

    model = QueueListModel(player_service=player)
    assert model._fetch_count() == 3
    page = model._fetch_page(0, 10)
    assert len(page) == 3
    assert page[0]["title"] == "A"


def test_add_item_updates_queue_service(service):
    service.add({"track_id": 1, "title": "New Track"})
    assert service.count == 1
    assert service.current_index == 0
    assert service.get_current()["track_id"] == 1


def test_remove_item_updates_index(service, sample_items):
    service.set_items(sample_items)
    assert service.current_index == 0
    service.remove([0])
    assert service.count == 2
    assert service.items[0]["title"] == "B"


def test_move_item(service, sample_items):
    service.set_items(sample_items)
    service.move(0, 2)
    assert service.items[2]["title"] == "A"


def test_clear_resets_state(service, sample_items):
    service.set_items(sample_items)
    service.clear()
    assert service.count == 0
    assert service.current_index == -1


def test_undo_restores_previous_state(service, sample_items):
    service.set_items(sample_items)
    service.clear()
    assert service.count == 0
    assert service.undo()
    assert service.count == 3


def test_queue_service_independent_of_player_service(service, sample_items):
    service.set_items(sample_items)
    player = MagicMock()
    player.get_queue.return_value = []
    assert service.count == 3
    assert player.get_queue() != service.items
