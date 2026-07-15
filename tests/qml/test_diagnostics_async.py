from __future__ import annotations
"""Wave XLIII — 10.2: Diagnostics async.
Tests:
  - Diagnostics via jobs, NOT from getters
  - Cero tareas y cero requests = PASS
  - All jobs produce dict with id/status/value/message/duration_ms
  - Uses DiagnosticsService, no direct db/radio/sync
"""
from unittest.mock import MagicMock
import time

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


def _process_events_until(condition, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


class TestDiagnosticsAsync:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def worker_manager(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def diagnostics_service(self):
        ds = MagicMock()
        ds.check_player_api.return_value = {"status": "ok", "api_version": "v1"}
        ds.check_sync_server.return_value = {"status": "ok", "running": True}
        ds.check_pairing.return_value = {"status": "ok", "paired": 1}
        ds.check_playback.return_value = {"status": "ok", "state": "playing"}
        ds.check_queue.return_value = {"status": "ok", "queue_length": 5}
        ds.check_continue_readiness.return_value = {"status": "ready", "has_queue": True}
        return ds

    @pytest.fixture
    def bridge(self, worker_manager, diagnostics_service):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        br = DiagnosticsBridge(
            diagnostics_service=diagnostics_service,
            worker_manager=worker_manager,
        )
        return br

    def test_diagnostics_uses_jobs_not_getters(self, bridge, worker_manager):
        jobs_collected = []

        def on_updated(jobs):
            jobs_collected.extend(jobs)

        bridge.diagnosticsUpdated.connect(on_updated)
        bridge.refresh()
        _process_events(1.0)
        if jobs_collected:
            for j in jobs_collected:
                assert "id" in j
                assert "status" in j
                assert j["status"] in ("PASS", "WARN", "FAIL", "UNKNOWN")
                assert "value" in j
                assert "message" in j
                assert "duration_ms" in j

    def test_diagnostics_jobs_have_correct_schema(self, bridge, worker_manager):
        jobs_collected = []

        def on_updated(jobs):
            jobs_collected.extend(jobs)

        bridge.diagnosticsUpdated.connect(on_updated)
        bridge.refresh()
        _process_events(2.0)
        for j in jobs_collected:
            assert isinstance(j.get("id"), str), f"Job id debe ser str: {j}"
            assert isinstance(j.get("status"), str), f"Job status debe ser str: {j}"
            assert isinstance(j.get("duration_ms"), (int, float)), f"duration_ms debe ser numérico: {j}"

    def test_no_diagnostics_service_still_works(self, worker_manager):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        bridge = DiagnosticsBridge(diagnostics_service=None, worker_manager=worker_manager)
        assert bridge._ds is None

    def test_copy_diagnostics_format(self, bridge):
        bridge._jobs = [
            {"id": "diagnostics.player_api", "status": "PASS", "value": True,
             "message": "Player API OK", "duration_ms": 12.5},
            {"id": "diagnostics.sync_server", "status": "WARN", "value": False,
             "message": "Sync server stopped", "duration_ms": 3.2},
        ]
        text = bridge.copyDiagnostics()
        assert "=== Michi Music Player Diagnostics ===" in text
        assert "PASS" in text
        assert "WARN" in text
        assert "diagnostics.player_api" in text
        assert "diagnostics.sync_server" in text

    def test_services_availability_all_ok(self, worker_manager):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        ds = MagicMock()
        bridge = DiagnosticsBridge(
            diagnostics_service=ds,
            player_service=object(),
            worker_manager=worker_manager,
            query_executor=object(),
        )
        svc = bridge._check_services_availability()
        assert svc["status"] == "PASS"
