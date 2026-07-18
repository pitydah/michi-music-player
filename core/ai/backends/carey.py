from __future__ import annotations

import logging
from typing import Any

from michi_ai.v2.core.models import ProviderRequest, ProviderResponse

from core.ai.backends.base import LocalModelBackend

logger = logging.getLogger("michi.backend.carey")

_MODEL_ID = "carey"
_MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"


class CareyBackend(LocalModelBackend):
    def __init__(self, model_manager: Any | None = None) -> None:
        self._model_manager = model_manager
        self._llm: Any = None
        self._cancelled = False

    def is_available(self) -> bool:
        if self._llm is not None:
            return True
        if self._model_manager is None:
            return False
        return self._model_manager.get_status(_MODEL_ID) in ("installed", "loaded", "unloaded")

    def load(self) -> None:
        if self._model_manager is None:
            raise RuntimeError("ModelManager required to load Carey")
        self._llm = self._model_manager.load(_MODEL_ID)

    def unload(self) -> None:
        self._llm = None
        if self._model_manager is not None:
            self._model_manager.unload(_MODEL_ID)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self._cancelled = False
        if self._llm is None:
            if not self.is_available():
                return ProviderResponse(
                    provider="carey", model=_MODEL_ID,
                    text="", validation_errors=("Model not available",),
                    fallback_used=True,
                )
            self.load()

        if self._cancelled:
            return ProviderResponse(
                provider="carey", model=_MODEL_ID,
                text="", validation_errors=("Cancelled",),
            )

        try:
            messages = list(request.messages)
            response = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.3,
                stop=None,
            )
            text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ProviderResponse(
                provider="carey",
                model=_MODEL_ID,
                text=text or "",
            )
        except Exception as exc:
            logger.warning("Carey generation failed: %s", exc)
            return ProviderResponse(
                provider="carey", model=_MODEL_ID,
                text="", validation_errors=(str(exc),),
                fallback_used=True,
            )

    def cancel(self) -> None:
        self._cancelled = True

    def get_runtime_stats(self) -> dict[str, Any]:
        return {"type": "carey", "ram_mb": 1500, "tokens_per_second": 8}
