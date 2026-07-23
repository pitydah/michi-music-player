"""Test playback-queue workflow: Library click QueueService PlayerService.
QueueService owns state; PlayerService executes; NowPlayingBridge reflects
PlayerService (no duplicate state); QueueBridge adapts QueueService.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

pytestmark = [pytest.mark.qml_module("playback")]

QML_PAGES = Path(__file__).parents[3] / "ui_qml" / "pages"


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_queue.return_value = []
    player.current = None
    player.state = "stopped"
    player.duration = 0
    player.get_track_by_id.return_value = None
    return player


@pytest.fixture
def queue_service(mock_player):
    return QueueService(player_service=mock_player)


@pytest.fixture
def queue_bridge(queue_service, mock_player):
    return QueueBridge(queue_service=queue_service, player_service=mock_player)


@pytest.fixture
def nowplaying_bridge(mock_player, queue_service, audio_quality_adapter):
    bridge = NowPlayingBridge(
        player_service=mock_player,
        queue_service=queue_service,
        audio_quality_adapter=audio_quality_adapter,
    )
    return bridge


def test_library_add_to_queue_via_queue_service(queue_service, mock_player):
    track = {"track_id": 1, "title": "Song", "artist": "Artist",
             "album": "Album", "source_type": "local_file", "duration": 200}
    queue_service.add(track)
    assert queue_service.count == 1
    assert queue_service.get_current()["track_id"] == 1


def test_queue_service_add_syncs_to_player(queue_service, mock_player):
    mock_player.set_queue = MagicMock()
    queue_service = QueueService(player_service=mock_player)
    track = {"track_id": 1, "title": "Song", "artist": "Artist"}
    queue_service.add(track)
    assert queue_service.count == 1
    mock_player.set_queue.assert_called_once()


def test_nowplaying_bridge_has_no_duplicate_control_logic(nowplaying_bridge):
    assert nowplaying_bridge is not None
    assert not hasattr(nowplaying_bridge, 'queue')
    assert hasattr(nowplaying_bridge, 'history')


def test_queue_bridge_remove_uses_queue_service(queue_bridge, queue_service, mock_player):
    mock_player.set_queue = MagicMock()
    queue_service.add({"track_id": 1, "title": "A"})
    queue_service.add({"track_id": 2, "title": "B"})
    result = queue_bridge.removeFromQueue(0)
    assert result["ok"]
    assert queue_service.count == 1
    assert queue_service.items[0]["track_id"] == 2


def test_queue_bridge_clear_uses_queue_service(queue_bridge, queue_service):
    queue_service.add({"track_id": 1, "title": "A"})
    queue_service.add({"track_id": 2, "title": "B"})
    result = queue_bridge.clearQueue()
    assert result["ok"]
    assert queue_service.count == 0


def test_queue_bridge_exposes_canonical_model_count_and_current_index(
    queue_bridge, queue_service
):
    queue_service.replace(
        [
            {"track_id": "first", "title": "First", "filepath": "/music/first.flac"},
            {"track_id": "second", "title": "Second", "filepath": "/music/second.flac"},
        ],
        start_index=1,
    )

    model = queue_bridge.queueModel
    assert queue_bridge.queueCount == 2
    assert queue_bridge.currentIndex == 1
    assert model.data(model.index(0, 0), model.TitleRole) == "First"
    assert model.data(model.index(1, 0), model.CurrentRole) is True


def test_playback_consumers_bind_to_queue_bridge_model():
    playback_page = (QML_PAGES / "PlaybackPage.qml").read_text()
    preview = (QML_PAGES / "nowplaying" / "NowPlayingQueuePreview.qml").read_text()

    assert "property var qb: typeof queueBridge" in playback_page
    assert "model: root.qb ? root.qb.queueModel : null" in playback_page
    assert "root.qb.queueCount" in playback_page
    assert "property var qb: typeof queueBridge" in preview
    assert "model: root.qb ? root.qb.queueModel : null" in preview
    assert "root.qb.queueCount" in preview
    assert "root.ps.queue" not in playback_page
    assert "root.ps.queue" not in preview


def test_playback_consumers_define_unavailable_queue_fallback():
    playback_page = (QML_PAGES / "PlaybackPage.qml").read_text()
    preview = (QML_PAGES / "nowplaying" / "NowPlayingQueuePreview.qml").read_text()

    assert "root.qb ? root.qb.queueCount : 0" in playback_page
    assert "root.qb ? root.qb.queueModel : null" in playback_page
    assert "root.qb ? root.qb.queueCount : 0" in preview
    assert "root.qb ? root.qb.queueModel : null" in preview


def test_one_queue_event_updates_order_count_and_current_once(
    queue_bridge, queue_service
):
    queue_service.replace(
        [
            {"track_id": "a", "title": "A", "filepath": "/music/a.flac"},
            {"track_id": "b", "title": "B", "filepath": "/music/b.flac"},
            {"track_id": "c", "title": "C", "filepath": "/music/c.flac"},
        ],
        start_index=1,
    )
    bridge_notifications = []
    model_resets = []
    queue_bridge.dataChanged.connect(lambda: bridge_notifications.append("changed"))
    queue_bridge.queueModel.modelReset.connect(lambda: model_resets.append("reset"))

    result = queue_service.reorder(0, 2)

    model = queue_bridge.queueModel
    assert result["ok"] is True
    assert bridge_notifications == ["changed"]
    assert model_resets == ["reset"]
    assert queue_bridge.queueCount == 3
    assert queue_bridge.currentIndex == 0
    assert [model.get(row)["title"] for row in range(3)] == ["B", "C", "A"]
    assert [model.get(row)["is_current"] for row in range(3)] == [True, False, False]


def test_queue_bridge_count_notification_and_shutdown_teardown(
    queue_bridge, queue_service
):
    queue_service.replace(
        [{"track_id": "a", "title": "A", "filepath": "/music/a.flac"}]
    )
    notifications = []
    queue_bridge.dataChanged.connect(lambda: notifications.append(queue_bridge.queueCount))

    queue_service.enqueue(
        {"track_id": "b", "title": "B", "filepath": "/music/b.flac"},
        play_now=False,
    )

    assert notifications == [2]
    assert queue_bridge.queueModel.rowCount() == 2

    queue_bridge.shutdown()
    queue_service.enqueue(
        {"track_id": "c", "title": "C", "filepath": "/music/c.flac"},
        play_now=False,
    )

    assert notifications == [2]
    assert queue_bridge.queueModel.rowCount() == 2


def test_full_workflow_library_to_playback(queue_service, mock_player):
    mock_player.set_queue = MagicMock()
    mock_player.play_index = MagicMock()
    mock_player.play_queue_index = mock_player.play_index

    tracks = [
        {"track_id": i, "title": f"Song {i}", "artist": "Artist",
         "source_type": "local_file", "duration": 200,
         "filepath": f"/music/song-{i}.flac"}
        for i in range(3)
    ]
    for t in tracks:
        queue_service.add(t)
    queue_service.current_index = 1

    mock_player.set_queue(queue_service.items)
    mock_player.get_queue.return_value = queue_service.items

    bridge = QueueBridge(queue_service=queue_service, player_service=mock_player)
    result = bridge.playFromIndex(1)
    assert result["ok"]
    mock_player.play_index.assert_called_with(1)


def test_queue_service_persistence_roundtrip(queue_service):
    tracks = [
        {"track_id": f"{i}", "track_uid": f"u{i}", "title": f"S{i}",
         "artist": "A", "source_type": "local_file", "duration": 200}
        for i in range(2)
    ]
    for t in tracks:
        queue_service.add(t)
    queue_service.save_state()

    fresh = QueueService()
    resolve_fn = MagicMock(side_effect=lambda item: item)
    result = fresh.load_state(resolve_fn=resolve_fn)
    assert result["ok"]
    assert fresh.count == 2


def _queue_state_path():
    from core.queue_service import _queue_state_path as qsp

    return qsp()
