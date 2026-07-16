"""Workflow: Metadata → Tagging → Doctor."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("metadata"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestMetadataTaggingDoctor:
    def test_metadata_preview(self, bootstrap):
        mb = bootstrap._bridges.get("metadata")
        assert mb is not None
        assert hasattr(mb, 'preview')

    def test_metadata_diff(self, bootstrap):
        mb = bootstrap._bridges.get("metadata")
        assert hasattr(mb, 'diff')

    def test_metadata_conflicts(self, bootstrap):
        mb = bootstrap._bridges.get("metadata")
        assert hasattr(mb, 'conflicts')

    def test_metadata_tagging_candidates(self, bootstrap):
        mb = bootstrap._bridges.get("metadata")
        assert hasattr(mb, 'tagging_candidates')

    def test_tagging_service(self, bootstrap):
        svc = bootstrap.container.get("smart_tagging_service")
        assert svc is not None
        assert hasattr(svc, 'identify')

    def test_doctor_service(self, bootstrap):
        svc = bootstrap.container.get("library_doctor_service")
        assert svc is not None
        assert hasattr(svc, 'scan')
