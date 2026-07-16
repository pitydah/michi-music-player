"""QualityAnalysisService — audio quality classification for tracks/albums/artists."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("michi.quality")


class QualityAnalysisService:
    def __init__(self, db=None):
        self._db = db

    def analyze_track(self, filepath: str) -> dict:
        from audio.quality_classifier import classify_audio_quality
        try:
            q = classify_audio_quality(filepath) if os.path.isfile(filepath) else {"category": "unknown"}
            return {"ok": True, "filepath": filepath, "quality": q}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
