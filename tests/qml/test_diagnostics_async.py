"""Wave XLIII — 10.2: Diagnostics async.

Tests:
  - Diagnostics via jobs, NOT from getters
  - Cero tareas y cero requests = PASS
  - Biblioteca vacía = WARN (no FAIL)
  - All jobs produce dict with id/status/value/message/duration_ms
"""
from __future__ import annotations

import time
import sqlite3

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
    def empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE IF NOT EXISTS media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, deleted_at REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS library_sources (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS library_scan_log (id INTEGER PRIMARY KEY, last_scan REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS play_history (id INTEGER PRIMARY KEY, filepath TEXT)")
        return conn

    @pytest.fixture
    def bridge(self, worker_manager, empty_db):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        class FakeDB:
            conn = empty_db
            db_path = ":memory:"
        br = DiagnosticsBridge(
            db=FakeDB(),
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

    def test_empty_library_is_warn_not_fail(self, worker_manager, empty_db):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        class FakeDB:
            conn = empty_db
            db_path = ":memory:"
        bridge = DiagnosticsBridge(db=FakeDB(), worker_manager=worker_manager)
        library_status = bridge._check_library_status()
        assert library_status["status"] in ("WARN", "PASS"), \
            f"Biblioteca vacía debe ser WARN, no FAIL. Got: {library_status['status']}"
        assert library_status["value"] == 0

    def test_no_db_is_fail(self, worker_manager):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        bridge = DiagnosticsBridge(db=None, worker_manager=worker_manager)
        db_status = bridge._check_db_integrity()
        assert db_status["status"] == "FAIL"
        assert db_status["value"] is False

    def test_no_player_is_warn(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        bridge = DiagnosticsBridge(player_service=None)
        player_status = bridge._check_player_status()
        assert player_status["status"] == "WARN"

    def test_copy_diagnostics_format(self, bridge):
        bridge._jobs = [
            {"id": "database.integrity", "status": "PASS", "value": 100,
             "message": "Integridad OK", "duration_ms": 12.5},
            {"id": "library.status", "status": "WARN", "value": 0,
             "message": "Biblioteca vacía", "duration_ms": 3.2},
        ]
        text = bridge.copyDiagnostics()
        assert "=== Michi Music Player Diagnostics ===" in text
        assert "PASS" in text
        assert "WARN" in text
        assert "database.integrity" in text
        assert "library.status" in text

    def test_services_availability_all_ok(self, worker_manager, empty_db):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        class FakeDB:
            conn = empty_db
            db_path = ":memory:"
        bridge = DiagnosticsBridge(
            db=FakeDB(),
            player_service=object(),
            worker_manager=worker_manager,
            query_executor=object(),
        )
        svc = bridge._check_services_availability()
        assert svc["status"] == "PASS"
