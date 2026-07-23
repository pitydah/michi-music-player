"""Tests for production assistant playback and queue gateway boundaries."""
from __future__ import annotations

from unittest.mock import MagicMock

from core.assistant_gateways import ProductionPlaybackGateway, ProductionQueueGateway


def _result(**data: object) -> dict:
    return {"ok": True, **data}


def test_gateways_separate_transport_and_queue_authority() -> None:
    player = MagicMock()
    player.state = "playing"
    queue = MagicMock()
    queue.next.return_value = _result()
    queue.previous.return_value = _result()
    queue.set_repeat.return_value = _result()
    queue.set_shuffle.return_value = _result()
    track_actions = MagicMock()
    track_actions.play_track.return_value = _result()
    query = MagicMock()
    query.fetch_track_internal.side_effect = lambda track_id: {
        "track_id": track_id,
        "filepath": f"/{track_id}.flac",
    }
    playback = ProductionPlaybackGateway(player, queue, track_actions)
    queue_gateway = ProductionQueueGateway(queue, query)

    assert playback.play_track("7")["ok"]
    assert playback.next()["ok"]
    assert playback.previous()["ok"]
    assert playback.set_repeat("all")["ok"]
    assert playback.set_shuffle(True)["ok"]
    queue.enqueue.return_value = _result()
    assert queue_gateway.add_to_queue(["7", "8"])["ok"]

    player.play.assert_not_called()
    player.play_next.assert_not_called()
    player.play_prev.assert_not_called()
    queue.enqueue.assert_called_once()


def test_queue_gateway_reports_missing_capability() -> None:
    gateway = ProductionQueueGateway(None)

    result = gateway.get_queue()

    assert not result["ok"]
    assert result["code"] == "CAPABILITY_UNAVAILABLE"
