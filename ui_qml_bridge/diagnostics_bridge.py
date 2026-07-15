"""DiagnosticsBridge — real runtime diagnostics via DiagnosticsService + async jobs.

Diagnostics MUST NOT: query SQL from getters, walk storage from UI thread,
run pytest from QML, or run benchmarks from QML.
"""
from __future__ import annotations

import platform
import sys
import time
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot


class DiagnosticsBridge(QObject):
    dataChanged = Signal()
    diagnosticsUpdated = Signal(list)

    def __init__(self, diagnostics_service=None, player_service=None,
                 worker_manager=None, query_executor=None,
                 library_bridge=None, parent=None):
        super().__init__(parent)
        self._ds = diagnostics_service
        self._player = player_service
        self._wm = worker_manager
        self._qe = query_executor
        self._lib = library_bridge
        self._jobs: list[dict] = []
        self._env_info: dict[str, Any] = {}

    @Property("QVariantList", notify=diagnosticsUpdated)
    def jobs(self):
        return list(self._jobs)

    @Slot(result=dict)
    def refresh(self):
        self._env_info = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "qml_mode": True,
            "app_version": "0.2.0a0",
        }
        self.dataChanged.emit()
        self._run_all_jobs()
        return {"ok": True}

    def _run_all_jobs(self):
        if not self._wm:
            self._jobs = [{"id": "worker.unavailable", "status": "FAIL",
                           "value": False, "message": "WorkerManager no disponible",
                           "duration_ms": 0}]
            self.diagnosticsUpdated.emit(self._jobs)
            return

        self._jobs = []
        self.diagnosticsUpdated.emit(self._jobs)

        checks = [
            ("diagnostics.player_api", self._check_player_api),
            ("diagnostics.sync_server", self._check_sync_server),
            ("diagnostics.pairing", self._check_pairing),
            ("diagnostics.playback", self._check_playback),
            ("diagnostics.queue", self._check_queue),
            ("diagnostics.continue_readiness", self._check_continue_readiness),
        ]

        if self._ds:
            for job_id, check_fn in checks:
                self._schedule_job(job_id, check_fn)

        self._schedule_job("services.availability", self._check_services_availability)

    def _schedule_job(self, job_id: str, check_fn):
        started = time.time()

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            return check_fn()

        def _on_done(result):
            elapsed = (time.time() - started) * 1000
            job = {
                "id": job_id,
                "status": result.get("status", "UNKNOWN"),
                "value": result.get("value"),
                "message": result.get("message", ""),
                "duration_ms": round(elapsed, 1),
            }
            self._jobs.append(job)
            self.diagnosticsUpdated.emit(self._jobs)

        def _on_error(code, msg):
            elapsed = (time.time() - started) * 1000
            job = {
                "id": job_id,
                "status": "FAIL",
                "value": None,
                "message": msg or code,
                "duration_ms": round(elapsed, 1),
            }
            self._jobs.append(job)
            self.diagnosticsUpdated.emit(self._jobs)

        self._wm.run_task(
            f"diag_{job_id}", _task,
            pass_context=True, cancellable=True, owner="diagnostics",
            on_done=_on_done, on_error=_on_error,
        )

    def _check_player_api(self) -> dict:
        if not self._ds:
            return {"status": "FAIL", "value": False, "message": "DiagnosticsService no disponible"}
        try:
            result = self._ds.check_player_api()
            ok = result.get("status") == "ok"
            return {"status": "PASS" if ok else "WARN", "value": ok,
                    "message": f"Player API: {result.get('status', 'unknown')}"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_sync_server(self) -> dict:
        if not self._ds:
            return {"status": "FAIL", "value": False, "message": "DiagnosticsService no disponible"}
        try:
            result = self._ds.check_sync_server()
            ok = result.get("status") == "ok"
            return {"status": "PASS" if ok else "WARN", "value": ok,
                    "message": f"Sync server: {result.get('status', 'unknown')}"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_pairing(self) -> dict:
        if not self._ds:
            return {"status": "FAIL", "value": False, "message": "DiagnosticsService no disponible"}
        try:
            result = self._ds.check_pairing()
            ok = result.get("status") == "ok"
            return {"status": "PASS" if ok else "WARN", "value": ok,
                    "message": f"Pairing: {result.get('paired', 0)} dispositivos"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_playback(self) -> dict:
        if not self._ds:
            return {"status": "FAIL", "value": False, "message": "DiagnosticsService no disponible"}
        try:
            result = self._ds.check_playback(self._player)
            ok = result.get("status") == "ok"
            return {"status": "PASS" if ok else "WARN", "value": ok,
                    "message": f"Playback: {result.get('state', 'unknown')}"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_queue(self) -> dict:
        if not self._ds:
            return {"status": "FAIL", "value": False, "message": "DiagnosticsService no disponible"}
        try:
            result = self._ds.check_queue(self._player)
            ok = result.get("status") == "ok"
            return {"status": "PASS" if ok else "WARN", "value": ok,
                    "message": f"Queue: {result.get('queue_length', 0)} pistas"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_continue_readiness(self) -> dict:
        if not self._ds:
            return {"status": "FAIL", "value": False, "message": "DiagnosticsService no disponible"}
        try:
            result = self._ds.check_continue_readiness(self._player)
            ok = result.get("status") == "ready"
            return {"status": "PASS" if ok else "WARN", "value": ok,
                    "message": f"Continue: {result.get('status', 'unknown')}"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_storage_paths(self) -> dict:
        try:
            from core.paths import data_dir, cache_dir, config_dir, database_path
            str(data_dir()), str(cache_dir()), str(config_dir()), str(database_path())
            return {"status": "PASS", "value": True, "message": "Rutas de almacenamiento OK"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_services_availability(self) -> dict:
        services = {
            "diagnostics_service": self._ds is not None,
            "player": self._player is not None,
            "worker_manager": self._wm is not None,
            "query_executor": self._qe is not None,
        }
        ok = sum(1 for v in services.values() if v)
        total = len(services)
        if ok == total:
            return {"status": "PASS", "value": ok, "message": f"{ok}/{total} servicios disponibles"}
        if ok == 0:
            return {"status": "FAIL", "value": 0, "message": "Ningún servicio disponible"}
        return {"status": "WARN", "value": ok, "message": f"{ok}/{total} servicios disponibles"}

    @Slot(result=str)
    def copyDiagnostics(self):
        lines = ["=== Michi Music Player Diagnostics ==="]
        lines.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        for j in self._jobs:
            lines.append(f"  {j['status']}  {j['id']}: {j['message']} ({j['duration_ms']}ms)")
        return "\n".join(lines)

    @property
    def query_executor(self):
        return self._qe
