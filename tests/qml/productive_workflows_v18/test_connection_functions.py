"""Workflow: Connection functions — discover, connect, disconnect."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("connections"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestConnectionFunctions:
    def test_connection_discover_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("connection.discover")
        assert a is not None and a.handler is not None

    def test_connection_connect_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("connection.connect")
        assert a is not None and a.handler is not None

    def test_connection_disconnect_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("connection.disconnect")
        assert a is not None and a.handler is not None

    def test_connection_service_exists(self, bootstrap):
        svc = bootstrap.container.get("connection_service")
        assert svc is not None
        assert type(svc).__name__ != "object"
        assert hasattr(svc, 'discover')
        assert hasattr(svc, 'connect')
        assert hasattr(svc, 'disconnect')

    def test_connections_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("connections")
        assert bridge is not None
