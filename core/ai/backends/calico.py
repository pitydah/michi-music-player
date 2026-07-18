from __future__ import annotations

from typing import Any

from michi_ai.v2.core.models import ProviderRequest, ProviderResponse

from core.ai.backends.base import LocalModelBackend
from core.ai.response_composer import ResponseComposer


class CalicoBackend(LocalModelBackend):
    def __init__(self, response_composer: ResponseComposer | None = None) -> None:
        self._response_composer = response_composer or ResponseComposer()
        self._cancelled = False

    def is_available(self) -> bool:
        return True

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self._cancelled = False
        if self._cancelled:
            return ProviderResponse(
                provider="calico", model="rules-v1",
                text="", validation_errors=("Cancelled",),
            )
        metadata: dict = {}
        text = self._response_composer.compose(request, metadata)
        return ProviderResponse(
            provider="calico",
            model="rules-v1",
            text=text,
        )

    def cancel(self) -> None:
        self._cancelled = True

    def get_runtime_stats(self) -> dict[str, Any]:
        return {"type": "calico", "ram_mb": 0, "tokens_per_second": 0}
