"""FolderService — folder scanning, integrity checks, safe operations."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("michi.folder_service")


class FolderService:
    def __init__(self, db=None, worker_manager=None):
        self._db = db
        self._wm = worker_manager

    def scan(self, path: str) -> dict:
        if not path or not os.path.isdir(path):
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            added = 0
            for root, _dirs, files in os.walk(path):
                if any(d.startswith(".") for d in root.split(os.sep)):
                    continue
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".flac", ".mp3", ".wav", ".ogg", ".opus",
                               ".m4a", ".wv", ".ape", ".dsf", ".dff", ".aiff"):
                        fp = os.path.join(root, f)
                        if self._db.add_file(fp):
                            added += 1
            return {"ok": True, "added": added}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def integrity_check(self, path: str) -> dict:
        issues = []
        if not path or not os.path.isdir(path):
            return {"ok": False, "error": "INVALID_PATH"}
        try:
            for root, _dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    if not os.access(fp, os.R_OK):
                        issues.append({"path": fp, "issue": "NOT_READABLE"})
            return {"ok": True, "issues": issues, "count": len(issues)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
