"""Queue authority tests for aggregate and remote production ingress."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from integrations.michi_link.server import V1_MIXIN


def _result(**data):
    return {"ok": True, **data}


class _Handler:
    def __init__(self):
        self.responses = []

    def _send_json(self, payload, status=200):
        self.responses.append((status, payload))


def test_michi_link_queue_and_controls_use_queue_service() -> None:
    queue = MagicMock()
    queue.get_state.return_value = {
        "items": [{"filepath": "/a.flac", "title": "A"}],
        "current_index": 0,
        "repeat": "all",
        "shuffle": True,
        "revision": 9,
    }
    queue.next.return_value = _result()
    queue.toggle_repeat.return_value = _result()
    queue.play_from_index.return_value = _result()
    V1_MIXIN._queue_service = queue
    V1_MIXIN._player_service = MagicMock()
    V1_MIXIN._playback = MagicMock()
    handler = _Handler()

    payload = V1_MIXIN._build_queue(None)
    V1_MIXIN._handle_control(
        handler, json.dumps({"command": "next"}).encode()
    )
    V1_MIXIN._handle_control(
        handler, json.dumps({"command": "repeat"}).encode()
    )
    V1_MIXIN._handle_queue_jump(
        handler, json.dumps({"index": 0}).encode()
    )

    assert payload["current_index"] == 0
    assert payload["repeat"] == "all"
    assert payload["shuffle"] is True
    assert payload["revision"] == 9
    queue.next.assert_called_once()
    queue.toggle_repeat.assert_called_once()
    queue.play_from_index.assert_called_once_with(0)
    V1_MIXIN._player_service.play_next.assert_not_called()
