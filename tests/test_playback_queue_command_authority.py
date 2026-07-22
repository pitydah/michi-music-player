from __future__ import annotations

from unittest.mock import MagicMock

from adapters.mpris import MPRISObject
from core.application_bootstrap import ApplicationBootstrap
from core.queue_service import QueueService
from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml.models.QueueListModel import QueueListModel


def _queue_with_player() -> tuple[QueueService, MagicMock]:
    player = MagicMock()
    queue = QueueService(player_service=player)
    queue.enqueue([
        {"title": "A", "filepath": "/music/a.flac"},
        {"title": "B", "filepath": "/music/b.flac"},
        {"title": "C", "filepath": "/music/c.flac"},
    ])
    return queue, player


def test_nowplaying_routes_all_queue_commands_to_queue_service() -> None:
    queue, player = _queue_with_player()
    bridge = NowPlayingBridge(
        player_service=player,
        queue_service=queue,
        audio_quality_adapter=MagicMock(),
    )

    assert bridge.queueIndex == 0
    assert bridge.next()["ok"]
    assert bridge.queueIndex == 1
    assert bridge.previous()["ok"]
    assert bridge.enqueueSong("/music/d.flac")["ok"]
    assert bridge.moveQueueItem(3, 1)["ok"]
    assert bridge.playQueueItem(1)["ok"]
    assert bridge.removeFromQueue(0)["ok"]
    assert len(bridge.queue) == 3
    assert bridge.clearQueue()["ok"]
    assert bridge.queue == []

    player.play_next.assert_not_called()
    player.play_prev.assert_not_called()
    player.enqueue.assert_not_called()
    player.remove_from_queue.assert_not_called()
    player.move_queue_item.assert_not_called()
    player.play_queue_item.assert_not_called()


def test_action_registry_next_and_previous_use_queue_service() -> None:
    queue, player = _queue_with_player()
    bootstrap = ApplicationBootstrap()
    bootstrap.container.register("queue_service", queue)
    bootstrap.container.register("playback_service", player)
    registry = ActionRegistry()
    bootstrap._register_actions(registry)

    assert registry.execute("next")["ok"]
    assert registry.execute("previous")["ok"]
    player.next.assert_not_called()
    player.previous.assert_not_called()


def test_mpris_next_and_previous_use_queue_service() -> None:
    queue, player = _queue_with_player()
    mpris = object.__new__(MPRISObject)
    mpris._engine = None
    mpris.set_player_service(player)
    mpris.set_queue_service(queue)

    mpris.Next()
    mpris.Previous()

    assert queue.current_index == 0
    player.play_next.assert_not_called()
    player.play_prev.assert_not_called()


def test_bridge_factory_injects_queue_service_into_nowplaying() -> None:
    queue, player = _queue_with_player()
    bootstrap = ApplicationBootstrap()
    bootstrap.container.register("queue_service", queue)
    bootstrap.container.register("playback_service", player)
    bootstrap.container.register("worker_manager", MagicMock())
    factory = BridgeFactory(bootstrap.container)

    factory.create_nowplaying_bridge()

    bridge = factory.get("nowplaying")
    assert bridge._queue_service is queue


def test_queue_bridge_saves_canonical_items_as_playlist() -> None:
    queue, player = _queue_with_player()
    playlists = MagicMock()
    playlists.saveQueueAsPlaylist.return_value = {"ok": True, "count": 3}
    bridge = QueueBridge(
        player_service=player,
        playlists_bridge=playlists,
        queue_service=queue,
    )

    result = bridge.saveAsPlaylist("Current queue")

    assert result["ok"]
    playlists.saveQueueAsPlaylist.assert_called_once_with(
        "Current queue", queue.items
    )
    player.get_queue.assert_not_called()


def test_queue_model_observes_action_registry_navigation() -> None:
    queue, player = _queue_with_player()
    model = QueueListModel(queue_service=queue)
    bootstrap = ApplicationBootstrap()
    bootstrap.container.register("queue_service", queue)
    bootstrap.container.register("playback_service", player)
    registry = ActionRegistry()
    bootstrap._register_actions(registry)

    assert model.data(model.index(0), model.CurrentRole) is True
    assert registry.execute("next")["ok"]

    assert model.data(model.index(0), model.CurrentRole) is False
    assert model.data(model.index(1), model.CurrentRole) is True


def test_queue_model_observes_mpris_navigation() -> None:
    queue, player = _queue_with_player()
    model = QueueListModel(queue_service=queue)
    mpris = object.__new__(MPRISObject)
    mpris._engine = None
    mpris.set_player_service(player)
    mpris.set_queue_service(queue)

    mpris.Next()

    assert model.data(model.index(1), model.CurrentRole) is True


def test_nowplaying_observes_external_queue_modes_and_index() -> None:
    queue, player = _queue_with_player()
    bridge = NowPlayingBridge(
        player_service=player,
        queue_service=queue,
        audio_quality_adapter=MagicMock(),
    )

    queue.set_repeat("all")
    queue.set_shuffle(True)
    queue.play_from_index(2)

    assert bridge.repeatMode == "all"
    assert bridge.shuffleEnabled is True
    assert bridge.queueIndex == 2
    assert bridge.queue[2]["is_current"] is True


def test_failed_mutation_does_not_publish_false_model_state() -> None:
    queue, player = _queue_with_player()
    model = QueueListModel(queue_service=queue)
    initial_titles = [model.data(model.index(i), model.TitleRole)
                      for i in range(model.rowCount())]
    player.play_queue.side_effect = RuntimeError("sync failed")

    result = queue.remove([0])

    assert not result["ok"]
    assert model.rowCount() == 3
    assert [model.data(model.index(i), model.TitleRole)
            for i in range(model.rowCount())] == initial_titles
