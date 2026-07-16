"""Workflow: Diagnostics → Health Check."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("diagnostics"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestDiagnostics:
    def test_diagnostics_open_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("diagnostics.open")
        assert a is not None, "diagnostics.open action exists"

    def test_diagnostics_service_methods(self, bootstrap):
        svc = bootstrap.container.get("diagnostics_service")
        assert svc is not None
        assert hasattr(svc, 'check_all')
        assert hasattr(svc, 'check_database')
        assert hasattr(svc, 'check_library')
        assert hasattr(svc, 'health')
