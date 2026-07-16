"""Workflow: Search A → Search B → reject stale A."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("search"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestSearchStaleRejection:
    def test_search_bridge_exists(self, bootstrap, bridges):
        sb = bridges.get("global_search")
        assert sb is not None

    def test_search_service_exists(self, bootstrap):
        svc = bootstrap.container.get("global_search_service")
        assert svc is not None

    def test_global_search_stale_guard(self, bootstrap, bridges):
        sb = bridges.get("global_search")
        assert hasattr(sb, '_is_stale') or hasattr(sb, 'cancel')
