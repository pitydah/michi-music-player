"""Workflow: Home Audio functions — volume, mute, discover."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("home_audio"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestHomeAudioFunctions:
    def test_home_audio_volume_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("home_audio.volume")
        assert a is not None and a.handler is not None

    def test_home_audio_mute_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("home_audio.mute")
        assert a is not None and a.handler is not None

    def test_home_audio_service_exists(self, bootstrap):
        svc = bootstrap.container.get("home_audio_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'set_volume')
        assert hasattr(svc, 'mute')
        assert hasattr(svc, 'discover_zones')

    def test_home_audio_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("home_audio")
        assert bridge is not None
