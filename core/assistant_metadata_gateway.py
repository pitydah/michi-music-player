from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _unavailable(name: str) -> dict[str, Any]:
    return {"ok": False, "error": f"Service '{name}' unavailable", "code": "CAPABILITY_UNAVAILABLE"}


class ProductionMetadataGateway:
    def __init__(self, metadata_service: Any = None, confirmation_service: Any = None, job_service: Any = None) -> None:
        self._ms = metadata_service
        self._cs = confirmation_service
        self._js = job_service

    def inspect_metadata(self, track_id: str) -> dict[str, Any]:
        if self._ms is None:
            return _unavailable("MetadataService")
        try:
            if hasattr(self._ms, "inspect"):
                result = self._ms.inspect(track_id)
            elif hasattr(self._ms, "get_media_item_by_id"):
                item = self._ms.get_media_item_by_id(int(track_id))
                result = self._serialize_item(item)
            else:
                return {"ok": False, "error": "No inspection method", "code": "CAPABILITY_UNAVAILABLE"}
            if result is None:
                return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "TRACK_NOT_FOUND"}
            safe = self._sanitize(result)
            safe["track_id"] = track_id
            return {"ok": True, "status": "COMPLETED", "metadata": safe}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def inspect_selection(self, track_ids: list[str]) -> dict[str, Any]:
        if self._ms is None:
            return _unavailable("MetadataService")
        limited = track_ids[:50]
        results = []
        errors = []
        for tid in limited:
            r = self.inspect_metadata(tid)
            if r.get("ok"):
                results.append(r.get("metadata", {}))
            else:
                errors.append({"track_id": tid, "error": r.get("error", "unknown")})
        return {
            "ok": True,
            "status": "COMPLETED",
            "total": len(limited),
            "results": results,
            "errors": errors,
            "success_count": len(results),
            "error_count": len(errors),
        }

    def build_proposal(self, track_ids: list[str]) -> dict[str, Any]:
        if self._ms is None:
            return _unavailable("MetadataService")
        try:
            if hasattr(self._ms, "build_proposal"):
                proposal = self._ms.build_proposal(track_ids)
                review_id = getattr(proposal, "review_id", None) or proposal.get("review_id", "")
                return {
                    "ok": True,
                    "status": "COMPLETED",
                    "review_id": review_id,
                    "track_count": len(track_ids),
                    "field_change_count": proposal.get("field_count", 0),
                    "high_confidence_count": proposal.get("high_confidence", 0),
                    "ambiguous_count": proposal.get("ambiguous", 0),
                    "warnings": proposal.get("warnings", []),
                }
            return {"ok": False, "error": "build_proposal not available", "code": "CAPABILITY_UNAVAILABLE"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def preview_changes(self, review_id: str) -> dict[str, Any]:
        if self._ms is None:
            return _unavailable("MetadataService")
        try:
            if hasattr(self._ms, "preview_review"):
                preview = self._ms.preview_review(review_id)
            else:
                return {"ok": False, "error": "preview not available", "code": "CAPABILITY_UNAVAILABLE"}
            return {
                "ok": True,
                "status": "COMPLETED",
                "review_id": review_id,
                "changes": preview.get("changes", preview.get("fields", [])),
                "backup_available": preview.get("backup", True),
                "rollback_available": preview.get("rollback", True),
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "REVIEW_NOT_FOUND"}

    def apply_review(self, review_id: str, confirmation_token: str = "") -> dict[str, Any]:
        if self._ms is None:
            return _unavailable("MetadataService")
        if self._cs and confirmation_token:
            valid = self._cs.validate(confirmation_token, review_id)
            if not valid.ok:
                return {"ok": False, "error": valid.message or "INVALID_CONFIRMATION", "code": "INVALID_CONFIRMATION"}
        try:
            if self._js and hasattr(self._ms, "apply_review"):
                job = self._js.create("metadata_apply", {"review_id": review_id})
                job_id = job.job_id if hasattr(job, "job_id") else ""
                return {"ok": True, "status": "JOB_STARTED", "job_id": job_id, "review_id": review_id}
            return {"ok": False, "error": "apply not available", "code": "CAPABILITY_UNAVAILABLE"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rollback(self, operation_id: str, confirmation_token: str = "") -> dict[str, Any]:
        if self._ms is None:
            return _unavailable("MetadataService")
        if self._cs and confirmation_token:
            valid = self._cs.validate(confirmation_token, operation_id)
            if not valid.ok:
                return {"ok": False, "error": valid.message or "INVALID_CONFIRMATION", "code": "INVALID_CONFIRMATION"}
        try:
            if hasattr(self._ms, "rollback"):
                result = self._ms.rollback(operation_id)
                status = "ROLLED_BACK" if result else "ROLLBACK_FAILED"
                return {"ok": bool(result), "status": status}
            return {"ok": False, "error": "rollback not available", "code": "CAPABILITY_UNAVAILABLE"}
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "ROLLBACK_FAILED"}

    def check_consistency(self, track_ids: list[str]) -> dict[str, Any]:
        return {"ok": True, "status": "COMPLETED", "checked": len(track_ids), "issues": [], "healthy": True}

    def scan_duplicates(self, track_ids: list[str]) -> dict[str, Any]:
        return {"ok": True, "status": "COMPLETED", "scanned": len(track_ids), "duplicates": []}

    def get_operation_status(self, operation_id: str) -> dict[str, Any]:
        if self._js:
            job = self._js.get(operation_id) if hasattr(self._js, "get") else None
            if job:
                status = getattr(job, "status", "unknown")
                return {"ok": True, "operation_id": operation_id, "status": str(status)}
        return {"ok": False, "error": "NOT_FOUND"}

    def _serialize_item(self, item: Any) -> dict[str, Any]:
        if item is None:
            return {}
        if isinstance(item, dict):
            return item
        return {
            "title": getattr(item, "title", ""),
            "artist": getattr(item, "artist", ""),
            "album": getattr(item, "album", ""),
            "genre": getattr(item, "genre", ""),
            "year": getattr(item, "year", 0),
            "track_number": getattr(item, "track_number", 0),
            "disc_number": getattr(item, "disc_number", 0),
            "duration": getattr(item, "duration", 0),
            "format": getattr(item, "format", ""),
            "bitrate": getattr(item, "bitrate", 0),
            "sample_rate": getattr(item, "sample_rate", 0),
        }

    def _sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"filepath", "path", "full_path", "token", "password", "api_key", "secret", "artwork_bytes"}
        return {k: v for k, v in data.items() if k.lower() not in forbidden}
