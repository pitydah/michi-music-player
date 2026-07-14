"""AudioAnalysisService — technical and acoustic analysis of audio files.

Supports format detection, codec info, quality metrics, validation,
and integration with the existing audio_analysis module.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.analysis")


class AudioAnalysisService(QObject):
    analysisCompleted = Signal(str, object)
    analysisProgress = Signal(str, float, object)

    def __init__(self, db=None, wm: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm
        self._enabled = True
        self._backend_available = self._check_backend()

    def _check_backend(self) -> bool:
        try:
            from audio_analysis.dependency_check import check_dependencies
            deps = check_dependencies()
            return deps.get("available", False)
        except Exception:
            return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def available(self) -> bool:
        return self._backend_available

    def analyze_file(self, filepath: str) -> dict[str, Any]:
        result = self._base_result(filepath)
        if not self._enabled:
            result["status"] = "disabled"
            result["error"] = "Análisis desactivado."
            return result
        if not os.path.isfile(filepath):
            result["status"] = "error"
            result["error"] = "FILE_NOT_FOUND"
            return result
        if not self._backend_available:
            result["status"] = "unsupported"
            result["error"] = "No backend disponible (librosa/GStreamer no instalado)"
            result["explanation"] = "Instala python3-librosa o GStreamer con soporte de análisis"
            return result
        try:
            from audio_analysis.feature_extractor import extract_features, make_track_key
            feat = extract_features(filepath, backend="librosa", db=self._db)
            result["status"] = feat.status
            result["track_key"] = make_track_key(filepath)
            result["features"] = {
                "bpm": getattr(feat, "bpm", 0),
                "energy": getattr(feat, "energy", 0.0),
                "danceability": getattr(feat, "danceability", 0.0),
                "acousticness": getattr(feat, "acousticness", 0.0),
                "dynamic_range_db": getattr(feat, "dynamic_range_db", 0.0),
                "spectral_centroid": getattr(feat, "spectral_centroid", 0.0),
            }
            self._enrich_codec_result(filepath, result)
        except Exception as e:
            logger.exception("Analysis failed for %s", filepath)
            result["status"] = "error"
            result["error"] = str(e)
        return result

    def _enrich_codec_result(self, filepath: str, result: dict[str, Any]):
        import mutagen
        try:
            af = mutagen.File(filepath)
            if af is not None and hasattr(af, "info"):
                info = af.info
                result["codec"] = type(af).__name__
                result["format"] = os.path.splitext(filepath)[1].lower().lstrip(".")
                result["sample_rate"] = getattr(info, "sample_rate", 0)
                result["bit_depth"] = getattr(info, "bit_depth", getattr(info, "bits_per_sample", 0))
                result["channels"] = getattr(info, "channels", 0)
                result["bitrate"] = getattr(info, "bitrate", 0)
                result["duration"] = getattr(info, "length", 0.0)
                result["checksum"] = self._compute_checksum(filepath)
                result["decode_status"] = "ok"
                result["loudness"] = self._read_loudness(af)
                result["peak"] = self._read_peak(af)
                result["clipping"] = result.get("peak", 0) > 0.999
                result["silence"] = result.get("loudness", 0) < -70
        except Exception:
            result["decode_status"] = "error"

    def _compute_checksum(self, filepath: str) -> str:
        try:
            import hashlib
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for _ in range(8):
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def _read_loudness(self, af) -> float:
        try:
            if hasattr(af, "tags") and af.tags:
                for k in af.tags:
                    if "REPLAYGAIN_TRACK_GAIN" in str(k).upper():
                        val = str(af.tags[k]).replace(" dB", "")
                        return -float(val)
        except Exception:
            pass
        return 0.0

    def _read_peak(self, af) -> float:
        try:
            if hasattr(af, "tags") and af.tags:
                for k in af.tags:
                    if "REPLAYGAIN_TRACK_PEAK" in str(k).upper():
                        return float(str(af.tags[k]))
        except Exception:
            pass
        return 0.0

    def analyze_batch(self, filepaths: list[str]) -> list[dict[str, Any]]:
        return [self.analyze_file(fp) for fp in filepaths]

    def get_backend_info(self) -> dict[str, Any]:
        return {
            "available": self._backend_available,
            "enabled": self._enabled,
            "name": "librosa" if self._backend_available else "none",
        }

    def _base_result(self, filepath: str) -> dict[str, Any]:
        return {
            "filepath": filepath, "status": "unknown", "error": "", "explanation": "",
            "features": {},
            "codec": "", "format": "", "sample_rate": 0, "bit_depth": 0,
            "channels": 0, "bitrate": 0, "duration": 0.0,
            "loudness": 0.0, "peak": 0.0, "clipping": False, "silence": False,
            "checksum": "", "decode_status": "",
        }
