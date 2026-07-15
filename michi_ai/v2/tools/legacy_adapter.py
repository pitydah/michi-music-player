from __future__ import annotations

import logging
from typing import Any

from michi_ai.v2.core.models import ErrorCode, OperationResult

logger = logging.getLogger(__name__)

_KNOWN_ACTIONS: frozenset[str] = frozenset({
    "play", "pause", "resume", "stop", "next", "previous", "seek",
    "set_volume", "set_repeat", "set_shuffle",
    "add_to_queue", "play_next", "replace_queue", "remove_from_queue",
    "clear_queue", "reorder_queue", "get_queue",
    "search", "get_track", "get_album", "get_artist",
    "list_recent", "list_unplayed", "list_favorites", "find_metadata_gaps",
    "list_playlists", "get_playlist", "create_playlist",
    "add_to_playlist", "remove_from_playlist", "reorder_playlist", "delete_playlist",
    "probe_audio", "analyze_audio", "recommend_conversion", "preview_conversion",
    "start_conversion", "cancel_conversion", "analyze_replaygain",
    "check_integrity", "compare_audio",
    "list_devices", "diagnose_ecosystem", "diagnose_server",
    "diagnose_home_audio", "diagnose_pairing", "plan_sync", "start_sync", "cancel_sync",
    "get_setting", "suggest_change", "preview_change", "apply_change", "list_settings",
    "get_diagnostics", "get_audio_diagnostics", "get_network_diagnostics",
    "request_navigation",
    "create_mix", "explain_mix", "save_mix_as_playlist", "cancel_mix",
    "list_jobs", "cancel_job", "get_job_status",
})

_ACTION_MAP: dict[str, str] = {
    "V1_PLAY": "play_track",
    "V1_PAUSE": "pause",
    "V1_RESUME": "resume",
    "V1_STOP": "stop",
    "V1_NEXT": "next",
    "V1_PREV": "previous",
    "V1_SEEK": "seek",
    "V1_VOLUME": "set_volume",
    "V1_SEARCH": "search_library",
    "V1_CREATE_PLAYLIST": "create_playlist",
    "V1_QUEUE_ADD": "add_to_queue",
    "V1_QUEUE_CLEAR": "clear_queue",
    "V1_SHUFFLE": "set_shuffle",
    "V1_REPEAT": "set_repeat",
}


def is_known_action(action: str) -> bool:
    return action in _KNOWN_ACTIONS or action in _ACTION_MAP


def map_legacy_action(action: str) -> str:
    mapped = _ACTION_MAP.get(action, action)
    if action in _ACTION_MAP:
        logger.warning("Deprecated action '%s' mapped to '%s'", action, mapped)
    return mapped


def reject_unknown_action(action: str) -> OperationResult[None]:
    return OperationResult.failure(
        ErrorCode.TOOL_NOT_FOUND,
        f"Unknown action: '{action}'. This action is not recognized by Michi AI V2.",
    )


def operation_result_to_legacy(result: OperationResult[Any]) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "success": result.ok,
        "code": result.code.value if result.code else "OK",
        "message": result.message,
        "data": result.data,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
        "requires_confirmation": result.requires_confirmation,
        "retryable": result.retryable,
        "cancelled": result.cancelled,
        "correlation_id": result.correlation_id,
    }


def legacy_to_operation_result(legacy: dict[str, Any]) -> OperationResult[Any]:
    ok = legacy.get("ok", legacy.get("success", False))
    return OperationResult(
        ok=bool(ok),
        code=ErrorCode.OK if ok else ErrorCode.TOOL_FAILED,
        message=legacy.get("message", legacy.get("error", "")),
        data=legacy.get("data"),
        warnings=tuple(legacy.get("warnings", [])),
        errors=tuple(legacy.get("errors", [])),
        requires_confirmation=legacy.get("requires_confirmation", False),
        retryable=legacy.get("retryable", False),
        cancelled=legacy.get("cancelled", False),
        correlation_id=legacy.get("correlation_id", ""),
    )


class OperationResultToLegacyToolResultAdapter:
    def adapt(self, result: OperationResult[Any]) -> dict[str, Any]:
        return operation_result_to_legacy(result)
