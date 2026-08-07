"""RecognitionService — identifies music via the canonical advanced detection stack.

Wires the advanced recognition runtime composed in ``core/composition/``:
a shared :class:`recognition.provider_manager.ProviderManager`, the
:class:`recognition.audio_capture_service.AudioCaptureService` and the
:class:`recognition.detection_service.DetectionService` orchestrator.
``identify(filepath)`` is the SmartTagging consumption surface; the
detection/capture runtime is available for the continuous identifier.
Construction never opens devices or sockets — everything starts lazily.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("michi.recognition_service")


class RecognitionService:
    """Identification facade over the advanced detection stack.

    Exposes the composed runtime through public attributes (``provider_manager``,
    ``detection_service``, ``capture``) so composition wiring is verifiable, and
    the ``identify(filepath)`` dict surface required by SmartTaggingService.
    """

    def __init__(self, provider_manager=None, detection_service=None,
                 capture=None, db=None):
        self.provider_manager = provider_manager
        self.detection_service = detection_service
        self.capture = capture
        self._db = db
        self._available = provider_manager is not None

    @property
    def available(self) -> bool:
        return self._available

    def identify(self, filepath: str) -> dict:
        """Identify a music file and return structured recognition data."""
        if not self.provider_manager:
            return {}
        for provider_name in ("shazamio", "audd", "acoustid"):
            provider = self.provider_manager.get_provider(provider_name)
            if not provider:
                continue
            try:
                result = provider.identify(filepath=filepath)
                if result:
                    return self._normalize(result, provider_name)
            except Exception as e:
                logger.debug("%s failed for %s: %s", provider_name, filepath, e)
        return {}

    def _normalize(self, result: dict, source: str) -> dict:
        """Convert provider result to canonical format."""
        return {
            "title": result.get("title", ""),
            "artist": result.get("artist", ""),
            "album": result.get("album", ""),
            "confidence": result.get("confidence", 0.0),
            "source": source,
        }

    def start(self) -> None:
        # Bootstrap-safe no-op: the detection runtime starts on explicit
        # enable through DetectionService.start(); never at composition.
        pass

    def shutdown(self) -> None:
        if self.detection_service is not None:
            stop = getattr(self.detection_service, "stop", None)
            if stop is not None:
                try:
                    stop()
                except Exception as e:  # noqa: BLE001
                    logger.debug("detection stop failed: %s", e)
