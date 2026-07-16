"""Workflow: Connections → Discover → Connect → Disconnect."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("connections"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestConnections:
    def test_connection_discover_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        for aid in ("connection.discover", "connection.connect", "connection.disconnect"):
            a = ar.find(aid)
            assert a is not None and a.handler is not None, f"{aid} handler"

    def test_connection_service_methods(self, bootstrap):
        svc = bootstrap.container.get("connection_service")
        assert svc is not None
        assert hasattr(svc, 'discover')
        assert hasattr(svc, 'connect')
        assert hasattr(svc, 'disconnect')

    def test_connections_bridge_exists(self, bootstrap):
        cb = bootstrap._bridges.get("connections")
        assert cb is not None
