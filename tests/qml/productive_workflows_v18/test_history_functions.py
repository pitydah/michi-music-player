"""Workflow: History functions — play, remove."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("history"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestHistoryFunctions:
    def test_history_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("history.play")
        assert a is not None and a.handler is not None

    def test_history_remove_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("history.remove")
        assert a is not None and a.handler is not None

    def test_history_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("history")
        assert bridge is not None

    def test_history_service_exists(self, bootstrap):
        svc = bootstrap.container.get("history_query_service")
        assert svc is not None
