from __future__ import annotations
"""EF — Diagnostics: service health via DiagnosticsService, storage paths, support bundle.
No SQL ni benchmarks en bridge. No direct db/radio/sync."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge

pytestmark = [pytest.mark.qml_module("diagnostics")]


@pytest.fixture
def ds():
    d = MagicMock()
    d.check_player_api.return_value = {"status": "ok", "api_version": "v1"}
    d.check_sync_server.return_value = {"status": "ok", "running": True}
    d.check_pairing.return_value = {"status": "ok", "paired": 1}
    d.check_playback.return_value = {"status": "ok", "state": "playing"}
    d.check_queue.return_value = {"status": "ok", "queue_length": 5}
    d.check_continue_readiness.return_value = {"status": "ready", "has_queue": True}
    return d


@pytest.fixture
def wm():
    wm = MagicMock()
    wm.run_task.return_value = MagicMock()
    return wm


@pytest.fixture
def bridge(wm, ds):
    return DiagnosticsBridge(diagnostics_service=ds, worker_manager=wm)


class TestDiagnosticsInitialState:
    def test_initial_jobs_empty(self, bridge):
        assert bridge.jobs == []

    def test_initial_env_empty(self, bridge):
        assert bridge._env_info == {}

    def test_refresh_returns_ok(self, bridge, wm):
        result = bridge.refresh()
        assert result["ok"] is True


class TestServiceHealth:
    def test_services_availability_all_present(self):
        ds = MagicMock()
        bridge = DiagnosticsBridge(
            diagnostics_service=ds,
            player_service=MagicMock(), worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        result = bridge._check_services_availability()
        assert result["status"] == "PASS"

    def test_services_availability_only_wm(self, bridge):
        result = bridge._check_services_availability()
        assert result["status"] == "WARN"


class TestDiagnosticsServiceChecks:
    def test_player_api_ok(self, ds):
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_player_api()
        assert result["status"] == "PASS"

    def test_sync_server_ok(self, ds):
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_sync_server()
        assert result["status"] == "PASS"

    def test_pairing_ok(self, ds):
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_pairing()
        assert result["status"] == "PASS"

    def test_playback_ok(self, ds):
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_playback()
        assert result["status"] == "PASS"

    def test_queue_ok(self, ds):
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_queue()
        assert result["status"] == "PASS"

    def test_continue_readiness_ok(self, ds):
        bridge = DiagnosticsBridge(diagnostics_service=ds)
        result = bridge._check_continue_readiness()
        assert result["status"] == "PASS"

    def test_no_diagnostics_service_returns_fail(self):
        bridge = DiagnosticsBridge()
        result = bridge._check_player_api()
        assert result["status"] == "FAIL"

    def test_storage_paths_ok(self, bridge):
        result = bridge._check_storage_paths()
        assert result["status"] in ("PASS", "FAIL")


class TestSupportBundle:
    def test_copy_diagnostics_returns_string(self, bridge):
        bridge._jobs = [
            {"status": "PASS", "id": "diagnostics.player_api", "message": "OK", "duration_ms": 10},
            {"status": "PASS", "id": "diagnostics.playback", "message": "OK", "duration_ms": 5},
        ]
        text = bridge.copyDiagnostics()
        assert "Michi Music Player Diagnostics" in text
        assert "diagnostics.player_api" in text

    def test_copy_diagnostics_empty_jobs(self, bridge):
        text = bridge.copyDiagnostics()
        assert text != ""

    def test_copy_diagnostics_includes_timestamp(self, bridge):
        text = bridge.copyDiagnostics()
        assert "Time:" in text


class TestJobsScheduling:
    def test_refresh_schedules_jobs(self, bridge, wm):
        bridge.refresh()
        assert wm.run_task.called

    def test_refresh_emits_diagnostics_updated(self, bridge, wm):
        bridge.diagnosticsUpdated = MagicMock()
        bridge.refresh()
        assert bridge.diagnosticsUpdated.emit.called

    def test_schedule_job_no_worker(self, bridge):
        bridge._wm = None
        bridge._run_all_jobs()
        assert len(bridge._jobs) == 1
        assert bridge._jobs[0]["id"] == "worker.unavailable"
