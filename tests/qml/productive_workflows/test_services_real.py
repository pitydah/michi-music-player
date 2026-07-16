"""Gate check: verify NO object() services exist in the container."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("gate_check"),
    pytest.mark.qml_route("all"),
]


class TestServicesReal:
    def test_no_object_services(self, bootstrap):
        services = bootstrap.container._services
        for name, svc in services.items():
            assert type(svc).__name__ != "object", (
                f"Service '{name}' is object() placeholder"
            )

    def test_action_registry_has_handlers(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        if ar is not None:
            for aid, desc in ar._actions.items():
                assert desc.handler is not None, (
                    f"Action '{aid}' has None handler"
                )
                assert callable(desc.handler), (
                    f"Action '{aid}' handler is not callable"
                )

    def test_all_bridges_have_services(self, bootstrap):
        bridges = bootstrap._bridges
        for name, bridge in bridges.items():
            assert bridge is not None, f"Bridge '{name}' is None"
