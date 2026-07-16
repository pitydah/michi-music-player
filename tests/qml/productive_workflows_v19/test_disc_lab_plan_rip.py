"""Workflow: Disc Lab → Plan → Rip Job → Cancel."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("disc_lab"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestDiscLab:
    def test_disc_lab_bridge_methods(self, bootstrap, bridges):
        dl = bridges.get("disc_lab")
        assert dl is not None
        assert hasattr(dl, 'scanDisc')
        assert hasattr(dl, 'cover')
        assert hasattr(dl, 'rip_plan')
        assert hasattr(dl, 'startExtraction')
        assert hasattr(dl, 'cancelExtraction')

    def test_disc_lab_service_exists(self, bootstrap):
        svc = bootstrap.container.get("disc_lab_service")
        if svc is None:
            pytest.skip("disc_lab_service not registered (optional)")
