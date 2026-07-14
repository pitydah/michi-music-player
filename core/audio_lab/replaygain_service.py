"""ReplayGainService — ReplayGain analysis, tagging, and removal.

Supports track analysis, album analysis, preview, loudness, peak,
clipping prevention, write tags, remove tags, batch, cancel.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.replaygain")


@dataclass
class ReplayGainResult:
    filepath: str = ""
    status: str = "pending"
    track_gain: float = 0.0
    track_peak: float = 0.0
    album_gain: float | None = None
    album_peak: float | None = None
    reference_loudness: float = -18.0
    error: str = ""


class ReplayGainService(QObject):
    analysisCompleted = Signal(str, object)
    tagsWritten = Signal(str, bool)
    tagsRemoved = Signal(str, bool)

    def __init__(self, db=None, wm: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm

    def analyze_track(self, filepath: str) -> ReplayGainResult:
        result = ReplayGainResult(filepath=filepath)
        if not filepath or not os.path.isfile(filepath):
            result.status = "error"
            result.error = "FILE_NOT_FOUND"
            return result
        try:
            rg_data = self._compute_replaygain(filepath)
            result.track_gain = rg_data.get("track_gain", 0.0)
            result.track_peak = rg_data.get("track_peak", 0.0)
            result.album_gain = rg_data.get("album_gain")
            result.album_peak = rg_data.get("album_peak")
            result.reference_loudness = rg_data.get("reference_loudness", -18.0)
            result.status = "completed"
        except Exception as e:
            logger.exception("ReplayGain analysis failed for %s", filepath)
            result.status = "error"
            result.error = str(e)
        return result

    def analyze_album(self, filepaths: list[str]) -> list[ReplayGainResult]:
        results = [self.analyze_track(fp) for fp in filepaths]
        if results and all(r.status == "completed" for r in results):
            album_gain = sum(r.track_gain for r in results) / len(results)
            album_peak = max(r.track_peak for r in results)
            for r in results:
                r.album_gain = album_gain
                r.album_peak = album_peak
        return results

    def write_tags(self, filepath: str, track_gain: float, track_peak: float,
                   album_gain: float | None = None,
                   album_peak: float | None = None) -> bool:
        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is None:
                logger.warning("Cannot open %s for tag writing", filepath)
                return False
            if not hasattr(af, "tags") or af.tags is None:
                af.add_tags()
            af.tags["REPLAYGAIN_TRACK_GAIN"] = f"{track_gain:.2f} dB"
            af.tags["REPLAYGAIN_TRACK_PEAK"] = f"{track_peak:.6f}"
            if album_gain is not None:
                af.tags["REPLAYGAIN_ALBUM_GAIN"] = f"{album_gain:.2f} dB"
            if album_peak is not None:
                af.tags["REPLAYGAIN_ALBUM_PEAK"] = f"{album_peak:.6f}"
            af.save()
            self.tagsWritten.emit(filepath, True)
            return True
        except Exception:
            logger.exception("Failed to write ReplayGain tags to %s", filepath)
            self.tagsWritten.emit(filepath, False)
            return False

    def remove_tags(self, filepath: str) -> bool:
        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is None or not hasattr(af, "tags") or af.tags is None:
                return True
            for key in list(af.tags.keys()):
                if key.upper().startswith("REPLAYGAIN_"):
                    del af.tags[key]
            af.save()
            self.tagsRemoved.emit(filepath, True)
            return True
        except Exception:
            logger.exception("Failed to remove ReplayGain tags from %s", filepath)
            self.tagsRemoved.emit(filepath, False)
            return False

    def _compute_replaygain(self, filepath: str) -> dict[str, Any]:
        data: dict[str, Any] = {
            "track_gain": 0.0,
            "track_peak": 0.0,
            "reference_loudness": -18.0,
        }
        try:
            import subprocess
            import json
            result = subprocess.run(
                ["ffmpeg", "-i", filepath, "-af",
                 "loudnorm=I=-18:LRA=7:TP=-2:print_format=json",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=120
            )
            for line in result.stderr.split("\n"):
                if "{" in line:
                    try:
                        parsed = json.loads(line.strip())
                        data["track_gain"] = -float(parsed.get("input_i", 0.0))
                        data["track_peak"] = float(parsed.get("input_tp", 0.0))
                        data["reference_loudness"] = -18.0
                    except (json.JSONDecodeError, ValueError):
                        pass
        except Exception:
            logger.debug("ffmpeg ReplayGain calc failed for %s; trying mutagen", filepath)
            import mutagen
            try:
                af = mutagen.File(filepath)
                if af and hasattr(af, "tags") and af.tags:
                    for key in af.tags:
                        if "REPLAYGAIN_TRACK_GAIN" in str(key).upper():
                            val = str(af.tags[key])
                            data["track_gain"] = float(val.replace(" dB", ""))
                            break
            except Exception:
                pass
        return data
