"""Workflow: Metadata → Tagging → Doctor."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("metadata"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestMetadataTaggingDoctor:
    def test_metadata_preview(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert mb is not None
        assert hasattr(mb, 'preview')

    def test_metadata_diff(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert hasattr(mb, 'diff')

    def test_metadata_conflicts(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert hasattr(mb, 'conflicts')

    def test_metadata_tagging_candidates(self, bootstrap, bridges):
        mb = bridges.get("metadata")
        assert hasattr(mb, 'tagging_candidates')

    def test_tagging_service(self, bootstrap):
        svc = bootstrap.container.get("smart_tagging_service")
        if svc is None:
            pytest.skip("smart_tagging_service not registered (optional)")
        assert hasattr(svc, 'identify')

    def test_doctor_service(self, bootstrap):
        svc = bootstrap.container.get("library_doctor_service")
        if svc is None:
            pytest.skip("library_doctor_service not registered (optional)")
        assert hasattr(svc, 'scan')

    def test_qtest_navigate_tagging(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("tagging")
        assert nav.currentRoute == "tagging"
        page = find_qml_item(root_window, "SmartTaggingPage")
        if page is not None:
            page.forceActiveFocus()
            QTest.keyClick(page, Qt.Key_Down)
            QTest.qWait(50)
            assert nav.currentRoute == "tagging"
