"""Transcode service — future audio conversion for device sync. STUB."""

from __future__ import annotations

import logging

logger = logging.getLogger("michi.sync.transcode")

TRANSCODE_PROFILES = {
    "original": {"name": "Original", "description": "Sin conversión — archivos tal cual"},
    "flac_mobile": {"name": "FLAC móvil", "description": "FLAC nivel 5 para dispositivos"},
    "opus_balanced": {"name": "OPUS 320", "description": "Equilibrado calidad/espacio"},
    "opus_efficient": {"name": "OPUS 160", "description": "Máximo ahorro de espacio"},
}


class TranscodeService:
    def __init__(self):
        self._profiles = TRANSCODE_PROFILES

    @property
    def available_encoders(self) -> dict[str, bool]:
        import shutil
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
        # FUTURE: implement with ffmpeg subprocess
        pass
