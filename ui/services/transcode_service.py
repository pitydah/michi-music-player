"""Transcode service — audio format conversion for device sync.

IMPORTANT: transcode() is not yet implemented. The available property
returns False until ffmpeg/opusenc/flac are integrated.
"""

from __future__ import annotations

import logging
import shutil

logger = logging.getLogger("michi.sync.transcode")

TRANSCODE_PROFILES = {
    "original": {"name": "Original", "description": "Sin conversión — archivos tal cual"},
    "flac_mobile": {"name": "FLAC móvil", "description": "FLAC nivel 5 — no disponible aún"},
    "opus_balanced": {"name": "OPUS 320", "description": "Equilibrado calidad/espacio — no disponible aún"},
    "opus_efficient": {"name": "OPUS 160", "description": "Máximo ahorro de espacio — no disponible aún"},
}


class TranscodeService:
    def __init__(self):
        self._profiles = TRANSCODE_PROFILES

    @property
    def available(self) -> bool:
        """Whether transcoding is actually functional (not yet)."""
        return False

    @property
    def available_encoders(self) -> dict[str, bool]:
        return {
            "flac": shutil.which("flac") is not None,
            "opus": shutil.which("opusenc") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None,
        }

    def get_profile(self, profile_id: str) -> dict:
        return self._profiles.get(profile_id, self._profiles["original"])

    def needs_transcode(self, source_path: str, profile_id: str) -> bool:
        return profile_id != "original"

    def transcode(self, source_path: str, dest_path: str,
                  profile_id: str = "original"):
        """Not yet implemented — returns silently until ffmpeg integration."""
        logger.warning(
            "Transcode requested but not implemented: %s → %s [%s]",
            source_path, dest_path, profile_id)
