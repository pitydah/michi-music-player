"""DiagnosticsBridge — real runtime diagnostics via async jobs.

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

    def __init__(self, player_service=None, db=None, radio_manager=None,
                 sync_manager=None, worker_manager=None, query_executor=None,
                 library_bridge=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._db = db
        self._radio = radio_manager
        self._sync = sync_manager
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
            ("database.integrity", self._check_db_integrity),
            ("library.status", self._check_library_status),
            ("player.status", self._check_player_status),
            ("storage.paths", self._check_storage_paths),
            ("services.availability", self._check_services_availability),
        ]

        for job_id, check_fn in checks:
            self._schedule_job(job_id, check_fn)

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

    def _check_db_integrity(self) -> dict:
        if not self._db:
            return {"status": "FAIL", "value": False, "message": "Base de datos no disponible"}
        try:
            conn = getattr(self._db, 'conn', None)
            if conn is None:
                return {"status": "FAIL", "value": False, "message": "Conexión BD no disponible"}
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if row and row[0] == "ok":
                count = conn.execute(
                    "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL"
                ).fetchone()
                total = count[0] if count else 0
                return {"status": "PASS", "value": total, "message": f"Integridad OK · {total} pistas"}
            return {"status": "WARN", "value": False, "message": f"Integridad: {row[0] if row else 'desconocida'}"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_library_status(self) -> dict:
        if not self._db:
            return {"status": "FAIL", "value": False, "message": "Base de datos no disponible"}
        try:
            conn = getattr(self._db, 'conn', None)
            if conn is None:
                return {"status": "FAIL", "value": False, "message": "Conexión BD no disponible"}
            count = conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL"
            ).fetchone()
            total = count[0] if count else 0
            if total == 0:
                return {"status": "WARN", "value": 0, "message": "Biblioteca vacía"}
            missing = conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL AND "
                "(title IS NULL OR title = '' OR artist IS NULL OR artist = '')"
            ).fetchone()
            missing_count = missing[0] if missing else 0
            if missing_count > 0:
                return {"status": "WARN", "value": total,
                        "message": f"{total} pistas · {missing_count} con metadatos incompletos"}
            return {"status": "PASS", "value": total, "message": f"{total} pistas · OK"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_player_status(self) -> dict:
        if not self._player:
            return {"status": "WARN", "value": False, "message": "Player no disponible"}
        try:
            backend = "unknown"
            if hasattr(self._player, 'get_active_backend_id'):
                backend = self._player.get_active_backend_id()
            volume = -1
            if hasattr(self._player, 'get_volume'):
                volume = self._player.get_volume()
            return {"status": "PASS", "value": True,
                    "message": f"Backend: {backend} · Vol: {volume}"}
        except Exception as e:
            return {"status": "WARN", "value": False, "message": str(e)}

    def _check_storage_paths(self) -> dict:
        try:
            from core.paths import data_dir, cache_dir, config_dir, database_path
            str(data_dir()), str(cache_dir()), str(config_dir()), str(database_path())
            return {"status": "PASS", "value": True, "message": "Rutas de almacenamiento OK"}
        except Exception as e:
            return {"status": "FAIL", "value": False, "message": str(e)}

    def _check_services_availability(self) -> dict:
        services = {
            "db": self._db is not None,
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
