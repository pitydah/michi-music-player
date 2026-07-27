"""DiscLabBridge — real disc detection, extraction, metadata, and progress.

NO simulates extraction.
Implements: device detection, disc state, track list, metadata, format,
destination, extraction, progress, cancel, error, dependency capability.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.disc_lab")


class DiscLabBridge(QObject):
    dataChanged = Signal()
    progressChanged = Signal(float, str)
    extractionComplete = Signal(dict)

    def __init__(self, disc_detection_service: Any = None, worker_manager=None, parent=None):
        super().__init__(parent)
        assert worker_manager is not None, "DiscLabBridge: worker_manager is REQUIRED"
        self._svc = disc_detection_service
        self._wm = worker_manager
        self._status = "unavailable"
        self._tracks: list[dict] = []
        self._drive_info = ""
        self._drives: list[str] = []
        self._extraction_progress = 0.0
        self._extraction_format = "flac"
        self._extraction_dest = ""
        self._dependencies_ok = False
        self._extraction_gen = 0

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def tracks(self):
        return list(self._tracks)

    @Property(str, notify=dataChanged)
    def driveInfo(self):
        return self._drive_info

    @Property("QVariantList", notify=dataChanged)
    def drives(self):
        return [{"device": d, "name": d} for d in self._drives]

    @Property(float, notify=progressChanged)
    def extractionProgress(self):
        return self._extraction_progress

    @Property(str, notify=progressChanged)
    def extractionFormat(self):
        return self._extraction_format

    @Property(bool, notify=dataChanged)
    def dependenciesOk(self):
        return self._dependencies_ok

    @Slot(result=dict)
    def refresh(self):
        self._check_dependencies()
        if not self._svc:
            self._status = "unavailable"
            self.dataChanged.emit()
            return {"ok": False, "error": "UNSUPPORTED", "dependencies_ok": self._dependencies_ok}
        try:
            if hasattr(self._svc, 'detect_drives'):
                drives = self._svc.detect_drives()
                self._drives = [d.device if hasattr(d, 'device') else str(d) for d in (drives or [])]
            else:
                self._drives = []
            if self._drives:
                default_drive = self._drives[0]
                if hasattr(self._svc, 'get_cd_info'):
                    info = self._svc.get_cd_info(default_drive)
                    self._status = "ready" if info else "no_disc"
                    if info:
                        self._toc = info
                else:
                    self._status = "ready"
                self._drive_info = default_drive
            else:
                self._status = "no_drive"
                self._drive_info = ""
        except Exception as e:
            logger.debug("Disc detection failed", exc_info=True)
            self._status = "error"
            self._drive_info = str(e)
        self.dataChanged.emit()
        return {"ok": True, "drives": len(self._drives), "dependencies_ok": self._dependencies_ok}

    def _check_dependencies(self):
        try:
            import importlib
            self._dependencies_ok = all((
                importlib.util.find_spec("mutagen") is not None,
            ))
        except Exception:
            self._dependencies_ok = False

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
            cd_info = self._svc.get_cd_info(drive) if hasattr(self._svc, 'get_cd_info') else None
            tracks_raw = []
            if cd_info and hasattr(cd_info, 'tracks'):
                tracks_raw = cd_info.tracks
            elif cd_info and isinstance(cd_info, dict) and 'tracks' in cd_info:
                tracks_raw = cd_info.get('tracks', [])
            self._tracks = [
                {"track": i + 1,
                 "title": getattr(t, 'title', None) or (t.get('title') if isinstance(t, dict) else f"Track {i+1}"),
                 "duration": int(getattr(t, 'duration', 0) or (t.get('duration', 0) if isinstance(t, dict) else 0)),
                 "selected": True}
                for i, t in enumerate(tracks_raw)
            ] if tracks_raw else [
                {"track": i + 1, "title": f"Track {i+1}",
                 "duration": 0, "selected": True}
                for i in range(getattr(cd_info, 'track_count', 0) or (cd_info.get('track_count', 0) if isinstance(cd_info, dict) else 0))
            ]
            self._status = "scanned" if self._tracks else "no_tracks"
            self.dataChanged.emit()
            return {"ok": True, "tracks": len(self._tracks)}
        except Exception as e:
            logger.debug("Disc scan failed", exc_info=True)
            self._status = "error"
            self.dataChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def setFormat(self, fmt: str):
        valid = {"flac", "wav", "mp3", "ogg"}
        if fmt.lower() in valid:
            self._extraction_format = fmt.lower()
            self.dataChanged.emit()
            return {"ok": True}
        return {"ok": False, "error": "INVALID_FORMAT"}

    @Slot(str, result=dict)
    def setDestination(self, path: str):
        if path:
            self._extraction_dest = path
            self.dataChanged.emit()
            return {"ok": True}
        return {"ok": False, "error": "EMPTY_PATH"}

    @Slot(result=dict)
    def startExtraction(self):
        if not self._svc or self._status not in ("scanned",):
            return {"ok": False, "error": "NOT_SCANNED"}
        if not self._tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if not self._extraction_dest:
            return {"ok": False, "error": "NO_DESTINATION"}

        selected_tracks = [t for t in self._tracks if t.get("selected", True)]
        if not selected_tracks:
            return {"ok": False, "error": "NO_TRACKS_SELECTED"}

        self._extraction_gen += 1
        gen = self._extraction_gen
        self._status = "extracting"
        self._extraction_progress = 0.0
        self.dataChanged.emit()
        self.progressChanged.emit(0.0, "Iniciando extracción...")

        if not self._wm:
            return {"ok": False, "error": "NO_WORKER_MANAGER"}

        drive = self._drive_info or (self._drives[0] if self._drives else "")
        fmt = self._extraction_format
        dest = self._extraction_dest
        track_nums = [t["track"] for t in selected_tracks]
        svc = self._svc

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            total = len(track_nums)
            results = []
            for idx, tn in enumerate(track_nums):
                ctx.token.raise_if_cancelled()
                ctx.report_progress((idx + 1) / total, f"Extrayendo pista {tn}...")
                try:
                    if hasattr(svc, 'rip_track'):
                        rip_result = svc.rip_track(drive, tn, dest, format=fmt)
                        if isinstance(rip_result, dict):
                            ok = rip_result.get("success", False)
                            out_path = rip_result.get("output_file", "")
                        else:
                            ok = False
                            out_path = ""
                        results.append({"track": tn, "ok": ok, "path": out_path})
                    else:
                        results.append({"track": tn, "ok": False, "error": "EXTRACT_NOT_IMPLEMENTED"})
                except Exception as e:
                    results.append({"track": tn, "ok": False, "error": str(e)})
            return {"tracks": results, "ok": True}

        def _on_done(result):
            if gen != self._extraction_gen:
                return
            self._status = "done"
            self._extraction_progress = 1.0
            self.progressChanged.emit(1.0, "Extracción completada")
            self.extractionComplete.emit(result)
            self.dataChanged.emit()

        def _on_error(code, msg):
            if gen != self._extraction_gen:
                return
            self._status = "error"
            self.progressChanged.emit(0.0, f"Error: {msg}")
            self.dataChanged.emit()

        def _on_cancelled():
            if gen != self._extraction_gen:
                return
            self._status = "cancelled"
            self.progressChanged.emit(0.0, "Extracción cancelada")
            self.dataChanged.emit()

        def _on_progress(pct, msg):
            if gen != self._extraction_gen:
                return
            self._extraction_progress = pct
            self.progressChanged.emit(pct, msg)

        self._wm.run_task(
            "disc_lab_extract", _task,
            pass_context=True, cancellable=True, owner="disc_lab",
            on_done=_on_done, on_error=_on_error,
            on_cancelled=_on_cancelled, on_progress=_on_progress,
        )
        return {"ok": True, "async": True}

    @Slot(result=dict)
    def cancelExtraction(self):
        if self._wm:
            self._wm.cancel_task("disc_lab_extract")
        self._status = "cancelled"
        self._extraction_progress = 0.0
        self.progressChanged.emit(0.0, "Cancelado")
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def cover(self):
        if not self._tracks:
            return {"ok": False, "error": "NO_DISC"}
        return {"ok": True, "message": "Cover search requires MusicBrainz provider (DEFERRED_PHYSICAL)"}

    @Slot(result=dict)
    def rip_plan(self):
        if not self._tracks:
            return {"ok": False, "error": "NO_DISC"}
        plan = {
            "tracks": len(self._tracks),
            "format": self._extraction_format,
            "destination": self._extraction_dest,
            "estimated_size_mb": len(self._tracks) * 50,
        }
        return {"ok": True, "plan": plan}

    @Slot(result=dict)
    def eject(self):
        drive = self._drive_info or (self._drives[0] if self._drives else "")
        hardware_ok = False
        if drive:
            try:
                result = subprocess.run(
                    ["eject", drive], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    hardware_ok = True
                else:
                    logger.warning(
                        "eject returned %d for %s: %s",
                        result.returncode, drive, result.stderr.decode().strip(),
                    )
            except (FileNotFoundError, TimeoutError, OSError) as exc:
                logger.warning("Hardware eject unavailable for %s: %s", drive, exc)
        else:
            logger.warning("No drive info available for eject")
        self._status = "no_disc"
        self._tracks = []
        self._extraction_progress = 0.0
        self.dataChanged.emit()
        if hardware_ok:
            return {"ok": True, "message": "Drive ejected"}
        return {"ok": True, "message": "State cleared (hardware eject unavailable)"}
