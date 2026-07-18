from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from michi_ai.v2.core.models import ProviderRequest, ProviderResponse


class LocalModelBackend(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        ...

    def load(self) -> None:
        raise NotImplementedError

    def unload(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        ...

    def cancel(self) -> None:
        raise NotImplementedError

    def get_runtime_stats(self) -> dict[str, Any]:
        return {"type": "abstract", "ram_mb": 0, "tokens_per_second": 0}
