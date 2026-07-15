"""Tests for Diagnostics v12 — DiagnosticsBridge uses DiagnosticsService, NO db/radio_manager/sync_manager directo."""
from unittest.mock import MagicMock, patch

import pytest


class TestDiagnosticsBridgeCreation:
    def test_requires_query_executor(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        with pytest.raises(Exception):
            DiagnosticsBridge()

    def test_requires_diagnostics_service(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        with pytest.raises(Exception):
            DiagnosticsBridge(query_executor=MagicMock())

    def test_creation(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        db = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        assert db is not None

    def test_no_direct_db_access(self):
        from ui_qml_bridge import diagnostics_bridge
        content = open(diagnostics_bridge.__file__).read()
        assert "self._db" not in content or "db=" not in content

    def test_no_direct_radio_access(self):
        from ui_qml_bridge import diagnostics_bridge
        content = open(diagnostics_bridge.__file__).read()
        assert "radio_manager" not in content

    def test_no_direct_sync_access(self):
        from ui_qml_bridge import diagnostics_bridge
        content = open(diagnostics_bridge.__file__).read()
        assert "sync_manager" not in content


class TestDiagnosticsOperations:
    def test_refresh(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        db = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        result = db.refresh()
        assert result.get("ok")

    def test_jobs_property(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        db = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        jobs = db.jobs
        assert isinstance(jobs, list)

    def test_copy_diagnostics(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        db = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        text = db.copyDiagnostics()
        assert "Michi Music Player" in text
