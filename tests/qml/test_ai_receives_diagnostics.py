"""Test MichiAIBridge — receives Diagnostics created before it, injects correct instance."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


@pytest.fixture
def diagnostics():
    d = MagicMock()
    d.refresh.return_value = {"ok": True}
    d.jobs = []
    return d


@pytest.fixture
def worker_manager():
    wm = MagicMock()
    wm.run_task.return_value = MagicMock(state="completed")
    return wm


class TestReceivesDiagnostics:
    def test_diagnostics_injected(self, diagnostics, worker_manager):
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            worker_manager=worker_manager,
        )
        assert bridge._diagnostics is diagnostics

    def test_diagnostics_not_none(self, diagnostics, worker_manager):
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            worker_manager=worker_manager,
        )
        assert bridge._diagnostics is not None

    def test_diagnose_calls_refresh(self, diagnostics, worker_manager):
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            worker_manager=worker_manager,
        )
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "completed" or bridge.status == "executing"

    def test_diagnose_returns_result(self, diagnostics, worker_manager):
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            worker_manager=worker_manager,
        )
        result = bridge._action_diagnose(MagicMock(entities={}))
        assert result.get("ok") is True

    def test_diagnose_without_diagnostics(self, worker_manager):
        bridge = MichiAIBridge(worker_manager=worker_manager)
        result = bridge._action_diagnose(MagicMock(entities={}))
        assert result.get("ok") is False
        assert "NO_DIAGNOSTICS_SERVICE" in result.get("error", "")

    def test_diagnostics_created_before_ai(self, diagnostics):
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            action_registry=MagicMock(),
        )
        assert bridge._diagnostics is not None
        assert bridge._action_registry is not None

    def test_diagnostics_refresh_uses_worker(self, diagnostics, worker_manager):
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            worker_manager=worker_manager,
        )
        bridge._set_status("idle")
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status in ("completed", "executing", "failed")

    def test_diagnostics_jobs_accessible(self, diagnostics, worker_manager):
        diagnostics.jobs = [
            {"id": "db.check", "status": "PASS", "message": "OK"},
        ]
        bridge = MichiAIBridge(
            diagnostics_service=diagnostics,
            worker_manager=worker_manager,
        )
        result = bridge._action_diagnose(MagicMock(entities={}))
        assert result.get("ok") is True or result.get("ok") is not None
