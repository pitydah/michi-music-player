"""Workflow: Radio → Buffer → Play → Stop."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("radio"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestRadio:
    def test_radio_play_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        for aid in ("radio.play", "radio.stop"):
            a = ar.get(aid)
            assert a is not None, f"{aid} action exists"

    def test_radio_service_methods(self, bootstrap):
        svc = bootstrap.container.get("radio_service")
        assert svc is not None
        assert hasattr(svc, 'play_station')
        assert hasattr(svc, 'stop')
        assert hasattr(svc, 'get_buffer_ms') or hasattr(svc, 'set_buffer_ms')
        assert hasattr(svc, 'set_reconnect_policy')

    def test_radio_bridge_exists(self, bootstrap, bridges):
        rb = bridges.get("radio")
        assert rb is not None
