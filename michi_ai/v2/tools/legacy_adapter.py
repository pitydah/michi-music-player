from __future__ import annotations

from typing import Any

from michi_ai.v2.core.models import ErrorCode, OperationResult


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
