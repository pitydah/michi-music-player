from __future__ import annotations

from michi_ai.v2.core.models import ErrorCode, OperationResult
from michi_ai.v2.tools.legacy_adapter import (
    legacy_to_operation_result,
    operation_result_to_legacy,
    OperationResultToLegacyToolResultAdapter,
)


class TestOperationResultToLegacy:
    def test_success_conversion(self):
        result = OperationResult.success(data={"value": 42}, message="Done", warnings=("warn1",))
        legacy = operation_result_to_legacy(result)
        assert legacy["ok"] is True
        assert legacy["success"] is True
        assert legacy["data"] == {"value": 42}
        assert legacy["message"] == "Done"
        assert "warn1" in legacy["warnings"]

    def test_failure_conversion(self):
        result = OperationResult.failure(ErrorCode.TOOL_NOT_FOUND, "Not found", errors=("err1",))
        legacy = operation_result_to_legacy(result)
        assert legacy["ok"] is False
        assert legacy["success"] is False
        assert "err1" in legacy["errors"]

    def test_confirmation_conversion(self):
        result = OperationResult.confirmation("Are you sure?")
        legacy = operation_result_to_legacy(result)
        assert legacy["ok"] is False
        assert legacy["requires_confirmation"] is True

    def test_cancellation_conversion(self):
        result = OperationResult(
            ok=False, code=ErrorCode.TOOL_CANCELLED, message="Cancelled",
            cancelled=True,
        )
        legacy = operation_result_to_legacy(result)
        assert legacy["cancelled"] is True

    def test_adapter_class(self):
        adapter = OperationResultToLegacyToolResultAdapter()
        result = OperationResult.success(data=[1, 2, 3])
        legacy = adapter.adapt(result)
        assert legacy["data"] == [1, 2, 3]


class TestLegacyToOperationResult:
    def test_legacy_success(self):
        legacy = {"ok": True, "data": {"result": "ok"}, "message": "Success"}
        result = legacy_to_operation_result(legacy)
        assert result.ok is True
        assert result.code == ErrorCode.OK
        assert result.data == {"result": "ok"}

    def test_legacy_success_field(self):
        legacy = {"success": True, "data": 42}
        result = legacy_to_operation_result(legacy)
        assert result.ok is True

    def test_legacy_failure(self):
        legacy = {"ok": False, "error": "Something broke", "retryable": True}
        result = legacy_to_operation_result(legacy)
        assert result.ok is False
        assert result.message == "Something broke"
        assert result.retryable is True

    def test_legacy_requires_confirmation(self):
        legacy = {"ok": False, "requires_confirmation": True}
        result = legacy_to_operation_result(legacy)
        assert result.requires_confirmation is True

    def test_legacy_cancelled(self):
        legacy = {"ok": False, "cancelled": True}
        result = legacy_to_operation_result(legacy)
        assert result.cancelled is True

    def test_roundtrip(self):
        original = OperationResult.success(data={"key": "val"}, message="test", warnings=("w",))
        legacy = operation_result_to_legacy(original)
        back = legacy_to_operation_result(legacy)
        assert back.ok == original.ok
        assert back.message == original.message
        assert back.data == original.data
        assert back.warnings == original.warnings
