from __future__ import annotations

import logging
from typing import Any

from michi_ai.v2.core.models import ProviderRequest, ProviderResponse

from core.ai.backends.base import LocalModelBackend

logger = logging.getLogger("michi.backend.sphynx")


class SphynxBackend(LocalModelBackend):
    def __init__(self) -> None:
        self._ollama_available: bool | None = None
        self._cancelled = False

    def is_available(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                self._ollama_available = resp.status == 200
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self._cancelled = False
        if not self.is_available():
            return ProviderResponse(
                provider="sphynx", model="ollama",
                text="", validation_errors=("Ollama not available",),
                fallback_used=True,
            )

        if self._cancelled:
            return ProviderResponse(
                provider="sphynx", model="ollama",
                text="", validation_errors=("Cancelled",),
            )

        try:
            import json
            import urllib.request

            messages = list(request.messages)
            payload = {
                "model": "llama3.2",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature or 0.3,
                    "num_predict": request.max_tokens or 1024,
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))

            message = response_data.get("message", {})
            content = message.get("content", "")

            return ProviderResponse(
                provider="sphynx",
                model=response_data.get("model", "ollama"),
                text=content or "",
            )

        except Exception as exc:
            logger.warning("Sphynx/Ollama generation failed: %s", exc)
            return ProviderResponse(
                provider="sphynx", model="ollama",
                text="", validation_errors=(str(exc),),
                fallback_used=True,
            )

    def cancel(self) -> None:
        self._cancelled = True

    def get_runtime_stats(self) -> dict[str, Any]:
        return {"type": "sphynx", "ram_mb": 0, "tokens_per_second": 25}
