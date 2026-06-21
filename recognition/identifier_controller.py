"""Identifier controller — source-aware music identification logic."""
import logging
import time

from PySide6.QtCore import QObject, Signal

from recognition.recognition_matcher import RecognitionMatcher
from recognition.provider_manager import ProviderManager

logger = logging.getLogger("astra.identifier")

LISTEN_SOURCES = {"radio", "navidrome", "jellyfin", "remote_stream"}
LOCAL_SOURCES = {"local_file", "device_file"}


class IdentifierController(QObject):
    state_changed = Signal(str)          # idle/listening/paused/processing/error
    source_changed = Signal(str, str)    # source_type, source_label
    detected = Signal(dict)
    pause_reason_changed = Signal(str)
    provider_changed = Signal(str, bool)

    def __init__(self, db, detection_service, parent=None):
        super().__init__(parent)
        self._db = db
        self._detection = detection_service
        self._provider_mgr = ProviderManager(self)
        self._enabled = False
        self._current_source_type = ""
        self._current_source_label = ""
        self._current_uri = ""
        self._current_title = ""
        self._current_artist = ""
        self._paused_reason = ""
        self._dedupe_minutes = 10

        # Enhanced matcher (fuzzy tiers + source-aware skip)
        self._matcher = RecognitionMatcher(db)

        # Persistent detection history repository
        try:
            from recognition.detection_history_repository import DetectionHistoryRepository
            self._history = DetectionHistoryRepository(db, self)
        except Exception:
            self._history = None

        # Wire detection signals
        self._detection.track_detected.connect(self._on_detection_result)
        self._detection.detection_failed.connect(self._on_detection_failed)
        self._detection.provider_changed.connect(self.provider_changed.emit)
        self._provider_mgr.provider_changed.connect(self.provider_changed.emit)

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

    @property
    def provider_manager(self):
        return self._provider_mgr

    def select_provider(self, name: str):
        self._provider_mgr.select_provider(name)
        self._detection.select_provider(name)

    def set_current_track(self, source_type: str = "", source_label: str = "",
                          uri: str = "", title: str = "", artist: str = ""):
        self._current_source_type = source_type
        self._current_source_label = source_label
        self._current_uri = uri
        self._current_title = title
        self._current_artist = artist
        self.source_changed.emit(source_type, source_label)
        self._recalculate()

    def _recalculate(self):
        if self._enabled and self._should_listen(self._current_source_type):
            self._start_listening()
        else:
            self._pause(self._pause_reason_for(self._current_source_type))

    @classmethod
    def _should_listen(cls, source_type: str) -> bool:
        return source_type in LISTEN_SOURCES

    def _pause_reason_for(self, source_type: str) -> str:
        if not self._enabled:
            return "Identificador desactivado"
        if source_type in LOCAL_SOURCES:
            return "Archivo local: Astra ya conoce sus metadatos"
        if source_type in ("unknown", ""):
            return "Sin fuente reconocida para identificar"
        return ""

    def _start_listening(self):
        self._detection.start(
            source=self._current_source_type,
            source_label=self._current_source_label,
            source_uri=self._current_uri)
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

    def identify_once(self):
        if self._enabled:
            self._detection.identify_once()

    def _set_state(self, state: str):
        self.state_changed.emit(state)

    # ── Detection response handlers ──

    def _on_detection_result(self, track):
        title = getattr(track, 'title', '')
        artist = getattr(track, 'artist', '')
        album = getattr(track, 'album', '')

        # Persistent dedup via DetectionHistoryRepository
        if self._history:
            existing = self._history.get_recent(title, artist)
            if existing:
                logger.debug("Skipping duplicate (DB): %s — %s", title, artist)
                return

        # Enhanced matching via RecognitionMatcher (fuzzy tiers, source-aware)
        match = self._matcher.match(
            title, artist, album, source_type=self._current_source_type)
        matched_filepath = match.get("filepath", "")
        match_status = match.get("status", "not_found")

        provider = getattr(track, 'provider', '')

        record = {
            "title": title, "artist": artist, "album": album,
            "source_type": self._current_source_type,
            "source_label": self._current_source_label,
            "source_uri": self._current_uri,
            "provider": provider,
            "matched_filepath": matched_filepath,
            "match_status": match_status,
            "detected_at": time.time(),
        }
        self.detected.emit(record)

    def _on_detection_failed(self, error: str):
        logger.debug("Detection failed: %s", error)
