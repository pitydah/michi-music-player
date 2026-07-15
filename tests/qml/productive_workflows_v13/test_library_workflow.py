"""Workflow: Library → Search → Select → Play."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("library"),
]


class TestLibraryWorkflow:
    def test_library_bridge_exists(self, bootstrap):
        lib = bootstrap._bridges.get("library")
        assert lib is not None, "LibraryBridge should exist"

    def test_library_query_service(self, bootstrap):
        svc = bootstrap.container.get("library_query_service")
        assert svc is not None, "LibraryQueryService should exist"

    def test_search_bridge_exists(self, bootstrap):
        search = bootstrap._bridges.get("global_search")
        assert search is not None, "GlobalSearchBridge should exist"
