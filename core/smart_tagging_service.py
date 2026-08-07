"""SmartTaggingService — music recognition and metadata enrichment with confidence scoring."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
                 recognition_service=None, metadata_editor=None,
                 confirmation_service=None):
        self._worker_manager = worker_manager
        self._library_query = library_query_service
        self._recognition = recognition_service
        self._editor = metadata_editor
        self._cs = confirmation_service
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

    def suggest_for_track(self, track_id: int) -> dict:
        """Bridge-compatible suggestion interface. Resolves track_id to filepath and runs identify."""
        if not self._library_query:
            return {"ok": False, "error": "NO_LIBRARY_QUERY", "suggestions": []}
        try:
            results = self._library_query.get_track(track_id)
            if not results:
                return {"ok": False, "error": "TRACK_NOT_FOUND", "suggestions": []}
            filepath = results.get("filepath") or results.get("path", "")
            if not filepath:
                return {"ok": False, "error": "NO_FILEPATH", "suggestions": []}
            result = self.identify(filepath)
            if not result.get("ok", False):
                return {"ok": False,
                        "error": result.get("error", "RECOGNITION_FAILED"),
                        "suggestions": []}
            suggestions_raw = result.get("suggestions", [])
            suggestions = []
            for s in suggestions_raw:
                field = s.get("field", "")
                suggestions.append({
                    "field": field,
                    "current_value": s.get("current_value", ""),
                    "proposed_value": s.get("proposed_value", ""),
                    "confidence": s.get("confidence", 0.0),
                    "source": s.get("source", ""),
                    "warning": s.get("warning", ""),
                    "selected": False,
                })
            return {"ok": True, "suggestions": suggestions}
        except Exception as e:
            logger.error("suggest_for_track(%s) failed: %s", track_id, e)
            return {"ok": False, "error": str(e), "suggestions": []}

    def batch_identify(self, paths: list[str]) -> dict:
        results = []
        for p in paths:
            if self._cancelled:
                break
            results.append(self.identify(p))
        return {"ok": True, "results": results, "count": len(results),
                "cancelled": self._cancelled}

    def accept_suggestion(self, filepath: str, field: str, value: str) -> dict:
        """Apply one suggestion through the canonical editor pipeline.

        Authorization (P0): the edit goes through proposal → confirmation
        token (issued and approved via ConfirmationService) → apply with
        readback verification. Without the canonical editor the operation is
        disabled (LEGACY_OPERATION_DISABLED) — physical tags are never
        written directly here.
        """
        if self._editor is None:
            return {"ok": False, "error": "LEGACY_OPERATION_DISABLED",
                    "code": "LEGACY_OPERATION_DISABLED"}
        proposal = self._editor.build_proposal(
            [{"filepath": filepath}], {field: str(value)})
        if not proposal.get("ok"):
            return {"ok": False, "error": proposal.get("code", "PROPOSAL_FAILED")}
        conf = self._editor.confirm(
            proposal["proposal_id"], selected_fields=[field])
        if not conf.get("ok"):
            return {"ok": False, "error": conf.get("code", "CONFIRMATION_UNAVAILABLE")}
        token = conf["confirmation_token"]
        if not self._editor.approve(token).get("ok"):
            return {"ok": False, "error": "INVALID_CONFIRMATION_TOKEN"}
        result = self._editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmation_token": token,
        }])
        ok = bool(result.get("ok")) and result.get("applied", 0) == 1
        return {"ok": ok, "field": field, "value": value,
                "status": result.get("status", "APPLY_FAILED")}

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
