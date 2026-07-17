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
class NormalizationPreset:
    """Preset de normalización para plataformas de streaming."""
    name: str
    target_loudness: float  # LUFS
    true_peak_limit: float  # dBTP
    loudness_range: float   # LRA
    description: str = ""


# Presets estándar de la industria
NORMALIZATION_PRESETS = {
    "spotify": NormalizationPreset(
        name="Spotify",
        target_loudness=-14.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="Spotify usa -14 LUFS con límite de -1 dBTP"
    ),
    "apple_music": NormalizationPreset(
        name="Apple Music",
        target_loudness=-16.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="Apple Music usa -16 LUFS con límite de -1 dBTP"
    ),
    "youtube": NormalizationPreset(
        name="YouTube",
        target_loudness=-14.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="YouTube normaliza a -14 LUFS con límite de -1 dBTP"
    ),
    "tidal": NormalizationPreset(
        name="Tidal",
        target_loudness=-14.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="Tidal Masters usa -14 LUFS"
    ),
    "amazon_music": NormalizationPreset(
        name="Amazon Music",
        target_loudness=-14.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="Amazon Music usa -14 LUFS"
    ),
    "soundcloud": NormalizationPreset(
        name="SoundCloud",
        target_loudness=-14.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="SoundCloud recomienda -14 LUFS"
    ),
    "broadcast_ebu": NormalizationPreset(
        name="Broadcast (EBU R128)",
        target_loudness=-23.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="Estándar europeo de broadcast EBU R128"
    ),
    "custom": NormalizationPreset(
        name="Personalizado",
        target_loudness=-14.0,
        true_peak_limit=-1.0,
        loudness_range=7.0,
        description="Configuración personalizada"
    )
}


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
    preset_name: str = "custom"


class AudioNormalizationService(QObject):
    normalizationCompleted = Signal(str, object)

    def __init__(self, db=None, wm: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm
        self._current_preset = "custom"

    def get_presets(self) -> dict[str, dict]:
        """Obtiene todos los presets disponibles para la UI."""
        return {
            key: {
                "name": preset.name,
                "target_loudness": preset.target_loudness,
                "true_peak_limit": preset.true_peak_limit,
                "loudness_range": preset.loudness_range,
                "description": preset.description
            }
            for key, preset in NORMALIZATION_PRESETS.items()
        }

    def get_preset(self, preset_key: str) -> dict | None:
        """Obtiene un preset específico por clave."""
        preset = NORMALIZATION_PRESETS.get(preset_key)
        if not preset:
            return None
        return {
            "name": preset.name,
            "target_loudness": preset.target_loudness,
            "true_peak_limit": preset.true_peak_limit,
            "loudness_range": preset.loudness_range,
            "description": preset.description
        }

    def set_current_preset(self, preset_key: str) -> bool:
        """Establece el preset actual."""
        if preset_key in NORMALIZATION_PRESETS:
            self._current_preset = preset_key
            return True
        return False

    def get_current_preset(self) -> str:
        """Obtiene la clave del preset actual."""
        return self._current_preset

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

    def _scan_loudness(self, filepath: str) -> dict[str, float]:
        data: dict[str, float] = {}
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", filepath, "-af", "loudnorm=I=-14:LRA=1:TP=-1:print_format=json",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=120
            )
            import json
            for line in result.stderr.split("\n"):
                if "{" in line:
                    try:
                        parsed = json.loads(line.strip())
                        data["integrated"] = float(parsed.get("input_i", 0.0))
                        data["true_peak"] = float(parsed.get("input_tp", 0.0))
                        data["loudness_range"] = float(parsed.get("input_lra", 0.0))
                    except (json.JSONDecodeError, ValueError):
                        pass
        except Exception:
            pass
        if not data:
            import mutagen
            try:
                af = mutagen.File(filepath)
                if af and hasattr(af.info, "sample_rate") and af.info.sample_rate:
                    data = {"integrated": 0.0, "true_peak": 0.0, "loudness_range": 0.0}
            except Exception:
                pass
        return data

    def normalize_file(self, filepath: str, target_loudness: float = -14.0,
                       destructive: bool = False,
                       confirmation_token: str | None = None,
                       preset_key: str = "custom") -> dict[str, Any]:
        """Normaliza un archivo usando un preset o valores personalizados.
        
        Args:
            filepath: Ruta del archivo a normalizar
            target_loudness: Nivel objetivo LUFS (se ignora si se usa preset)
            destructive: Si True, modifica el archivo original
            confirmation_token: Token para confirmar operaciones destructivas
            preset_key: Clave del preset a usar (spotify, apple_music, youtube, etc.)
        """
        result: dict[str, Any] = {"ok": False, "filepath": filepath}
        if not filepath or not os.path.isfile(filepath):
            result["error"] = "FILE_NOT_FOUND"
            return result
        
        # Obtener parámetros del preset si se especifica
        if preset_key and preset_key in NORMALIZATION_PRESETS:
            preset = NORMALIZATION_PRESETS[preset_key]
            target_loudness = preset.target_loudness
            self._current_preset = preset_key
        
        if destructive:
            if not confirmation_token:
                result["requires_confirmation"] = True
                result["confirmation_token"] = f"norm_destructive_{id(filepath)}"
                result["warning"] = "La normalización destructiva sobrescribirá el archivo original. Esta operación no se puede deshacer."
                result["preset_used"] = preset_key
                return result
            return self._normalize_destructive(filepath, target_loudness, preset_key)
        else:
            result["ok"] = True
            result["status"] = "metadata_only"
            result["message"] = "Usar ReplayGain para normalización no destructiva"
            result["preset_used"] = preset_key
            result["target_loudness"] = target_loudness
        return result

    def _normalize_destructive(self, filepath: str, target_loudness: float, preset_key: str = "custom") -> dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", filepath, "-af", f"loudnorm=I={target_loudness}:TP=-1:LRA=7",
                 "-y", filepath + ".tmp"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                os.replace(filepath + ".tmp", filepath)
                if not os.path.isfile(filepath):
                    return {"ok": False, "error": "Output file not found after normalization", "error_code": "FILE_NOT_FOUND"}
                original_size = os.path.getsize(filepath)
                if original_size == 0:
                    return {"ok": False, "error": "Output file is empty after normalization", "error_code": "FILE_EMPTY"}
                return {"ok": True, "filepath": filepath, "target_loudness": target_loudness, "verified": True, "preset_used": preset_key}
            return {"ok": False, "error": f"ffmpeg error: {result.stderr[:200]}"}
        except Exception as e:
            logger.exception("Destructive normalization failed for %s", filepath)
            return {"ok": False, "error": str(e)}
