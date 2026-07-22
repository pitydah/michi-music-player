from __future__ import annotations
"""Test QueueService as single source of truth for queue state.
QueueService owns state; PlayerService executes; QueueListModel observes;
QueueBridge adapts. No duplicate state.
"""

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml.models.QueueListModel import QueueListModel

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
    bridge = QueueBridge(player_service=MagicMock(), queue_service=service)
    assert bridge.queue_service is service
    assert bridge.queue_service is not None


def test_queue_bridge_does_not_create_queue_service_internally(service):
    bridge = QueueBridge(player_service=MagicMock(), queue_service=service)
    assert not hasattr(bridge, '_queue_service') or bridge._queue_service is service


def test_queue_listmodel_reads_from_queue_service(service, sample_items):
    service.set_items(sample_items)
    from ui_qml.models.QueueListModel import QueueListModel

    model = QueueListModel(queue_service=service)
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


def test_canonical_queue_drives_model_playback_and_restore(tmp_path, monkeypatch):
    state_path = tmp_path / "queue_state.json"
    monkeypatch.setattr("core.queue_service._queue_state_path", lambda: str(state_path))
    player = MagicMock()
    service = QueueService(player_service=player)
    bridge = QueueBridge(player_service=player, queue_service=service)
    items = [
        {"track_id": 1, "title": "A", "filepath": "/music/a.flac"},
        {"track_id": 2, "title": "B", "filepath": "/music/b.flac"},
        {"track_id": 3, "title": "C", "filepath": "/music/c.flac"},
    ]

    service.enqueue(items)
    bridge.refresh()
    assert bridge.queueCount == 3
    player.get_queue.assert_not_called()
    player.play_queue.assert_called()
    assert bridge.moveItem(0, 2)["ok"]
    assert bridge.playFromIndex(1)["ok"]
    player.play.assert_called_once_with(
        "/music/c.flac",
        "C",
        "",
        "",
    )
    assert service.get_current()["title"] == "C"
    assert bridge.removeFromQueue(0)["ok"]
    assert [item["title"] for item in service.items] == ["C", "A"]
    assert service.current_index == 0
    assert bridge.persist()["ok"]

    restored_player = MagicMock()
    restored = QueueService(player_service=restored_player)
    restored_bridge = QueueBridge(
        player_service=restored_player,
        queue_service=restored,
    )
    assert restored_bridge.restore()["ok"]
    assert restored_bridge.queueCount == 2
    assert [item["title"] for item in restored.items] == ["C", "A"]
    assert restored.current_index == 0


def _navigation_service(repeat="none"):
    player = MagicMock()
    service = QueueService(player_service=player)
    service.repeat = repeat
    service.enqueue([
        {"track_id": 1, "title": "A", "filepath": "/music/a.flac"},
        {"track_id": 2, "title": "B", "filepath": "/music/b.flac"},
        {"track_id": 3, "title": "C", "filepath": "/music/c.flac"},
    ])
    return service, player


def test_next_and_previous_execute_current_track():
    service, player = _navigation_service()

    assert service.next()["ok"]
    assert service.current_index == 1
    player.play.assert_called_with("/music/b.flac", "B", "", "")
    assert service.previous()["ok"]
    assert service.current_index == 0
    player.play.assert_called_with("/music/a.flac", "A", "", "")


def test_navigation_boundaries_and_empty_queue():
    empty = QueueService(player_service=MagicMock())
    assert empty.next()["error"] == "EMPTY_QUEUE"
    assert empty.previous()["error"] == "EMPTY_QUEUE"
    assert empty.play_from_index(0)["error"] == "EMPTY_QUEUE"

    service, _player = _navigation_service()
    assert service.previous()["error"] == "START_OF_QUEUE"
    service.current_index = 2
    assert service.next()["error"] == "END_OF_QUEUE"
    assert service.play_from_index(10)["error"] == "INVALID_INDEX"


def test_repeat_all_wraps_in_both_directions():
    service, player = _navigation_service(repeat="all")
    service.current_index = 2

    assert service.next()["ok"]
    assert service.current_index == 0
    assert service.previous()["ok"]
    assert service.current_index == 2
    assert player.play.call_count == 2


def test_enqueue_next_inserts_without_advancing():
    service, _player = _navigation_service()
    service.current_index = 1

    result = service.enqueue_next(
        {"track_id": 4, "title": "D", "filepath": "/music/d.flac"}
    )

    assert result["ok"]
    assert [item["title"] for item in service.items] == ["A", "B", "D", "C"]
    assert service.current_index == 1


def test_queue_model_marks_current_position_from_service():
    service, _player = _navigation_service()
    service.current_index = 1
    model = QueueListModel(queue_service=service)

    page = model._fetch_page(0, 10)

    assert [item["is_current"] for item in page] == [False, True, False]


def test_backend_sync_and_execution_errors_are_structured():
    service, player = _navigation_service()
    player.play_queue.side_effect = RuntimeError("queue sync failed")

    sync_result = service.enqueue_next(
        {"track_id": 4, "title": "D", "filepath": "/music/d.flac"}
    )

    assert sync_result["error"] == "BACKEND_SYNC_FAILED"
    assert "queue sync failed" in sync_result["message"]

    player.play_queue.side_effect = None
    player.play.side_effect = RuntimeError("play failed")
    play_result = service.play_from_index(0)
    assert play_result["error"] == "BACKEND_SYNC_FAILED"
    assert "play failed" in play_result["message"]
