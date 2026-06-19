"""Detection models — DetectedTrack dataclass."""

import time
from dataclasses import dataclass


@dataclass
class DetectedTrack:
    title: str
    artist: str
    album: str = ""
    source: str = ""
    provider: str = ""
    confidence: float | None = None
    isrc: str | None = None
    artwork_url: str | None = None
    external_url: str | None = None
    filepath: str | None = None
    matched_library_id: int | None = None
    raw_json: str | None = None
    detected_at: float = 0.0

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = time.time()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "source": self.source,
            "provider": self.provider,
            "confidence": self.confidence,
            "isrc": self.isrc,
            "artwork_url": self.artwork_url,
            "external_url": self.external_url,
            "filepath": self.filepath,
            "matched_library_id": self.matched_library_id,
            "raw_json": self.raw_json,
            "detected_at": self.detected_at,
        }
