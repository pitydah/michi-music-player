"""LibrarySourcesService — agnóstico de UI, gestiona carpetas de biblioteca.

Lee desde settings_manager. No crea otra base de datos.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("michi.library_sources")


class LibrarySource:
    def __init__(self, path: str, enabled: bool = True,
                 network: bool = False, removable: bool = False):
        self.path = path
        self.enabled = enabled
        self.network = network
        self.removable = removable
        self.last_scan: float = 0.0
        self.available: bool = Path(path).is_dir() if path else False

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "enabled": self.enabled,
            "network": self.network,
            "removable": self.removable,
            "available": self.available,
            "last_scan": self.last_scan,
        }


class LibrarySourcesService:
    def __init__(self):
        self._sources: list[LibrarySource] = []
        self._load()

    def _load(self):
        try:
            from core.settings_manager import get
            folder = get("general/music_folder")
            if folder and folder not in [s.path for s in self._sources]:
                self._sources.append(LibrarySource(path=folder))
        except Exception:
            default = str(Path.home() / "Música")
            if default not in [s.path for s in self._sources]:
                self._sources.append(LibrarySource(path=default))

    def list(self) -> list[dict]:
        return [s.to_dict() for s in self._sources]

    def add(self, path: str) -> dict:
        p = Path(path)
        if not p.is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        if any(s.path == path for s in self._sources):
            return {"ok": False, "error": "ALREADY_EXISTS"}
        self._sources.append(LibrarySource(path=path))
        self._save()
        return {"ok": True}

    def remove(self, path: str) -> dict:
        before = len(self._sources)
        self._sources = [s for s in self._sources if s.path != path]
        if len(self._sources) == before:
            return {"ok": False, "error": "NOT_FOUND"}
        self._save()
        return {"ok": True}

    def enable(self, path: str, enabled: bool) -> dict:
        for s in self._sources:
            if s.path == path:
                s.enabled = enabled
                self._save()
                return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    def root_paths(self) -> list[str]:
        return [s.path for s in self._sources if s.enabled and s.available]

    def _save(self):
        try:
            from core.settings_manager import set_
            paths = [s.path for s in self._sources]
            set_("library/source_paths", paths)
        except Exception:
            pass
