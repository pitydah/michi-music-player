"""MichiAIServiceV2 — wraps integrations/ai_assistant/AIAssistantService for DI."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.michi_ai_service")


class MichiAIServiceV2:
    def __init__(self, ai_assistant_service=None, tool_registry=None,
                 suggestion_engine=None):
        self._ai = ai_assistant_service
        self._tools = tool_registry
        self._suggestions = suggestion_engine

    @property
    def available(self) -> bool:
        return self._ai is not None

    def process_message(self, text: str, context: dict | None = None) -> dict:
        if self._ai:
            try:
                return self._ai.process_message(text, context or {})
            except Exception as e:
                return {"ok": False, "error": str(e), "response": f"Error: {e}"}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE", "response": "AI no disponible"}

    def get_suggestions(self, context: dict | None = None) -> list[dict]:
        if self._suggestions:
            try:
                return self._suggestions.get_suggestions(context or {})
            except Exception:
                pass
        return []

    def cancel(self):
        pass

    def health(self) -> dict:
        return {"available": self.available}

    def shutdown(self):
        pass
