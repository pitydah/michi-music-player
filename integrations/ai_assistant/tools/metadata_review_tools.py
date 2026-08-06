"""Metadata review tools for Michi AI Assistant — detect, suggest, compare, apply."""

from __future__ import annotations

import threading
from typing import Any

from integrations.ai_assistant.schemas import ToolResult

# One shared MetadataReviewService per library database: tools never construct
# a review service ad hoc per call (single canonical instance per db).
_review_services: dict[int, Any] = {}
_review_lock = threading.Lock()


def _get_review_service(db: Any, kb: Any = None) -> Any:
    from metadata.review.metadata_review_service import MetadataReviewService
    key = id(db)
    with _review_lock:
        svc = _review_services.get(key)
        if svc is None:
            svc = MetadataReviewService(db, kb)
            _review_services[key] = svc
        return svc


def find_metadata_inconsistencies(db: Any, limit: int = 100) -> ToolResult:
    try:
        svc = _get_review_service(db)
        result = svc.find_inconsistencies(limit)
        return ToolResult(
            name="find_metadata_inconsistencies", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="find_metadata_inconsistencies", success=False, error=str(e),
        )


def suggest_metadata_for_track(db: Any, track_id: int = 0,
                                kb: Any = None) -> ToolResult:
    try:
        if not track_id:
            return ToolResult(
                name="suggest_metadata_for_track", success=False,
                error="Especifica un track_id.",
            )
        svc = _get_review_service(db, kb)
        result = svc.suggest_for_track(track_id)
        return ToolResult(
            name="suggest_metadata_for_track", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="suggest_metadata_for_track", success=False, error=str(e),
        )


def suggest_metadata_for_album(db: Any, album_title: str = "",
                                artist_name: str = "",
                                kb: Any = None) -> ToolResult:
    try:
        if not album_title.strip():
            return ToolResult(
                name="suggest_metadata_for_album", success=False,
                error="Especifica un titulo de album.",
            )
        svc = _get_review_service(db, kb)
        result = svc.suggest_for_album(album_title.strip(), artist_name.strip())
        return ToolResult(
            name="suggest_metadata_for_album", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="suggest_metadata_for_album", success=False, error=str(e),
        )


def suggest_metadata_for_artist(db: Any, artist_name: str = "",
                                 kb: Any = None) -> ToolResult:
    try:
        if not artist_name.strip():
            return ToolResult(
                name="suggest_metadata_for_artist", success=False,
                error="Especifica un nombre de artista.",
            )
        proposal = {
            "entity_type": "artist",
            "artist_name": artist_name.strip(),
            "proposals": [],
        }
        if kb:
            result = kb.lookup_artist(artist_name.strip())
            if result.get("data"):
                data = result["data"].get("data", result["data"])
                from metadata.review.metadata_diff import generate_diff_for_artist
                p = generate_diff_for_artist(
                    {"artist": artist_name.strip()}, data,
                )
                if p:
                    proposal["proposals"].append({
                        "proposal_id": p.proposal_id,
                        "changes": [
                            {"field": c.field, "current_value": c.current_value,
                             "suggested_value": c.suggested_value, "source": c.source,
                             "confidence": c.confidence}
                            for c in p.changes
                        ],
                    })
        return ToolResult(
            name="suggest_metadata_for_artist", success=True, data=proposal,
        )
    except Exception as e:
        return ToolResult(
            name="suggest_metadata_for_artist", success=False, error=str(e),
        )


def create_metadata_review(db: Any, track_ids: list[int],
                           kb: Any = None) -> ToolResult:
    try:
        if not track_ids:
            return ToolResult(
                name="create_metadata_review", success=False,
                error="Especifica al menos un track_id.",
            )
        svc = _get_review_service(db, kb)
        result = svc.create_review(track_ids)
        return ToolResult(
            name="create_metadata_review", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="create_metadata_review", success=False, error=str(e),
        )


def apply_metadata_review(db: Any, review_id: str = "",
                           accepted_fields: dict | None = None) -> ToolResult:
    try:
        if not review_id:
            return ToolResult(
                name="apply_metadata_review", success=False,
                error="Especifica un review_id.",
            )
        svc = _get_review_service(db)
        result = svc.apply_review(review_id, accepted_fields or {})
        return ToolResult(
            name="apply_metadata_review", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="apply_metadata_review", success=False, error=str(e),
        )


def reject_metadata_review(db: Any, review_id: str = "") -> ToolResult:
    try:
        if not review_id:
            return ToolResult(
                name="reject_metadata_review", success=False,
                error="Especifica un review_id.",
            )
        svc = _get_review_service(db)
        result = svc.reject_review(review_id)
        return ToolResult(
            name="reject_metadata_review", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="reject_metadata_review", success=False, error=str(e),
        )


def undo_metadata_review(db: Any, review_id: str = "") -> ToolResult:
    try:
        if not review_id:
            return ToolResult(
                name="undo_metadata_review", success=False,
                error="Especifica un review_id.",
            )
        svc = _get_review_service(db)
        result = svc.undo_review(review_id)
        return ToolResult(
            name="undo_metadata_review", success=True, data=result,
        )
    except Exception as e:
        return ToolResult(
            name="undo_metadata_review", success=False, error=str(e),
        )
