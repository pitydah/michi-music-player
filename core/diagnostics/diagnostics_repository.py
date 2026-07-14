from __future__ import annotations

import logging

logger = logging.getLogger("michi.diagnostics.repository")


class DiagnosticsRepository:
    def __init__(self, db=None):
        self._db = db

    def _conn(self):
        if self._db is None:
            return None
        return getattr(self._db, 'conn', None)

    def check_integrity(self) -> dict:
        conn = self._conn()
        if conn is None:
            return {"status": "FAIL", "value": False, "message": "Base de datos no disponible"}
        try:
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

    def library_status(self) -> dict:
        conn = self._conn()
        if conn is None:
            return {"status": "FAIL", "value": False, "message": "Base de datos no disponible"}
        try:
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
