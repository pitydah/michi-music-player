"""Canonical OperationResult — typed result for service operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OperationResult:
    ok: bool
    code: str = ""
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    partial: bool = False
    retryable: bool = False
    recoverable: bool = True
    requires_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "code": self.code,
            "message": self.message,
            "data": dict(self.data),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "partial": self.partial,
            "retryable": self.retryable,
            "recoverable": self.recoverable,
            "requires_confirmation": self.requires_confirmation,
        }

    @classmethod
    def success(cls, data: dict[str, Any] | None = None,
                message: str = "") -> OperationResult:
        return cls(ok=True, code="OK", message=message,
                   data=data or {})

    @classmethod
    def fail(cls, code: str, message: str = "",
             recoverable: bool = True) -> OperationResult:
        return cls(ok=False, code=code, message=message,
                   recoverable=recoverable)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperationResult:
        return cls(
            ok=d.get("ok", False),
            code=d.get("code", d.get("error_code", "")),
            message=d.get("message", d.get("error", "")),
            data=d.get("data", {}),
            warnings=d.get("warnings", []),
            errors=d.get("errors", []),
            partial=d.get("partial", False),
            retryable=d.get("retryable", False),
            recoverable=d.get("recoverable", True),
            requires_confirmation=d.get("requires_confirmation", False),
        )
