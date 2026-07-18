"""SmartTaggingService — music recognition and metadata enrichment with confidence scoring."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("michi.smart_tagging")


@dataclass
class TagSuggestion:
    field: str
    current_value: str
    proposed_value: str
    confidence: float  # 0.0 - 1.0
    source: str  # "shazam", "acoustid", "audd", "musicbrainz"
    original_value: str = ""


@dataclass
class TrackSuggestion:
    filepath: str
    suggestions: list[TagSuggestion] = field(default_factory=list)
    overall_confidence: float = 0.0


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
                suggestions = self._build_suggestions(filepath, result)
                return {"ok": True, "suggestions": suggestions,
                        "overall_confidence": self._compute_confidence(result)}
            return {"ok": True, "suggestions": [], "message": "No match"}
        except Exception as e:
            logger.error("Identification error for %s: %s", filepath, e)
            return {"ok": False, "error": str(e)}

    def batch_identify(self, paths: list[str]) -> dict:
        results = []
        for p in paths:
            if self._cancelled:
                break
            results.append(self.identify(p))
        return {"ok": True, "results": results, "count": len(results),
                "cancelled": self._cancelled}

    def accept_suggestion(self, filepath: str, field: str, value: str) -> dict:
        from metadata.tag_reader import read_tags
        from metadata.tag_writer import write_tags
        tags = read_tags(filepath)
        if not tags:
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        tags.set_field(field, value)
        ok = write_tags(tags)
        if ok:
            return {"ok": True, "field": field, "value": value}
        return {"ok": False, "error": "WRITE_FAILED"}

    def apply_all(self, filepath: str, suggestions: list[dict]) -> dict:
        results = []
        for s in suggestions:
            r = self.accept_suggestion(filepath, s.get("field", ""), s.get("proposed_value", ""))
            results.append(r)
        return {"ok": True, "results": results, "applied": sum(1 for r in results if r.get("ok"))}

    def cancel(self):
        self._cancelled = True

    def start(self):
        self._cancelled = False

    def health(self) -> dict:
        return {"available": self.available}

    def shutdown(self):
        self._cancelled = True

    def _build_suggestions(self, filepath: str, result: dict) -> list[dict]:
        from metadata.tag_reader import read_tags
        tags = read_tags(filepath)
        suggestions = []
        mappings = [
            ("title", "title"), ("artist", "artist"), ("album", "album"),
            ("genre", "genre"), ("year", "year"), ("tracknumber", "track_number"),
        ]
        for tag_field, result_key in mappings:
            current = getattr(tags, tag_field, "") if tags else ""
            proposed = result.get(result_key, "")
            if proposed and proposed != current:
                suggestions.append({
                    "field": tag_field,
                    "current_value": current,
                    "proposed_value": proposed,
                    "confidence": result.get("confidence", 0.5),
                    "source": result.get("source", "unknown"),
                })
        return suggestions

    @staticmethod
    def _compute_confidence(result: dict) -> float:
        return result.get("confidence", result.get("score", 0.5))
