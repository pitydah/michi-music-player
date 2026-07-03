"""DiscLabBridge — connects QML Disc Lab page to real disc detection services."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.disc_lab")


class DiscLabBridge(QObject):
    dataChanged = Signal()

    def __init__(self, disc_service=None, parent=None):
        super().__init__(parent)
        self._disc_svc = disc_service
        self._status = "unavailable"
        self._tracks = []
        self._drive_info = ""

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def tracks(self):
        return self._tracks

    @Property(str, notify=dataChanged)
    def driveInfo(self):
        return self._drive_info

    @Slot()
    def refresh(self):
        if self._disc_svc and hasattr(self._disc_svc, 'detect_drive'):
            try:
                info = self._disc_svc.detect_drive()
                if info:
                    self._drive_info = info.get("name", "") or info.get("device", "") or "Unidad detectada"
                    self._status = "ready"
                else:
                    self._drive_info = ""
                    self._status = "no_disc"
            except Exception:
                logger.debug("Disc detection failed", exc_info=True)
                self._status = "error"
        else:
            self._status = "unavailable"
        self.dataChanged.emit()

    @Slot()
    def scanDisc(self):
        if self._status != "ready":
            return
        self._status = "scanning"
        self.dataChanged.emit()
        try:
            if self._disc_svc and hasattr(self._disc_svc, 'scan_disc'):
                tracks = self._disc_svc.scan_disc()
                self._tracks = [
                    {"track": i + 1, "title": t.get("title", f"Track {i+1}") if isinstance(t, dict) else f"Track {i+1}"}
                    for i, t in enumerate(tracks or [])
                ]
                self._status = "scanned" if self._tracks else "no_tracks"
            else:
                self._status = "unavailable"
        except Exception:
            logger.debug("Disc scan failed", exc_info=True)
            self._status = "error"
        self.dataChanged.emit()
