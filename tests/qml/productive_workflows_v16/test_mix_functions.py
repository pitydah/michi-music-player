"""Workflow: Mix functions — generate, cancel, play, enqueue, save."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("mix"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
    pytest.mark.qml_dimension("primary_interaction"),
]


class TestMixFunctions:
    def test_mix_generate_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("mix.generate")
        assert a is not None and a.handler is not None

    def test_mix_cancel_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("mix.cancel")
        assert a is not None and a.handler is not None

    def test_mix_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("mix.play")
        assert a is not None and a.handler is not None

    def test_mix_enqueue_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("mix.enqueue")
        assert a is not None and a.handler is not None

    def test_mix_service_exists(self, bootstrap):
        svc = bootstrap.container.get("mix_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'generate')
        assert hasattr(svc, 'cancel')
        assert hasattr(svc, 'health')

    def test_mix_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("mix")
        assert bridge is not None
