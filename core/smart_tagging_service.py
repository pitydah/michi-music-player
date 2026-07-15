"""SmartTaggingService — real music recognition and metadata enrichment.
Uses ShazamIO, AcoustID, and AudD providers for identification."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.smart_tagging")


class SmartTaggingService:
    def __init__(self, worker_manager=None, library_query_service=None,
                 recognition_service=None):
        self._worker_manager = worker_manager
        self._library_query = library_query_service
        self._recognition = recognition_service
        self._cancelled = False

    @property
    def available(self) -> bool:
        return self._recognition is not None

    def identify(self, filepath: str) -> dict:
        if not self._recognition:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            result = self._recognition.identify(filepath)
            if result:
                return {"ok": True, "result": result}
            return {"ok": True, "result": None, "message": "No match found"}
        except Exception as e:
            logger.error("Identification error: %s", e)
            return {"ok": False, "error": str(e)}

    def batch_identify(self, paths: list[str]) -> dict:
        results = []
        for p in paths:
            if self._cancelled:
                break
            results.append(self.identify(p))
        return {"ok": True, "results": results, "count": len(results)}

    def cancel(self):
        self._cancelled = True

    def health(self) -> dict:
        return {"available": self.available}

    def shutdown(self):
        self._cancelled = True
