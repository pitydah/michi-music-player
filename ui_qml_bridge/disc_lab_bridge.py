"""DiscLabBridge — connects QML Disc Lab page to DiscDetectionService."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
from typing import Any

logger = logging.getLogger("michi.disc_lab")


class DiscLabBridge(QObject):
    dataChanged = Signal()

    def __init__(self, disc_detection_service: Any = None, parent=None):
        super().__init__(parent)
        self._svc = disc_detection_service
        self._status = "unavailable"
        self._tracks: list[dict] = []
        self._drive_info = ""
        self._drives: list[str] = []

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def tracks(self):
        return self._tracks

    @Property(str, notify=dataChanged)
    def driveInfo(self):
        return self._drive_info

    @Property("QVariantList", notify=dataChanged)
    def drives(self):
        return [{"device": d, "name": d} for d in self._drives]

    @Slot(result=dict)
    def refresh(self):
        if not self._svc:
            self._status = "unavailable"
            self.dataChanged.emit()
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            drives = self._svc.detect_drives()
            self._drives = drives or []
            if drives:
                default_drive = self._svc.get_default_drive() or drives[0]
                has_cd = self._svc.detect_audio_cd(default_drive)
                self._status = "ready" if has_cd else "no_disc"
                self._drive_info = default_drive
            else:
                self._status = "no_drive"
                self._drive_info = ""
        except Exception as e:
            logger.debug("Disc detection failed", exc_info=True)
            self._status = "error"
            self._drive_info = str(e)
        self.dataChanged.emit()
        return {"ok": True, "drives": len(self._drives)}

    @Slot(result=dict)
    def scanDisc(self):
        if not self._svc or self._status not in ("ready",):
            return {"ok": False, "error": "NO_DISC"}
        self._status = "scanning"
        self.dataChanged.emit()
        try:
            drive = self._drive_info or (self._drives[0] if self._drives else "")
            if not drive:
                self._status = "no_drive"
                self.dataChanged.emit()
                return {"ok": False, "error": "NO_DRIVE"}
            toc = self._svc.get_disc_toc(drive)
            track_count = toc.get("tracks", 0) if isinstance(toc, dict) else 0
            durations = self._svc.get_track_durations(drive) if hasattr(self._svc, 'get_track_durations') else []
            self._tracks = [
                {"track": i + 1, "title": f"Track {i+1}", "duration": durations[i] if i < len(durations) else 0}
                for i in range(track_count)
            ]
            self._status = "scanned" if self._tracks else "no_tracks"
            self.dataChanged.emit()
            return {"ok": True, "tracks": len(self._tracks)}
        except Exception as e:
            logger.debug("Disc scan failed", exc_info=True)
            self._status = "error"
            self.dataChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def eject(self):
        self._status = "no_disc"
        self._tracks = []
        self.dataChanged.emit()
        return {"ok": True}
