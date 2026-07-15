"""Workflow: Mix → Generate → Results."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("mix"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("mix"),
]


class TestMixWorkflow:
    def test_mix_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("mix")
        assert bridge is not None, "MixBridge should exist"

    def test_mix_service_not_object(self, bootstrap):
        svc = bootstrap.container.get("mix_service")
        assert svc is not None, "MixService should not be None"
        assert type(svc).__name__ != "object", "MixService should not be object()"
