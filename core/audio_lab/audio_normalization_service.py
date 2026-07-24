"""AudioNormalizationService — destructive normalization of audio files.

Requires explicit confirmation for destructive operations.
Differentiates: ReplayGain metadata (non-destructive),
player-side gain (in-memory), destructive normalization (rewrites file).
"""
from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.normalization")


@dataclass
class NormalizationResult:
    filepath: str = ""
    status: str = "pending"
    integrated_loudness: float = 0.0
    true_peak: float = 0.0
    loudness_range: float = 0.0
    target_loudness: float = -14.0
    gain_applied: float = 0.0
    error: str = ""
    destructive: bool = False


class AudioNormalizationService(QObject):
    normalizationCompleted = Signal(str, object)

    def __init__(self, db=None, wm: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm

    def measure_loudness(self, filepath: str) -> NormalizationResult:
        result = NormalizationResult(filepath=filepath)
        if not filepath or not os.path.isfile(filepath):
            result.status = "error"
            result.error = "FILE_NOT_FOUND"
            return result
        try:
            loudness_data = self._scan_loudness(filepath)
            result.integrated_loudness = loudness_data.get("integrated", 0.0)
            result.true_peak = loudness_data.get("true_peak", 0.0)
            result.loudness_range = loudness_data.get("loudness_range", 0.0)
            result.status = "completed"
        except Exception as e:
            logger.exception("Loudness measurement failed for %s", filepath)
            result.status = "error"
            result.error = str(e)
        return result

    def _scan_loudness(self, filepath: str) -> dict[str, float] | None:
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", filepath, "-af", "loudnorm=I=-14:LRA=1:TP=-1:print_format=json",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=120
            )
            import json
            stderr = result.stderr
            json_start = stderr.find("{")
            json_end = stderr.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                block = stderr[json_start:json_end]
                parsed = json.loads(block)
                return {
                    "integrated": float(parsed.get("input_i", 0.0)),
                    "true_peak": float(parsed.get("input_tp", 0.0)),
                    "loudness_range": float(parsed.get("input_lra", 0.0)),
                }
            return None
        except Exception:
            return None

    def normalize_file(self, filepath: str, target_loudness: float = -14.0,
                       destructive: bool = False,
                       confirmation_token: str | None = None) -> dict[str, Any]:
        """Normaliza un archivo con parámetros manuales.

        Args:
            filepath: Ruta del archivo a normalizar
            target_loudness: Nivel objetivo LUFS
            destructive: Si True, modifica el archivo original
            confirmation_token: Token para confirmar operaciones destructivas
        """
        result: dict[str, Any] = {"ok": False, "filepath": filepath}
        if not filepath or not os.path.isfile(filepath):
            result["error"] = "FILE_NOT_FOUND"
            return result

        if destructive:
            if not confirmation_token:
                result["requires_confirmation"] = True
                result["confirmation_token"] = f"norm_destructive_{id(filepath)}"
                result["warning"] = "La normalización destructiva sobrescribirá el archivo original. Esta operación no se puede deshacer."
                return result
            return self._normalize_destructive(filepath, target_loudness)
        else:
            result["ok"] = True
            result["status"] = "metadata_only"
            result["message"] = "Usar ReplayGain para normalización no destructiva"
            result["target_loudness"] = target_loudness
        return result

    def _normalize_destructive(self, filepath: str, target_loudness: float) -> dict[str, Any]:
        try:
            import subprocess
            ext = os.path.splitext(filepath)[1] or ".wav"
            tmp_path = filepath + ".normalized" + ext
            result = subprocess.run(
                ["ffmpeg", "-i", filepath, "-af", f"loudnorm=I={target_loudness}:TP=-1:LRA=7",
                 "-y", tmp_path],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                os.replace(tmp_path, filepath)
                if not os.path.isfile(filepath):
                    return {"ok": False, "error": "Output file not found after normalization", "error_code": "FILE_NOT_FOUND"}
                original_size = os.path.getsize(filepath)
                if original_size == 0:
                    return {"ok": False, "error": "Output file is empty after normalization", "error_code": "FILE_EMPTY"}
                return {"ok": True, "filepath": filepath, "target_loudness": target_loudness, "verified": True}
            return {"ok": False, "error": f"ffmpeg error: {result.stderr[:200]}"}
        except Exception as e:
            logger.exception("Destructive normalization failed for %s", filepath)
            return {"ok": False, "error": str(e)}
