"""Result — standard return type for all Michi services.

Every service method returns a Result object, never raises to caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Result:
    ok: bool = False
    code: str = "OK"
    message: str = ""
    data: Any = None
    error: str | None = None

    @classmethod
    def success(cls, data: Any = None, message: str = "") -> Result:
        return cls(ok=True, code="OK", message=message, data=data)

    @classmethod
    def fail(cls, code: str = "ERROR", message: str = "",
             error: str | None = None) -> Result:
        return cls(ok=False, code=code, message=message or code,
                   error=error or message or code)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "code": self.code,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }
