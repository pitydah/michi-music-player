"""QueueBridge v2 command and playlist-save contracts."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _queue_service(items: list[dict] | None = None, current_index: int = -1) -> MagicMock:
    service = MagicMock()
    state = {"items": list(items or []), "current_index": current_index}
    service.get_state.return_value = state
    service.items = list(state["items"])
    service.current_index = current_index
    service.subscribe.return_value = MagicMock()
    return service


def test_add_delegates_once_without_requesting_playback() -> None:
    service = _queue_service([{"title": "Current"}], current_index=0)
    service.enqueue.return_value = {"ok": True, "added": 2}
    bridge = QueueBridge(queue_service=service)
    additions = [{"title": "Second"}, {"title": "Third"}]

    result = bridge.add(additions)

    assert result == {"ok": True, "added": 2}
    service.enqueue.assert_called_once_with(additions, play_now=False)
    assert service.current_index == 0


def test_add_empty_items_returns_service_error_after_one_delegation() -> None:
    service = _queue_service()
    service.enqueue.return_value = {"ok": False, "error": "EMPTY_QUEUE"}
    bridge = QueueBridge(queue_service=service)

    result = bridge.add([])

    assert result == {"ok": False, "error": "EMPTY_QUEUE"}
    service.enqueue.assert_called_once_with([], play_now=False)


def test_replace_and_play_delegates_valid_request_once() -> None:
    service = _queue_service([{"title": "Old"}], current_index=0)
    service.replace_and_play.return_value = {
        "ok": True,
        "operation": "replace_and_play",
        "current_index": 1,
    }
    bridge = QueueBridge(queue_service=service)
    replacement = [{"title": "First"}, {"title": "Selected"}]

    result = bridge.replaceAndPlay(replacement, 1)

    assert result["ok"] is True
    assert result["current_index"] == 1
    service.replace_and_play.assert_called_once_with(replacement, 1)


def test_replace_and_play_rejects_empty_items_without_mutation() -> None:
    service = _queue_service([{"title": "Current"}], current_index=0)
    bridge = QueueBridge(queue_service=service)

    result = bridge.replaceAndPlay([], 0)

    assert result == {"ok": False, "error": "EMPTY_QUEUE"}
    service.replace_and_play.assert_not_called()


def test_replace_and_play_rejects_out_of_range_index_without_mutation() -> None:
    service = _queue_service([{"title": "Current"}], current_index=0)
    bridge = QueueBridge(queue_service=service)
    replacement = [{"title": "Only"}]

    result = bridge.replaceAndPlay(replacement, 1)

    assert result == {"ok": False, "error": "INVALID_INDEX"}
    service.replace_and_play.assert_not_called()


def test_save_as_playlist_writes_current_queue_once_in_order() -> None:
    items = [{"title": "First"}, {"title": "Second"}]
    service = _queue_service(items, current_index=0)
    playlists = MagicMock()
    playlists.saveQueueAsPlaylist.return_value = {"ok": True, "count": 2}
    bridge = QueueBridge(queue_service=service, playlists_bridge=playlists)

    result = bridge.saveAsPlaylist("  Road Trip  ")

    assert result == {"ok": True, "count": 2}
    playlists.saveQueueAsPlaylist.assert_called_once_with("Road Trip", items)


def test_save_as_playlist_rejects_blank_name_without_write() -> None:
    playlists = MagicMock()
    bridge = QueueBridge(
        queue_service=_queue_service([{"title": "Track"}]),
        playlists_bridge=playlists,
    )

    result = bridge.saveAsPlaylist("   ")

    assert result == {"ok": False, "error": "EMPTY_NAME"}
    playlists.saveQueueAsPlaylist.assert_not_called()


def test_save_as_playlist_rejects_empty_queue_without_write() -> None:
    playlists = MagicMock()
    bridge = QueueBridge(queue_service=_queue_service(), playlists_bridge=playlists)

    result = bridge.saveAsPlaylist("Empty mix")

    assert result == {"ok": False, "error": "EMPTY_QUEUE"}
    playlists.saveQueueAsPlaylist.assert_not_called()


def test_save_as_playlist_rejects_unavailable_service_without_write() -> None:
    bridge = QueueBridge(
        queue_service=_queue_service([{"title": "Track"}]),
        playlists_bridge=None,
    )

    result = bridge.saveAsPlaylist("Favorites")

    assert result == {"ok": False, "error": "NO_PLAYLIST_BRIDGE"}


def test_save_as_playlist_reports_write_failure_without_retry() -> None:
    playlists = MagicMock()
    playlists.saveQueueAsPlaylist.side_effect = RuntimeError("disk full")
    bridge = QueueBridge(
        queue_service=_queue_service([{"title": "Track"}]),
        playlists_bridge=playlists,
    )

    result = bridge.saveAsPlaylist("Favorites")

    assert result == {"ok": False, "error": "disk full"}
    assert playlists.saveQueueAsPlaylist.call_count == 1


def test_queue_action_uses_only_queue_bridge_playlist_write() -> None:
    source = (PROJECT_ROOT / "ui_qml/pages/queue/QueueActions.qml").read_text()

    assert 'root.qb.saveAsPlaylist("Cola")' in source
    assert "playlistsBridge.createFromQueue" not in source
