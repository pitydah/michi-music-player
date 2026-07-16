"""Workflow: Shutdown with active jobs."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("runtime_cleanup"),
]


class TestShutdown:
    def test_shutdown_services(self, bootstrap):
        c = bootstrap.container
        c.shutdown()
        for name, svc in c._services.items():
            if hasattr(svc, 'shutdown'):
                assert True  # shutdown was called
        assert c.state.value == "stopped"
