"""Workflow: Home — bridge existence and navigation."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("home"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("home"),
]


class TestHomeWorkflow:
    def test_home_bridge_exists(self, bootstrap):
        home_bridge = bootstrap._bridges.get("home")
        assert home_bridge is not None, "HomeBridge should be registered"

    def test_capability_bridge_exists(self, bootstrap):
        cap = bootstrap._bridges.get("capability")
        assert cap is not None, "CapabilityBridge should be registered"

    def test_navigate_to_home(self, nav):
        nav.navigate("home")
        assert nav.currentRoute == "home", (
            f"Expected 'home', got '{nav.currentRoute}'"
        )
