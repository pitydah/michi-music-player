"""RecognitionService — identifies music files via configured providers."""

from __future__ import annotations

import logging

logger = logging.getLogger("michi.recognition_service")


class RecognitionService:
    """Thin wrapper over recognition providers for SmartTagging consumption.

    Exposes identify(filepath) -> dict as required by SmartTaggingService.
    """

    def __init__(self, provider_manager=None):
        self._provider_mgr = provider_manager
        self._available = provider_manager is not None

    @property
    def available(self) -> bool:
        return self._available

    def identify(self, filepath: str) -> dict:
        """Identify a music file and return structured recognition data."""
        if not self._provider_mgr:
            return {}
        for provider_name in ("shazam", "audd", "acoustid"):
            provider = self._provider_mgr.get_provider(provider_name)
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
        pass

    def shutdown(self) -> None:
        pass
