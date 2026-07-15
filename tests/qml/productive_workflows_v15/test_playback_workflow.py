"""Workflow: Playback bridge and service connectivity."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("playback"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("playback"),
]


class TestPlaybackWorkflow:
    def test_playback_bridge_exists(self, bootstrap):
        pb = bootstrap._bridges.get("playback")
        assert pb is not None, "PlaybackBridge should exist"

    def test_nowplaying_bridge_exists(self, bootstrap):
        np = bootstrap._bridges.get("nowplaying")
        assert np is not None, "NowPlayingBridge should exist"

    def test_queue_bridge_exists(self, bootstrap):
        qb = bootstrap._bridges.get("queue")
        assert qb is not None, "QueueBridge should exist"

    def test_playback_has_action_handlers(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        assert ar is not None, "ActionRegistry should exist"
        play = ar.find("play")
        assert play is not None and play.handler is not None, "play handler should exist"
        pause = ar.find("pause")
        assert pause is not None and pause.handler is not None, "pause handler should exist"
