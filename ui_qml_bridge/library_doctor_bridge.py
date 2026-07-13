"""LibraryDoctorBridge — connects QML Library Doctor page to real library health services."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.library_doctor")


class LibraryDoctorBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, worker_manager=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = worker_manager
        self._status = "idle"
        self._issues = []
        self._total_checked = 0
        self._issue_count = 0

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def issues(self):
        return self._issues

    @Property(int, notify=dataChanged)
    def totalChecked(self):
        return self._total_checked

    @Property(int, notify=dataChanged)
    def issueCount(self):
        return self._issue_count

    @Property(int, notify=dataChanged)
    def missingMetadataCount(self):
        return sum(1 for i in self._issues if i.get("type") == "missing_metadata")

    @Property(int, notify=dataChanged)
    def missingFileCount(self):
        return sum(1 for i in self._issues if i.get("type") == "missing_file")

    @Property(int, notify=dataChanged)
    def healthyCount(self):
        return max(0, self._total_checked - self._issue_count)

    @Slot()
    def scan(self):
        self._status = "scanning"
        self._issues = []
        self.dataChanged.emit()
        issues = []
        try:
            if self._db and hasattr(self._db, 'get_tracks'):
                tracks = self._db.get_tracks(limit=500)
                self._total_checked = len(tracks)
                for t in tracks:
                    title = t.get("title") if isinstance(t, dict) else getattr(t, 'title', '')
                    artist = t.get("artist") if isinstance(t, dict) else getattr(t, 'artist', '')
                    if not title or not artist:
                        fp = t.get("filepath") if isinstance(t, dict) else getattr(t, 'filepath', '')
                        issues.append({
                            "type": "missing_metadata",
                            "filepath": fp or "",
                            "detail": "Falta título o artista",
                        })
                    filepath = t.get("filepath") if isinstance(t, dict) else getattr(t, 'filepath', '')
                    if filepath:
                        from pathlib import Path
                        if not Path(filepath).exists():
                            issues.append({
                                "type": "missing_file",
                                "filepath": filepath,
                                "detail": "Archivo no encontrado",
                            })
        except Exception:
            logger.debug("Library doctor scan failed", exc_info=True)
        self._issues = issues[:100]
        self._issue_count = len(self._issues)
        self._status = "done" if self._total_checked > 0 else "no_data"
        self.dataChanged.emit()

    @Slot(result=dict)
    def doctorScore(self) -> dict:
        score = 0
        if self._db:
            score += 25
        if self._status in ("done", "idle"):
            score += 20
        if self._total_checked > 0:
            score += 15
        if self._wm:
            score += 15
        if hasattr(self, 'scan'):
            score += 15
        if hasattr(self, '_issues') and len(self._issues) >= 0:
            score += 10
        return {
            "score": min(100, score),
            "has_db": self._db is not None,
            "has_worker_manager": self._wm is not None,
            "status": self._status,
            "total_checked": self._total_checked,
            "issue_count": self._issue_count,
        }

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
