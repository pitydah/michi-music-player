"""Workflow: Home Audio → Group → Volume → Ungroup."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("home_audio"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestHomeAudio:
    def test_home_audio_volume_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        for aid in ("home_audio.volume", "home_audio.mute", "home_audio.group", "home_audio.ungroup"):
            a = ar.find(aid)
            assert a is not None and a.handler is not None, f"{aid} handler"

    def test_home_audio_service_methods(self, bootstrap):
        svc = bootstrap.container.get("home_audio_service")
        assert svc is not None
        assert hasattr(svc, 'discover_zones')
        assert hasattr(svc, 'get_groups')
        assert hasattr(svc, 'create_group')
        assert hasattr(svc, 'delete_group')
        assert hasattr(svc, 'set_volume')
        assert hasattr(svc, 'mute')

    def test_home_audio_bridge_exists(self, bootstrap):
        hb = bootstrap._bridges.get("home_audio")
        assert hb is not None
