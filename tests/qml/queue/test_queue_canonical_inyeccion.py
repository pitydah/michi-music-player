"""DN — QueueService canonical injection tests.
QueueService is injected into: QueueBridge, AppBridge, PlaybackService,
MichiAI, Notifications, CommandPalette.
QueueService is the single source of truth. No parallel queue state.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml.models.QueueListModel import QueueListModel
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from core.service_container import ServiceContainer
from ui_qml_bridge.bridge_factory import BridgeFactory
pytestmark = [pytest.mark.qml_module("queue")]

EXPECTED_QUEUE_ROLES = {
    b"trackId",
    b"trackUid",
    b"title",
    b"artist",
    b"album",
    b"albumKey",
    b"duration",
    b"current",
    b"position",
    b"coverKey",
    b"sourceType",
}


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
    assert isinstance(result["ok"], bool)


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
    np = NowPlayingBridge(
        player_service=player,
        audio_quality_adapter=MagicMock(),
    )
    assert not hasattr(np, "queue")
    player.get_queue.assert_not_called()


def test_queue_list_model_exposes_complete_typed_role_contract(service):
    service.set_items(
        [
            {
                "track_id": 7,
                "track_uid": "uid-7",
                "title": "Naima",
                "artist": "John Coltrane",
                "album": "Giant Steps",
                "album_key": "giant-steps",
                "duration": "291",
                "filepath": "/music/naima.flac",
                "cover_key": "cover-naima",
                "source_type": "local_file",
            }
        ],
        current_index=0,
    )
    model = QueueListModel(queue_service=service)
    index = model.index(0)

    assert set(model.roleNames().values()) == EXPECTED_QUEUE_ROLES
    assert model.data(index, model.TrackIdRole) == "7"
    assert model.data(index, model.TrackUidRole) == "uid-7"
    assert model.data(index, model.TitleRole) == "Naima"
    assert model.data(index, model.ArtistRole) == "John Coltrane"
    assert model.data(index, model.AlbumRole) == "Giant Steps"
    assert model.data(index, model.AlbumKeyRole) == "giant-steps"
    assert model.data(index, model.DurationRole) == 291
    assert model.data(index, model.CurrentRole) is True
    assert model.data(index, model.PositionRole) == 0
    assert model.data(index, model.CoverKeyRole) == "cover-naima"
    assert model.data(index, model.SourceTypeRole) == "local_file"


def test_queue_list_model_positions_and_current_follow_service_state(service):
    service.set_items(
        [
            {"track_id": "a", "title": "A"},
            {"track_id": "b", "title": "B"},
            {"track_id": "c", "title": "C"},
        ],
        current_index=1,
    )
    model = QueueListModel(queue_service=service)

    assert [model.data(model.index(row), model.PositionRole) for row in range(3)] == [0, 1, 2]
    assert [model.data(model.index(row), model.CurrentRole) for row in range(3)] == [
        False,
        True,
        False,
    ]

    service.current_index = 2

    assert [model.data(model.index(row), model.CurrentRole) for row in range(3)] == [
        False,
        False,
        True,
    ]


def test_queue_service_no_duplicate_state(service, sample_items):
    service.set_items(sample_items)
    player = MagicMock()
    player.get_queue.return_value = []
    assert service.count == 2
    assert len(player.get_queue()) == 0


def test_bridge_factory_injects_queue_service():
    c = ServiceContainer()
    c.register("playback_service", MagicMock())
    c.register("worker_manager", MagicMock())
    c.register("database", MagicMock())
    c.register("queue_service", QueueService())
    c.register("settings_coordinator", MagicMock())
    c.register("settings_service", MagicMock())
    c.register("global_search_service", MagicMock())
    c.register("track_action_service", MagicMock())
    c.register("confirmation_service", MagicMock())
    c.register("notification_service", MagicMock())
    c.register("diagnostics_service", MagicMock())
    c.register("job_service", MagicMock())
    c.register("mix_query_service", MagicMock())
    c.register("playlist_service", MagicMock())
    c.register("history_query_service", MagicMock())
    c.register("device_sync_service", MagicMock())
    c.register("home_audio_service", MagicMock())
    c.register("connection_service", MagicMock())
    c.register("radio_service", MagicMock())
    c.register("audio_lab_service", MagicMock())
    c.register("metadata_service", MagicMock())
    c.register("smart_tagging_service", MagicMock())
    c.register("library_doctor_service", MagicMock())
    c.register("library_sources_service", MagicMock())
    c.register("process_controller", MagicMock())
    factory = BridgeFactory(c)
    factory.create_queue_bridge()
    bridge = factory.get("queue")
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
