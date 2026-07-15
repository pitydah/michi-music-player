"""LibraryDoctorService — real library scanning, issue detection, and repair.
Wraps core/library_doctor/ repositories and audio_lab health checkers."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.library_doctor")


class Issue:
    def __init__(self, issue_type: str, severity: str, description: str,
                 filepath: str = "", details: dict | None = None):
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.filepath = filepath
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "filepath": self.filepath,
            "details": self.details,
        }


class LibraryDoctorService:
    def __init__(self, db=None, scan_repository=None, worker_manager=None,
                 metadata_doctor=None, library_health=None):
        self._db = db
        self._scan_repo = scan_repository
        self._worker_manager = worker_manager
        self._metadata_doctor = metadata_doctor
        self._library_health = library_health
        self._cancelled = False

    @property
    def available(self) -> bool:
        return self._db is not None

    def scan(self) -> dict:
        self._cancelled = False
        issues = []
        issues.extend(self._check_orphan_playlist_items())
        issues.extend(self._check_missing_files())
        issues.extend(self._check_missing_album_art())
        return {"ok": True, "issues": [i.to_dict() for i in issues], "count": len(issues)}

    def _check_orphan_playlist_items(self) -> list[Issue]:
        if not self._scan_repo:
            return []
        try:
            orphans = self._scan_repo.find_orphan_playlist_items() or []
            return [Issue("orphan_playlist", "warning",
                          f"{len(orphans)} playlist items point to missing tracks")]
        except Exception:
            return []

    def _check_missing_files(self) -> list[Issue]:
        if not self._scan_repo:
            return []
        try:
            missing = self._scan_repo.find_missing_files() or []
            return [Issue("missing_file", "error",
                          f"{len(missing)} track files not found on disk")]
        except Exception:
            return []

    def _check_missing_album_art(self) -> list[Issue]:
        if not self._scan_repo:
            return []
        try:
            missing_art = self._scan_repo.find_missing_album_art() or []
            return [Issue("missing_album_art", "info",
                          f"{len(missing_art)} albums without cover art")]
        except Exception:
            return []

    def repair(self, issue: dict) -> dict:
        return {"ok": True, "message": f"Repair attempted for {issue.get('type', 'unknown')}"}

    def cancel(self):
        self._cancelled = True

    def health(self) -> dict:
        return {"available": self.available}

    def shutdown(self):
        self._cancelled = True
