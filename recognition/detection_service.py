"""Detection Service — orchestrates music identification lifecycle with real audio capture."""
import logging

from PySide6.QtCore import QObject, Signal

from recognition.models import DetectedTrack
from recognition.provider_manager import ProviderManager

logger = logging.getLogger("michi.detection")


class DetectionService(QObject):
    track_detected = Signal(object)     # DetectedTrack
    detection_failed = Signal(str)      # error message
    status_changed = Signal(str)        # idle/listening/capturing/processing/identified/error
    sample_captured = Signal(dict)       # sample metadata
    provider_changed = Signal(str, bool)  # provider_name, is_configured
    diagnostic_changed = Signal(dict)

    def __init__(self, db, provider_manager: ProviderManager = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._provider_mgr = provider_manager or ProviderManager(self)
        self._active = False
        self._status = "idle"
        self._last_error = ""
        self._detections_total = 0
        self._duplicates_avoided = 0
        self._capture = None
        self._capture_timer = None
        self._identifying = False
        self._worker_mgr = None

        self._provider_mgr.provider_changed.connect(
            lambda n, ok: self.provider_changed.emit(n, ok))

    @property
    def recognizer(self):
        return self._provider_mgr.recognizer

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def status(self) -> str:
        return self._status

    @property
    def provider_name(self) -> str:
        return self._provider_mgr.current_provider

    def set_recognizer(self, recognizer):
        self._provider_mgr._recognizer = recognizer

    def select_provider(self, name: str):
        self._provider_mgr.select_provider(name)

    def start(self, source: str = "", source_label: str = "",
              source_uri: str = ""):
        self._active = True
        self._current_source = source
        self._set_status("listening")
        # Continuous audio capture loop (every 15 seconds)
        if not self._capture:
            try:
                from recognition.audio_capture_service import AudioCaptureService
                self._capture = AudioCaptureService()
            except Exception:
                pass
        if not self._capture_timer:
            from PySide6.QtCore import QTimer
            self._capture_timer = QTimer(self)
            self._capture_timer.timeout.connect(self.identify_once)
        self._capture_timer.start(15000)
        logger.info("Detection started source=%s", source)

    def stop(self):
        self._active = False
        if self._capture_timer:
            self._capture_timer.stop()
        self._set_status("idle")

    def toggle(self, source: str = ""):
        if self._active:
            self.stop()
        else:
            self.start(source)

    def set_worker_manager(self, mgr):
        """Set WorkerManager for async identification. Offloads capture+identify."""
        self._worker_mgr = mgr
        if mgr:
            mgr.identify_done.connect(self._on_worker_identify)
            mgr.identify_error.connect(lambda e: self.detection_failed.emit(e))

    def _on_worker_identify(self, result):
        if result:
            self._handle_identified(result)
        else:
            self._set_status("no_match")
            self.detection_failed.emit("Sin coincidencia")
        self._identifying = False

    def identify_once(self):
        if not self._active:
            return
        if self._identifying:
            return
        self._identifying = True

        # Offload to WorkerManager if available
        if self._worker_mgr:
            self._set_status("processing")
            self._worker_mgr.identify(self._capture, self.recognizer)
            return

        # Synchronous fallback
        try:
            self._set_status("processing")

            # Use cached AudioCaptureService instance
            sample_bytes = None
            if self._capture and self._capture.is_available:
                self._set_status("capturing")
                sample_bytes = self._capture.capture_once()
                self.sample_captured.emit(
                    {"size": len(sample_bytes) if sample_bytes else 0,
                     "format": "S16LE/22050Hz/mono"})

            result = self.recognizer.identify(sample_bytes=sample_bytes,
                                              source=self._current_source if hasattr(self, '_current_source') else "")
            if result:
                self._handle_identified(result)
            else:
                self._set_status("no_match")
                self.detection_failed.emit("Sin coincidencia")
        finally:
            self._identifying = False

    def add_manual_detection(self, title: str, artist: str,
                             source: str = "manual", album: str = "",
                             provider: str = "manual"):
        self._set_status("identified")

        existing = self._db.find_detected_track_recent(title, artist)
        if existing:
            logger.debug("Skipping duplicate: %s - %s", artist, title)
            self._duplicates_avoided += 1
            return

        track = DetectedTrack(
            title=title, artist=artist, album=album,
            source=source, provider=provider, confidence=1.0)
        self._save_track(track)
        self._detections_total += 1

    def _handle_identified(self, result: dict):
        self._set_status("identified")
        track = DetectedTrack(
            title=result.get("title", ""),
            artist=result.get("artist", ""),
            album=result.get("album", ""),
            source=result.get("source", ""),
            provider=result.get("provider", self.provider_name),
            confidence=result.get("confidence"),
        )
        self._save_track(track)
        self._detections_total += 1

    def _save_track(self, track: DetectedTrack):
        try:
            self._db.add_detected_track(
                title=track.title, artist=track.artist,
                album=track.album, source=track.source,
                provider=track.provider, confidence=track.confidence,
                filepath=track.filepath or "",
                matched_library_id=track.matched_library_id or 0,
            )
        except Exception:
            self._db.add_detected_track(
                title=track.title or "",
                artist=track.artist or "",
                album=track.album or "",
                source=track.source or "",
                provider=track.provider or "",
                confidence=track.confidence or 0.0,
                filepath=track.filepath or "",
                matched_library_id=track.matched_library_id or 0,
            )
        self.track_detected.emit(track)

    def _set_status(self, status: str):
        self._status = status
        self.status_changed.emit(status)

    def diagnostics(self) -> dict:
        return {
            "active": self._active,
            "status": self._status,
            "provider": self.provider_name,
            "provider_ok": self._provider_mgr.recognizer.is_configured(),
            "last_error": self._last_error,
            "detections_total": self._detections_total,
            "duplicates_avoided": self._duplicates_avoided,
        }
