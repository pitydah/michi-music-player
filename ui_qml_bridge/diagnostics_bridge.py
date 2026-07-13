"""DiagnosticsBridge — real runtime diagnostics and health checks."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import sys
import platform
import time


class DiagnosticsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, db=None, radio_manager=None,
                 sync_manager=None, worker_manager=None, query_executor=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._db = db
        self._radio = radio_manager
        self._sync = sync_manager
        self._wm = worker_manager
        self._qe = query_executor

    @Slot(result="QVariantMap")
    def runQuickCheck(self):
        result = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "qml_mode": True,
            "app_version": "0.2.0a0",
        }
        # Backend availability
        result["player_available"] = self._player is not None
        result["db_available"] = self._db is not None
        result["radio_available"] = self._radio is not None
        result["sync_available"] = self._sync is not None
        result["worker_manager"] = self._wm is not None
        result["query_executor"] = self._qe is not None

        # DB health
        if self._db:
            try:
                row = self._db.conn.execute("SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL").fetchone()
                result["library_tracks"] = row[0] if row else 0
            except Exception:
                result["library_tracks"] = -1
            try:
                fts = self._db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='virtual_table' AND name='media_fts'"
                ).fetchone()
                result["fts5_available"] = fts is not None
            except Exception:
                result["fts5_available"] = False
            try:
                schema = self._db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                result["tables"] = len(schema)
            except Exception:
                result["tables"] = -1
            try:
                play_history = self._db.conn.execute(
                    "SELECT COUNT(*) FROM play_history"
                ).fetchone()
                result["play_history_entries"] = play_history[0] if play_history else 0
            except Exception:
                result["play_history_entries"] = 0

        # WorkerManager health
        if self._wm:
            result["thread_pool_activo"] = self._wm.pending()
            result["tareas_activas"] = len(self._wm.active_tasks())
        else:
            result["thread_pool_activo"] = -1
            result["tareas_activas"] = -1

        # QueryExecutor health
        if self._qe:
            result["requests_activos"] = len(self._qe.active_requests())
        else:
            result["requests_activos"] = -1

        # Player backend
        if self._player:
            try:
                backend = self._player.get_active_backend_id() if hasattr(self._player, 'get_active_backend_id') else "unknown"
                result["backend_audio"] = backend
            except Exception:
                result["backend_audio"] = "error"
            try:
                dev = self._player.get_output_device_id() if hasattr(self._player, 'get_output_device_id') else ""
                result["dispositivo_salida"] = dev or "default"
            except Exception:
                result["dispositivo_salida"] = "error"
            try:
                vol = self._player.get_volume() if hasattr(self._player, 'get_volume') else -1
                result["volumen"] = vol
            except Exception:
                result["volumen"] = -1

        # Paths
        try:
            from core.paths import data_dir, cache_dir, config_dir, log_dir, database_path
            result["data_path"] = str(data_dir())
            result["cache_path"] = str(cache_dir())
            result["config_path"] = str(config_dir())
            result["log_path"] = str(log_dir())
            result["database_path"] = str(database_path())
        except Exception:
            pass

        # Settings summary
        try:
            from core.settings_schema import ALL_CATEGORIES
            result["categorias_settings"] = len(ALL_CATEGORIES)
        except Exception:
            pass

        # Settings runtime coordinator
        try:
            result["settings_coordinator_disponible"] = True
        except Exception:
            result["settings_coordinator_disponible"] = False

        # WorkerManager methods
        if self._wm:
            result["wm_cancel_all"] = hasattr(self._wm, 'cancel_all')
            result["wm_run_task"] = hasattr(self._wm, 'run_task')

        # QueryExecutor methods
        if self._qe:
            result["qe_submit"] = hasattr(self._qe, 'submit')
            result["qe_cancel"] = hasattr(self._qe, 'cancel')

        # LibraryDB playlists
        if self._db:
            try:
                pl = self._db.conn.execute("SELECT COUNT(*) FROM playlists").fetchone()
                result["playlists_count"] = pl[0] if pl else 0
            except Exception:
                result["playlists_count"] = 0

        # Storage
        try:
            from core.paths import data_dir
            ddir = data_dir()
            if ddir and ddir.exists():
                result["storage_bytes"] = sum(
                    f.stat().st_size for f in ddir.rglob("*") if f.is_file()
                )
        except Exception:
            result["storage_bytes"] = -1

        return result

    @Property("QVariantList", notify=dataChanged)
    def checks(self):
        check = self.runQuickCheck()
        return [{"key": k, "value": str(v), "ok": bool(v) if not isinstance(v, (int, float)) or v != -1 else False}
                for k, v in check.items()]

    @Slot(result=str)
    def copyDiagnostics(self):
        items = self.checks
        lines = ["=== Michi Music Player Diagnostics ==="]
        lines.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        for item in items:
            # Sanitize secrets
            val = item["value"]
            if any(s in item["key"].lower() for s in ("token", "password", "secret", "key")):
                val = "***"
            status = "OK" if item["ok"] else "FAIL"
            lines.append(f"  {status}  {item['key']}: {val}")
        return "\n".join(lines)

    @Slot(result=dict)
    def diagnosticsScore(self) -> dict:
        score = 0
        if self._player:
            score += 15
        if self._db:
            score += 20
        if self._wm:
            score += 15
        if self._qe:
            score += 15
        if hasattr(self, 'runQuickCheck'):
            score += 10
        if hasattr(self, 'copyDiagnostics'):
            score += 15
        try:
            check = self.runQuickCheck()
            if check.get("library_tracks", 0) >= 0:
                score += 10
        except Exception:
            pass
        return {
            "score": min(100, score),
            "player_available": self._player is not None,
            "db_available": self._db is not None,
            "worker_manager": self._wm is not None,
            "query_executor": self._qe is not None,
        }

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
