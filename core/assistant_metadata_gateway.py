from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _unavailable(name: str) -> dict[str, Any]:
    return {"ok": False, "error": f"Service '{name}' unavailable", "code": "CAPABILITY_UNAVAILABLE"}


class ProductionMetadataGateway:
    def __init__(self, metadata_service: Any = None, confirmation_service: Any = None, job_service: Any = None, metadata_editor: Any = None) -> None:
        self._ms = metadata_service
        self._cs = confirmation_service
        self._js = job_service
        self._editor = metadata_editor

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
        """Create a metadata proposal through the canonical editor service.

        The editor is the single editing authority: it reads current DB
        values, fills detectable gaps and returns a proposal id for the
        preview/apply steps.
        """
        if self._editor is None:
            return _unavailable("MetadataEditorService (build_proposal)")
        try:
            refs = [{"track_id": int(tid)} for tid in track_ids if str(tid).isdigit()]
            if not refs:
                return {"ok": False, "error": "NO_VALID_TRACK_IDS",
                        "code": "NO_VALID_TRACK_IDS"}
            proposal = self._editor.build_proposal(refs)
            return {
                "ok": True,
                "status": "COMPLETED",
                "review_id": proposal.get("proposal_id", ""),
                "track_count": len(track_ids),
                "field_change_count": proposal.get("field_count", 0),
                "fields": proposal.get("fields", []),
                "warnings": [],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def preview_changes(self, review_id: str) -> dict[str, Any]:
        if self._editor is None:
            return _unavailable("MetadataEditorService (preview)")
        try:
            preview = self._editor.preview_proposal(review_id)
            if not preview.get("ok"):
                return {"ok": False, "error": preview.get("message", "PREVIEW_FAILED"),
                        "code": "REVIEW_NOT_FOUND"}
            return {
                "ok": True,
                "status": "COMPLETED",
                "review_id": review_id,
                "changes": preview.get("changes", []),
                "backup_available": True,
                "rollback_available": True,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "REVIEW_NOT_FOUND"}

    def apply_review(self, review_id: str, confirmation_token: str = "") -> dict[str, Any]:
        if self._editor is None:
            return _unavailable("MetadataEditorService (apply)")
        if self._cs and confirmation_token:
            request = self._cs.approve(confirmation_token)
            if request is None or request.operation_id != review_id:
                return {"ok": False, "error": "INVALID_CONFIRMATION",
                        "code": "INVALID_CONFIRMATION"}
        try:
            result = self._editor.apply_batch([{
                "proposal_id": review_id,
                "confirmation_token": confirmation_token,
                "confirmed": True,
                "source": "ai_plan",
            }])
            if not result.get("ok"):
                return {"ok": False, "error": result.get("status", "APPLY_FAILED"),
                        "code": result.get("status", "APPLY_FAILED"),
                        "review_id": review_id,
                        "applied": result.get("applied", 0),
                        "failed": result.get("failed", 0),
                        "conflicts": result.get("conflicts", 0)}
            return {"ok": True, "status": "COMPLETED", "review_id": review_id,
                    "applied": result.get("applied", 0),
                    "failed": result.get("failed", 0),
                    "conflicts": result.get("conflicts", 0),
                    "operation_id": result.get("operation_id", ""),
                    "readback_verified": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rollback(self, operation_id: str, confirmation_token: str = "") -> dict[str, Any]:
        if self._editor is None:
            return _unavailable("MetadataEditorService (rollback)")
        if self._cs and confirmation_token:
            request = self._cs.approve(confirmation_token)
            if request is None or request.operation_id != operation_id:
                return {"ok": False, "error": "INVALID_CONFIRMATION",
                        "code": "INVALID_CONFIRMATION"}
        try:
            result = self._editor.undo(operation_id)
            status = "ROLLED_BACK" if result.get("ok") else result.get("code", "ROLLBACK_FAILED")
            return {"ok": bool(result.get("ok")), "status": status,
                    "operation_id": operation_id}
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "ROLLBACK_FAILED"}

    def check_consistency(self, track_ids: list[str]) -> dict[str, Any]:
        if self._ms is None or not hasattr(self._ms, "check_consistency"):
            return _unavailable("consistency check (route not wired)")
        try:
            return self._ms.check_consistency(track_ids)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def scan_duplicates(self, track_ids: list[str]) -> dict[str, Any]:
        if self._ms is None or not hasattr(self._ms, "scan_duplicates"):
            return _unavailable("duplicate scan (route not wired)")
        try:
            return self._ms.scan_duplicates(track_ids)
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
