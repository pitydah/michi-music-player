"""Identifier controller — source-aware music identification logic."""
import logging
import time

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("astra.identifier")


class IdentifierController(QObject):
    """Centralizes: should we listen? what's the source? duplicate detection? library match?"""

    state_changed = Signal(str)          # idle/listening/paused/processing/error
    source_changed = Signal(str, str)    # source_type, source_label
    detected = Signal(dict)
    pause_reason_changed = Signal(str)

    LISTEN_SOURCES = {"radio", "navidrome", "jellyfin", "remote_stream"}
    LOCAL_SOURCES = {"local_file", "device_file"}

    def __init__(self, db, detection_service, parent=None):
        super().__init__(parent)
        self._db = db
        self._detection = detection_service
        self._enabled = False
        self._current_source_type = ""
        self._current_source_label = ""
        self._current_uri = ""
        self._paused_reason = ""
        self._last_detections: list[dict] = []
        self._dedupe_minutes = 10

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        self._recalculate()

    @property
    def current_source_type(self) -> str:
        return self._current_source_type

    @property
    def current_source_label(self) -> str:
        return self._current_source_label

    def set_current_track(self, source_type: str, source_label: str = "",
                          uri: str = "", title: str = "", artist: str = ""):
        self._current_source_type = source_type
        self._current_source_label = source_label
        self._current_uri = uri
        self.source_changed.emit(source_type, source_label)
        self._recalculate()

    def _recalculate(self):
        if self._enabled and self._should_listen(self._current_source_type):
            self._start_listening()
        else:
            self._pause(self._pause_reason_for(self._current_source_type))

    @classmethod
    def _should_listen(cls, source_type: str) -> bool:
        return source_type in cls.LISTEN_SOURCES

    def _pause_reason_for(self, source_type: str) -> str:
        if not self._enabled:
            return "Identificador desactivado"
        if source_type in self.LOCAL_SOURCES:
            return "Archivo local — Astra ya conoce sus metadatos"
        if source_type in ("unknown", ""):
            return "Fuente no reconocida"
        return ""

    def _start_listening(self):
        self._detection.start(source=self._current_source_type)
        self._set_state("listening")

    def _pause(self, reason: str = ""):
        self._detection.stop()
        self._paused_reason = reason
        self.pause_reason_changed.emit(reason)
        self._set_state("paused")

    def stop(self):
        self._enabled = False
        self._detection.stop()
        self._set_state("idle")

    def _set_state(self, state: str):
        self.state_changed.emit(state)

    # ── Detection result handling ──

    def on_detected(self, title: str, artist: str, album: str = "",
                    duration: float = 0.0, genre: str = "", year: int = 0):
        if self._is_recent_duplicate(title, artist):
            logger.debug("Skipping duplicate: %s — %s", title, artist)
            return

        match = self._find_library_match(title, artist, album)
        matched_filepath = match.get("filepath", "") if match else ""

        record = {
            "title": title,
            "artist": artist,
            "album": album,
            "duration": duration,
            "genre": genre,
            "year": year,
            "source_type": self._current_source_type,
            "source_label": self._current_source_label,
            "source_uri": self._current_uri,
            "matched_filepath": matched_filepath,
            "detected_at": time.time(),
        }

        self._last_detections.insert(0, record)
        if len(self._last_detections) > 100:
            self._last_detections.pop()

        self._db.add_detected_track(
            title=title,
            artist=artist,
            album=album,
            year=year,
            genre=genre,
            duration=duration,
            source=self._current_source_label,
            provider=self._current_source_type,
            confidence=0.85,
            filepath=matched_filepath,
            matched_library_id=0,
        )

        self.detected.emit(record)

    def _is_recent_duplicate(self, title: str, artist: str) -> bool:
        cutoff = time.time() - self._dedupe_minutes * 60
        for r in self._last_detections:
            if r["title"] == title and r["artist"] == artist and r.get("detected_at", 0) > cutoff:
                return True
        return False

    def _find_library_match(self, title: str, artist: str, album: str = "") -> dict | None:
        try:
            items = self._db.get_all(search=title)
            for item in items:
                if item.artist and artist and item.artist.lower() == artist.lower():
                    return {"filepath": item.filepath, "title": item.title,
                            "artist": item.artist, "album": item.album}
            # Fallback: title match with album
            if album:
                for item in items:
                    if item.album and item.album.lower() == album.lower():
                        return {"filepath": item.filepath, "title": item.title,
                                "artist": item.artist, "album": item.album}
        except Exception:
            pass
        return None
