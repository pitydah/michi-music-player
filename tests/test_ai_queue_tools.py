"""Tests for legacy AI queue tools using canonical QueueService."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from integrations.ai_assistant.tools.queue_tools import (
    add_tracks_to_queue,
    play_track,
)


def _db():
    db = MagicMock()
    db.get_all.return_value = [
        SimpleNamespace(id=1, filepath="/music/one.flac"),
        SimpleNamespace(id=2, filepath="/music/two.flac"),
    ]
    return db


def test_add_tracks_uses_queue_service() -> None:
    queue = MagicMock()

    result = add_tracks_to_queue(_db(), [1, 2], queue_service=queue)

    assert result.success
    queue.enqueue.assert_called_once_with(
        ["/music/one.flac", "/music/two.flac"], play_now=False
    )


def test_play_track_uses_queue_service() -> None:
    queue = MagicMock()

    result = play_track(_db(), 1, queue_service=queue)

    assert result.success
    queue.enqueue.assert_called_once_with(["/music/one.flac"], play_now=True)


def test_queue_tool_fails_without_queue_service() -> None:
    result = add_tracks_to_queue(_db(), [1])

    assert not result.success
    assert result.error == "Queue service unavailable."
