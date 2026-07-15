from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperationResult:
    ok: bool = True
    code: str = ""
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    partial: bool = False
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "code": self.code,
            "message": self.message,
            "data": dict(self.data),
            "warnings": list(self.warnings),
            "partial": self.partial,
            "retryable": self.retryable,
        }

    @classmethod
    def from_legacy_dict(cls, d: dict[str, Any]) -> OperationResult:
        return cls(
            ok=d.get("ok", True),
            code=d.get("code", ""),
            message=d.get("message", ""),
            data=d.get("data", d.get("details", {})),
            warnings=d.get("warnings", []),
            partial=d.get("partial", d.get("recoverable", False)),
            retryable=d.get("retryable", False),
        )
