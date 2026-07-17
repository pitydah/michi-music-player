"""E2E: Metadata preview workflow."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("metadata"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestMetadataPreviewE2E:
    def test_metadata_bridge_preview(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert mb is not None
        assert hasattr(mb, 'preview')

    def test_metadata_bridge_diff(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert mb is not None
        assert hasattr(mb, 'diff')

    def test_metadata_bridge_conflicts(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert mb is not None
        assert hasattr(mb, 'conflicts')
