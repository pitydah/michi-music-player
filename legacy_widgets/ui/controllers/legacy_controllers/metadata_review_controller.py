"""Metadata review controller — bridges UI panel with MetadataReviewService."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.metadata.review_controller")


class MetadataReviewController(QObject):
    apply_result = Signal(dict)

    def __init__(self, db: Any, kb: Any = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._db = db
        self._kb = kb
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service
        from metadata.review.metadata_review_service import MetadataReviewService
        self._service = MetadataReviewService(self._db, self._kb)
        return self._service

    def load_review(self, review_id: str) -> dict:
        svc = self._get_service()
        return svc.load_review(review_id)

    def create_review(self, track_ids: list[int]) -> dict:
        svc = self._get_service()
        return svc.create_review(track_ids)

    def apply_review(self, review_id: str,
                     accepted_fields: dict[int, list[str]]) -> dict:
        svc = self._get_service()
        result = svc.apply_review(review_id, accepted_fields)
        self.apply_result.emit(result)
        return result

    def reject_review(self, review_id: str) -> dict:
        svc = self._get_service()
        return svc.reject_review(review_id)

    def undo_review(self, review_id: str) -> dict:
        svc = self._get_service()
        return svc.undo_review(review_id)
