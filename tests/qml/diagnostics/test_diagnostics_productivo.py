"""EF — Diagnostics: service health, DB, library, playback, Queue, Jobs, AudioLab,
Devices, Connections, HomeAudio, Settings, logs, support bundle.
No SQL ni benchmarks en bridge."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge


@pytest.fixture
def wm():
    wm = MagicMock()
    wm.run_task.return_value = MagicMock()
    return wm


@pytest.fixture
def bridge(wm):
    return DiagnosticsBridge(worker_manager=wm)


class TestDiagnosticsInitialState:
    def test_initial_jobs_empty(self, bridge):
        assert bridge.jobs == []

    def test_initial_env_empty(self, bridge):
        assert bridge._env_info == {}

    def test_refresh_returns_ok(self, bridge, wm):
        result = bridge.refresh()
        assert result["ok"] is True


class TestServiceHealth:
    def test_service_health_player(self):
        bridge = DiagnosticsBridge(player_service=MagicMock())
        result = bridge._check_player_status()
        assert result["status"] in ("PASS", "WARN", "FAIL")

    def test_service_health_no_player(self, bridge):
        result = bridge._check_player_status()
        assert result["status"] == "WARN"

    def test_services_availability_all_present(self):
        bridge = DiagnosticsBridge(
            player_service=MagicMock(), worker_manager=MagicMock(),
            query_executor=MagicMock(), db=MagicMock(),
        )
        result = bridge._check_services_availability()
        assert result["status"] == "PASS"

    def test_services_availability_only_wm(self, bridge):
        result = bridge._check_services_availability()
        assert result["status"] == "WARN"
        assert result["value"] == 1


class TestDBHealth:
    def test_db_integrity_no_db(self, bridge):
        result = bridge._check_db_integrity()
        assert result["status"] == "FAIL"

    def test_db_integrity_with_conn(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, deleted_at REAL)")
        fake_db = type("FakeDB", (), {"conn": conn})()
        bridge = DiagnosticsBridge(db=fake_db)
        result = bridge._check_db_integrity()
        assert result["status"] == "PASS"

    def test_library_status_no_db(self, bridge):
        result = bridge._check_library_status()
        assert result["status"] == "FAIL"

    def test_library_status_with_tracks(self):
        import sqlite3
import pytest
pytestmark = [pytest.mark.qml_module("diagnostics")]

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, deleted_at REAL)")
        conn.execute("INSERT INTO media_items (filepath, title, artist) VALUES ('/a.mp3', 'A', 'X')")
        fake_db = type("FakeDB", (), {"conn": conn})()
        bridge = DiagnosticsBridge(db=fake_db)
        result = bridge._check_library_status()
        assert result["status"] == "PASS"


class TestStoragePaths:
    def test_storage_paths_ok(self, bridge):
        result = bridge._check_storage_paths()
        assert result["status"] in ("PASS", "FAIL")


class TestSupportBundle:
    def test_copy_diagnostics_returns_string(self, bridge):
        bridge._jobs = [
            {"status": "PASS", "id": "database.integrity", "message": "OK", "duration_ms": 10},
            {"status": "PASS", "id": "player.status", "message": "OK", "duration_ms": 5},
        ]
        text = bridge.copyDiagnostics()
        assert "Michi Music Player Diagnostics" in text
        assert "database.integrity" in text

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


class DiagnosticsCheck:
    pass
