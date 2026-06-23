"""Metadata apply service — applies accepted metadata changes to LibraryDB or files."""

from __future__ import annotations

import logging
from typing import Any

from metadata.review.metadata_review_repository import MetadataReviewRepository

logger = logging.getLogger("michi.metadata.apply_service")


class MetadataApplyService:
    def __init__(self, db: Any, repository: MetadataReviewRepository,
                 apply_to_db: bool = True,
                 apply_to_files: bool = False,
                 require_confirmation: bool = True):
        self._db = db
        self._repo = repository
        self._apply_to_db = apply_to_db
        self._apply_to_files = apply_to_files
        self._require_confirm = require_confirmation

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
        if target == "file_tags" and self._apply_to_files:
            return self._apply_to_files_target(review_id, review, accepted_fields)
        if target != "local_db":
            return {"status": "error", "error": f"apply_target '{target}' no soportado."}

        return self._apply_to_db_target(review_id, review, accepted_fields)

    def _apply_to_db_target(self, review_id: str, review, accepted_fields: dict[int, list[str]]) -> dict[str, Any]:
        if self._require_confirm and not accepted_fields:
            return {"status": "error", "error": "Debes confirmar al menos un campo para aplicar los cambios."}
        applied = 0
        skipped = 0
        for proposal in review.proposals:
            accepted = accepted_fields.get(proposal.track_id, [])
            for change in proposal.changes:
                if change.field in accepted and change.suggested_value:
                    old_val = self._get_current(proposal.track_id, change.field)
                    ok = self._db.update_media_item_field(
                        proposal.track_id, change.field, change.suggested_value,
                    )
                    if ok:
                        self._repo.save_undo(
                            review_id, proposal.track_id, change.field, old_val,
                        )
                        change.accepted = True
                        applied += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1

            proposal.status = "applied" if applied > 0 else "rejected"
            self._repo.save_proposal(proposal)

        review.status = "applied"
        self._repo.log_action(
            review_id, "apply", "applied",
            f"Aplicados {applied} cambios, omitidos {skipped}",
        )
        return {"status": "applied", "applied": applied, "skipped": skipped, "target": "local_db"}

    def _apply_to_files_target(self, review_id: str, review, accepted_fields: dict[int, list[str]]) -> dict[str, Any]:
        applied = 0
        skipped = 0
        for proposal in review.proposals:
            accepted = accepted_fields.get(proposal.track_id, [])
            changes_to_write = [c for c in proposal.changes if c.field in accepted and c.suggested_value]
            if not changes_to_write:
                skipped += len(proposal.changes)
                continue
            item = self._db.get_media_item_by_id(proposal.track_id)
            if not item or not getattr(item, "filepath", ""):
                skipped += len(proposal.changes)
                continue
            ok = _write_tags_for_track(item.filepath, changes_to_write)
            if ok:
                for c in changes_to_write:
                    old_val = self._get_current(proposal.track_id, c.field)
                    self._db.update_media_item_field(proposal.track_id, c.field, c.suggested_value)
                    self._repo.save_undo(review_id, proposal.track_id, c.field, old_val)
                    c.accepted = True
                    applied += 1
            else:
                skipped += len(changes_to_write)

            proposal.status = "applied" if applied > 0 else "rejected"
            self._repo.save_proposal(proposal)

        review.status = "applied"
        self._repo.log_action(
            review_id, "apply", "applied_to_files",
            f"Escritos {applied} cambios en archivos, omitidos {skipped}",
        )
        return {"status": "applied", "applied": applied, "skipped": skipped, "target": "file_tags"}

    def _get_current(self, track_id: int, field: str) -> str:
        try:
            item = self._db.get_media_item_by_id(track_id)
            if item:
                return str(getattr(item, field, "") or "")
        except Exception:
            pass
        return ""


def _write_tags_for_track(filepath: str, changes: list) -> bool:
    if not changes:
        return False
    try:
        from metadata.tag_reader import read_tags
        from metadata.tag_writer import write_tags
        tags = read_tags(filepath)
        if tags is None:
            return False
        for change in changes:
            if change.accepted and change.suggested_value:
                tags.set_field(change.field, change.suggested_value)
        return write_tags(tags)
    except Exception as e:
        logger.warning("Tag write failed for %s: %s", filepath, e)
        return False
