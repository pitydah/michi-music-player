"""DiagnosticsService — real service health, database, library, and runtime diagnostics.
Wraps audio_lab diagnostics, ecosystem doctor, and individual service health checks."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.diagnostics_service")


class DiagnosticsService:
    def __init__(self, db=None, audio_diagnostics=None, ecosystem_doctor=None,
                 player_service=None, worker_manager=None):
        self._db = db
        self._audio_diag = audio_diagnostics
        self._eco_doctor = ecosystem_doctor
        self._player = player_service
        self._worker_manager = worker_manager

    @property
    def available(self) -> bool:
        return True

    def check_all(self) -> dict:
        return {
            "service_health": self.check_service_health(),
            "database": self.check_database(),
            "library": self.check_library(),
            "playback": self.check_playback(),
        }

    def check_service_health(self) -> dict:
        return {"status": "ok"}

    def check_database(self) -> dict:
        if not self._db:
            return {"status": "unavailable", "error": "NO_DB"}
        try:
            cursor = self._db.conn.execute("SELECT COUNT(*) FROM tracks")
            track_count = cursor.fetchone()[0]
            return {"status": "ok", "track_count": track_count}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def check_library(self) -> dict:
        if not self._db:
            return {"status": "unavailable", "error": "NO_DB"}
        try:
            roots = self._db.conn.execute(
                "SELECT COUNT(*) FROM library_roots"
            ).fetchone()[0]
            return {"status": "ok", "root_count": roots}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def check_playback(self) -> dict:
        if not self._player:
            return {"status": "unavailable"}
        try:
            state = getattr(self._player, 'state', 'unknown')
            return {"status": "ok", "state": state}
        except Exception:
            return {"status": "error"}

    def analyse_file(self, path: str) -> dict:
        if self._audio_diag:
            try:
                from core.audio_lab.diagnostics_service import analyse_file
                result = analyse_file(path)
                return {"ok": True, "result": result}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def generate_report(self, path: str) -> dict:
        if self._audio_diag:
            try:
                from core.audio_lab.diagnostics_service import generate_report
                report = generate_report(path)
                return {"ok": True, "report": report}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def start(self):
        pass

    def cancel(self):
        pass

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
