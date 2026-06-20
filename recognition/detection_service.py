"""Detection Service — manages music identification lifecycle.

First version: UI + DB integration only. No real audio capture yet.

Roadmap for real recognition:
  1. Capture audio via GStreamer appsink (pull 12-second PCM samples at 22050Hz)
  2. Option A: AcoustID fingerprint via chromaprint (fpcalc binary or python-acoustid)
  3. Option B: AudD API (requires API key — https://audd.io)
  4. Option C: ACRCloud API (requires API key — https://acrcloud.com)
  5. Option D: ShazamIO (unofficial, no API key needed)
  6. Store fingerprint matches in detected_tracks table for local cache
"""

import logging

from PySide6.QtCore import QObject, Signal

from recognition.models import DetectedTrack
from recognition.null_recognizer import NullRecognizer

logger = logging.getLogger("astra.detection")


class DetectionService(QObject):
    track_detected = Signal(object)   # DetectedTrack
    detection_failed = Signal(str)    # error message
    status_changed = Signal(str)      # idle/listening/processing/identified/error

    def __init__(self, db, recognizer=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._recognizer = recognizer or NullRecognizer()
        self._active = False
        self._status = "idle"

    def start(self, source: str = "", filepath: str | None = None):
        self._active = True
        self._set_status("listening")
        logger.info("Detection started source=%s filepath=%s", source, filepath)

    def stop(self):
        self._active = False
        self._set_status("idle")

    def toggle(self, source: str = "", filepath: str | None = None):
        if self._active:
            self.stop()
        else:
            self.start(source, filepath)

    def is_active(self) -> bool:
        return self._active

    def _set_status(self, status: str):
        self._status = status
        self.status_changed.emit(status)

    def add_manual_detection(self, title: str, artist: str,
                             source: str = "manual", album: str = "",
                             provider: str = "manual"):
        """Add a detection manually — for testing and future external APIs."""
        self._set_status("identified")

        # Deduplication: skip if same title+artist detected in last 5 min
        existing = self._db.find_detected_track_recent(title, artist)
        if existing:
            logger.debug("Skipping duplicate: %s - %s", artist, title)
            return

        track = DetectedTrack(
            title=title,
            artist=artist,
            album=album,
            source=source,
            provider=provider,
            confidence=1.0,
        )

        self._db.add_detected_track(
            title=track.title,
            artist=track.artist,
            album=track.album,
            source=track.source,
            provider=track.provider,
            confidence=track.confidence,
            isrc=track.isrc,
            artwork_url=track.artwork_url,
            external_url=track.external_url,
            filepath=track.filepath,
            matched_library_id=track.matched_library_id,
            raw_json=track.raw_json,
        )

        self.track_detected.emit(track)
