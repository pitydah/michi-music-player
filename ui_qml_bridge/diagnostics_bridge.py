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
            "player_available": self._player is not None,
            "db_available": self._db is not None,
            "radio_available": self._radio is not None,
            "sync_available": self._sync is not None,
        }
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
        # WorkerManager health
        if self._wm:
            result["thread_pool_active"] = self._wm.pending()
            result["active_tasks"] = len(self._wm.active_tasks())
        # Player backend
        if self._player:
            try:
                backend = self._player.get_active_backend_id() if hasattr(self._player, 'get_active_backend_id') else "unknown"
                result["audio_backend"] = backend
            except Exception:
                result["audio_backend"] = "error"
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
            status = "OK" if item["ok"] else "FAIL"
            lines.append(f"  {status}  {item['key']}: {item['value']}")
        return "\n".join(lines)

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
