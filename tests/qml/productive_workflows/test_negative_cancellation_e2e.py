"""E2E: Cancellation of long operations."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestNegativeCancellationE2E:
    def test_action_registry_cancel(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        assert ar is not None
        action = ar.get("queue.clear")
        assert action is not None

    def test_library_doctor_cancel(self, bootstrap, bridges):
        doc = bridges.get("library_doctor")
        assert doc is not None
        assert hasattr(doc, 'cancelScan')
