"""Metadata Review Service — orchestrates metadata detection, suggestion, and review."""

from __future__ import annotations

import logging
from typing import Any

from metadata.review.metadata_diff import (
    generate_diff_for_artist,
    generate_diff_for_album,
    generate_diff_for_track,
    generate_diff_from_gaps,
)
from metadata.review.metadata_review_repository import MetadataReviewRepository
from metadata.review.metadata_apply_service import MetadataApplyService
from metadata.review.metadata_undo import MetadataUndo
from metadata.review.schemas import (
    MetadataProposal,
    MetadataReview,
    generate_review_id,
    now_iso,
)

logger = logging.getLogger("michi.metadata.review_service")

_METADATA_GAP_FIELDS = ("title", "artist", "album", "albumartist", "genre", "year")


class MetadataReviewService:
    def __init__(self, db: Any, kb: Any = None,
                 metadata_editor: Any | None = None,
                 confirmation_service: Any | None = None):
        self._db = db
        self._kb = kb
        self._editor = metadata_editor
        self._repo = MetadataReviewRepository()
        self._apply = MetadataApplyService(
            db, self._repo,
            apply_to_db=self._apply_to_db,
            apply_to_files=self._apply_to_files,
            require_confirmation=self._require_confirm,
            metadata_editor=metadata_editor,
            confirmation_service=confirmation_service,
        )
        self._undo = MetadataUndo(db, self._repo)

    @staticmethod
    def _get_setting(key: str, default):
        from core.settings_manager import get_bool, get_float, get_int
        if isinstance(default, bool):
            val = get_bool(key)
            return val if val is not None else default
        if isinstance(default, float):
            return get_float(key) or default
        return get_int(key) or default

    @property
    def _enabled(self):
        return self._get_setting("ai_assistant/metadata_review_enabled", True)

    @property
    def _min_confidence(self):
        return self._get_setting("ai_assistant/metadata_min_confidence", 0.75)

    @property
    def _allow_low(self):
        return self._get_setting("ai_assistant/metadata_allow_low_confidence", False)

    @property
    def _max_batch(self):
        return self._get_setting("ai_assistant/metadata_max_batch", 50)

    @property
    def _require_confirm(self):
        return self._get_setting("ai_assistant/metadata_require_field_confirmation", True)

    @property
    def _apply_to_db(self):
        return self._get_setting("ai_assistant/metadata_apply_to_db", True)

    @property
    def _apply_to_files(self):
        return self._get_setting("ai_assistant/metadata_apply_to_files", False)

    def _disabled_response(self):
        return {
            "status": "disabled",
            "message": "La revision de metadata esta desactivada. "
                       "Puedes activarla en Configuracion > Asistente IA.",
        }

    def _filter_confidence(self, changes: list) -> list:
        if self._allow_low:
            return changes
        return [c for c in changes if c.confidence >= self._min_confidence]

    def find_inconsistencies(self, limit: int = 100) -> dict[str, Any]:
        if not self._enabled:
            return self._disabled_response()
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        results: list[dict] = []
        max_items = min(limit, 200)

        for item in items:
            if len(results) >= max_items:
                break
            missing = []
            for field in _METADATA_GAP_FIELDS:
                val = str(getattr(item, field, "") or "").strip()
                if not val:
                    missing.append(field)
            if missing:
                results.append({
                    "track_id": getattr(item, "id", 0),
                    "title": str(getattr(item, "title", "") or ""),
                    "artist": str(getattr(item, "artist", "") or ""),
                    "album": str(getattr(item, "album", "") or ""),
                    "missing_fields": missing,
                })

        return {
            "total_tracks_checked": min(len(items), max_items),
            "inconsistent_count": len(results),
            "results": results,
        }

    def suggest_for_track(self, track_id: int) -> dict[str, Any]:
        if not self._enabled:
            return self._disabled_response()
        item = self._db.get_media_item_by_id(track_id)
        if not item:
            return {"status": "error", "error": "Track no encontrado."}

        local = {
            "id": item.id, "title": item.title, "artist": item.artist,
            "album": item.album, "albumartist": item.albumartist,
            "year": str(item.year) if item.year else "",
            "genre": item.genre, "duration": item.duration,
            "isrc": item.isrc, "mb_track_id": item.mb_track_id,
            "mb_album_id": item.mb_album_id,
            "mb_albumartist_id": item.mb_albumartist_id,
        }

        proposals: list[MetadataProposal] = []

        if self._kb:
            if item.artist:
                artist_result = self._kb.lookup_artist(item.artist)
                if artist_result.get("data"):
                    artist_data = artist_result["data"].get("data", artist_result["data"])
                    p = generate_diff_for_artist(local, artist_data)
                    if p:
                        proposals.append(p)

            if item.album:
                album_result = self._kb.lookup_album(item.album, item.artist)
                if album_result.get("data"):
                    album_data = album_result["data"].get("data", album_result["data"])
                    p = generate_diff_for_album(local, album_data)
                    if p:
                        proposals.append(p)

            if item.title and item.artist:
                rec_result = self._kb.lookup_recording(item.title, item.artist)
                if rec_result.get("data"):
                    rec_data = rec_result["data"].get("data", rec_result["data"])
                    p = generate_diff_for_track(local, rec_data)
                    if p:
                        proposals.append(p)

        missing = []
        for field in _METADATA_GAP_FIELDS:
            if not str(getattr(item, field, "") or "").strip():
                missing.append(field)
        if missing:
            p = generate_diff_from_gaps(local, missing)
            if p:
                proposals.append(p)

        for p in proposals:
            p.changes = self._filter_confidence(p.changes)
            self._repo.save_proposal(p)

        return {
            "track_id": track_id,
            "title": item.title,
            "artist": item.artist,
            "proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "entity_type": p.entity_type,
                    "changes": [
                        {"field": c.field, "current_value": c.current_value,
                         "suggested_value": c.suggested_value, "source": c.source,
                         "confidence": c.confidence, "reason": c.reason}
                        for c in p.changes
                    ],
                }
                for p in proposals
            ],
            "total_proposals": len(proposals),
        }

    def suggest_for_album(self, album_title: str,
                          artist_name: str = "") -> dict[str, Any]:
        proposals: list[MetadataProposal] = []
        if self._kb:
            result = self._kb.lookup_album(album_title, artist_name)
            if result.get("data"):
                album_data = result["data"].get("data", result["data"])
                p = generate_diff_for_album(
                    {"album": album_title, "artist": artist_name}, album_data,
                )
                if p:
                    proposals.append(p)
                    self._repo.save_proposal(p)

        return {
            "album_title": album_title,
            "artist_name": artist_name,
            "proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "changes": [
                        {"field": c.field, "current_value": c.current_value,
                         "suggested_value": c.suggested_value, "source": c.source,
                         "confidence": c.confidence}
                        for c in p.changes
                    ],
                }
                for p in proposals
            ],
        }

    def create_review(self, track_ids: list[int]) -> dict[str, Any]:
        if not self._enabled:
            return self._disabled_response()
        review = MetadataReview(
            review_id=generate_review_id(),
            created_at=now_iso(),
            apply_target="local_db",
        )
        for tid in track_ids[:self._max_batch]:
            result = self.suggest_for_track(tid)
            for pdata in result.get("proposals", []):
                proposal = self._repo.load_proposal(pdata["proposal_id"])
                if proposal and proposal.changes:
                    review.proposals.append(proposal)

        if not review.proposals:
            return {"status": "empty", "review_id": "", "message": "No se encontraron cambios para proponer."}

        self._repo.save_review(review)
        self._repo.log_action(review.review_id, "create_review", "created",
                              f"Revision con {len(review.proposals)} propuestas")

        return {
            "status": "ready",
            "review_id": review.review_id,
            "proposal_count": len(review.proposals),
            "total_changes": sum(len(p.changes) for p in review.proposals),
            "proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "track_id": p.track_id,
                    "title": p.title,
                    "artist_name": p.artist_name,
                    "changes": [
                        {"field": c.field, "current_value": c.current_value,
                         "suggested_value": c.suggested_value, "source": c.source,
                         "confidence": c.confidence, "reason": c.reason}
                        for c in p.changes
                    ],
                }
                for p in review.proposals
            ],
        }

    def apply_review(self, review_id: str,
                     accepted_fields: dict[int, list[str]]) -> dict[str, Any]:
        return self._apply.apply(review_id, accepted_fields)

    def undo_review(self, review_id: str) -> dict[str, Any]:
        return self._undo.undo(review_id)

    def reject_review(self, review_id: str) -> dict[str, Any]:
        review = self._repo.load_review(review_id)
        if not review:
            return {"status": "error", "error": "Revision no encontrada."}
        review.status = "rejected"
        self._repo.log_action(review_id, "reject", "rejected", "Revision rechazada")
        return {"status": "rejected", "review_id": review_id}

    def load_review(self, review_id: str) -> dict[str, Any]:
        review = self._repo.load_review(review_id)
        if not review:
            return {"status": "error", "error": "Revision no encontrada."}
        return {
            "review_id": review.review_id,
            "status": review.status,
            "apply_target": review.apply_target,
            "proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "track_id": p.track_id,
                    "entity_type": p.entity_type,
                    "title": p.title,
                    "artist_name": p.artist_name,
                    "changes": [
                        {"field": c.field, "current_value": c.current_value,
                         "suggested_value": c.suggested_value, "source": c.source,
                         "confidence": c.confidence, "reason": c.reason}
                        for c in p.changes
                    ],
                }
                for p in review.proposals
            ],
        }
