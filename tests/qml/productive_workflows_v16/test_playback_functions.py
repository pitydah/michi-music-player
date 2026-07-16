"""Workflow: Playback functions — play, pause, stop, next, prev."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("playback"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
    pytest.mark.qml_dimension("primary_interaction"),
]


class TestPlaybackFunctions:
    def test_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        assert ar is not None
        a = ar.find("play")
        assert a is not None, "play action"
        assert a.handler is not None, "play handler not None"
        assert a.title == "Play"
        assert a.category == "playback"

    def test_pause_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("pause")
        assert a is not None and a.handler is not None

    def test_stop_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("stop")
        assert a is not None and a.handler is not None

    def test_next_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("next")
        assert a is not None and a.handler is not None

    def test_previous_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("previous")
        assert a is not None and a.handler is not None

    def test_track_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("track.play")
        assert a is not None and a.handler is not None

    def test_track_enqueue_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("track.enqueue")
        assert a is not None and a.handler is not None

    def test_track_favorite_toggle_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("track.favorite.toggle")
        assert a is not None and a.handler is not None

    def test_playback_bridge_exists(self, bootstrap):
        pb = bootstrap._bridges.get("playback")
        assert pb is not None

    def test_nowplaying_bridge_exists(self, bootstrap):
        np = bootstrap._bridges.get("nowplaying")
        assert np is not None

    def test_queue_bridge_exists(self, bootstrap):
        qb = bootstrap._bridges.get("queue")
        assert qb is not None

    def test_playback_service_exists(self, bootstrap):
        svc = bootstrap.container.get("playback_service")
        assert svc is not None
        assert hasattr(svc, 'play')
        assert hasattr(svc, 'pause')
        assert hasattr(svc, 'stop')
        assert hasattr(svc, 'next')

    def test_queue_service_methods(self, bootstrap):
        svc = bootstrap.container.get("queue_service")
        assert svc is not None
        assert hasattr(svc, 'enqueue')
        assert hasattr(svc, 'remove')
        assert hasattr(svc, 'clear')
        assert hasattr(svc, 'play_next')
