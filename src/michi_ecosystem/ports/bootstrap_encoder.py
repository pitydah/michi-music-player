"""Bootstrap encoder boundary (R7): V1 today, V2 when contracts freeze."""

from __future__ import annotations

from typing import Protocol

from michi_ecosystem.domain.bootstrap import FactoryBootstrapPayload


class BootstrapEncodingError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class FactoryBootstrapEncoderPort(Protocol):
    def encode(self, payload: FactoryBootstrapPayload) -> bytes: ...
