"""Metadata apply service — applies accepted metadata changes to LibraryDB or files."""

from __future__ import annotations

import logging
from typing import Any

from metadata.review.metadata_review_repository import MetadataReviewRepository

logger = logging.getLogger("michi.metadata.apply_service")


class MetadataApplyService:
    def __init__(self, db, repository: MetadataReviewRepository,
                 apply_to_db: bool = True,
                 apply_to_files: bool = False,
                 require_confirmation: bool = True,
                 metadata_editor: Any | None = None,
                 confirmation_service: Any | None = None):
        if not hasattr(db, 'update_media_item_field'):
            raise TypeError("db object must implement update_media_item_field()")
        if not hasattr(db, 'get_media_item_by_id'):
            raise TypeError("db object must implement get_media_item_by_id()")
        self._db = db
        self._repo = repository
        self._apply_to_db = apply_to_db
        self._apply_to_files = apply_to_files
        self._require_confirm = require_confirmation
        self._editor = metadata_editor
        self._cs = confirmation_service

    def apply(self, review_id: str, accepted_fields: dict[int, list[str]]) -> dict[str, Any]:
        review = self._repo.load_review(review_id)
        if not review:
            return {"status": "error", "error": "Revision no encontrada."}
        if review.status == "applied":
            return {"status": "error", "error": "Esta revision ya fue aplicada."}

        target = review.apply_target
        if target == "local_db" and not self._apply_to_db:
            return {"status": "error", "error": "Aplicacion a DB desactivada en configuracion."}
        if target == "file_tags" and not self._apply_to_files:
            return {"status": "error", "error": "Escritura a archivos desactivada en configuracion."}

        # P0: all metadata mutations route through the canonical editor with
        # a ConfirmationToken. The legacy direct DB/tag writes are disabled.
        if self._editor is not None:
            return self._apply_via_editor(review_id, review, accepted_fields)
        return {"status": "error", "error": "LEGACY_OPERATION_DISABLED",
                "message": "Metadata apply requires the canonical "
                           "MetadataEditorService (proposal → token → apply)"}

    def _apply_via_editor(self, review_id: str, review,
                          accepted_fields: dict[int, list[str]]) -> dict[str, Any]:
        """Route accepted review changes through the canonical editor pipeline.

        Every track with accepted fields becomes a proposal → token (issued
        and approved via ConfirmationService) → apply_batch with readback
        verification. Unsupported fields are skipped honestly.
        """
        applied = 0
        skipped = 0
        for proposal in review.proposals:
            accepted = set(accepted_fields.get(proposal.track_id, []))
            changes = {
                c.field: c.suggested_value
                for c in proposal.changes
                if c.field in accepted and c.suggested_value
            }
            if not changes:
                skipped += 1
                continue
            item = self._db.get_media_item_by_id(proposal.track_id)
            filepath = getattr(item, "filepath", "") if item else ""
            ref = {"track_id": proposal.track_id}
            if filepath:
                ref["filepath"] = filepath
            build = self._editor.build_proposal([ref], changes)
            if not build.get("ok"):
                skipped += 1
                continue
            conf = self._editor.confirm(
                build["proposal_id"], selected_fields=list(changes))
            if not conf.get("ok"):
                skipped += 1
                continue
            token = conf["confirmation_token"]
            if not self._editor.approve(token).get("ok"):
                skipped += 1
                continue
            result = self._editor.apply_batch([{
                "proposal_id": build["proposal_id"],
                "confirmation_token": token,
            }])
            applied += result.get("applied", 0)
            skipped += result.get("failed", 0) + result.get("conflicts", 0)
            for c in proposal.changes:
                if c.field in accepted:
                    c.accepted = True
            proposal.status = ("applied" if applied
                               else "rejected")
            self._repo.save_proposal(proposal)

        review.status = "applied" if skipped == 0 else "partial"
        self._repo.log_action(
            review_id, "apply", review.status,
            f"Aplicados {applied} cambios, omitidos {skipped}",
        )
        return {"status": review.status, "applied": applied,
                "skipped": skipped, "target": review.apply_target}

    def _get_current(self, track_id: int, field: str) -> str | None:
        try:
            item = self._db.get_media_item_by_id(track_id)
            if item:
                return str(getattr(item, field, "") or "")
        except Exception as e:
            logger.warning("Failed to get current value for track %d field %s: %s",
                           track_id, field, e)
        return None
