"""Workflow: Search and Navigation functions."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_dimension("service_wiring"),
    pytest.mark.qml_dimension("navigation"),
]


class TestSearchFunctions:
    pytestmark = [pytest.mark.qml_module("search")]

    def test_global_search_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("global_search")
        assert bridge is not None

    def test_global_search_service_exists(self, bootstrap):
        svc = bootstrap.container.get("global_search_service")
        assert svc is not None


class TestNavigationFunctions:
    pytestmark = [pytest.mark.qml_module("core")]

    def test_navigation_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("navigation")
        assert bridge is not None

    def test_route_registry_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("route_registry")
        assert bridge is not None

    def test_page_state_store_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("page_state")
        assert bridge is not None
