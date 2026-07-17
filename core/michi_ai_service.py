"""MichiAIService — wraps the local AI engine for the QML bridge."""
from __future__ import annotations

from michi_ai.engine import process


class MichiAIService:
    def __init__(self):
        self._active = True

    def process_message(self, text: str, context: dict | None = None) -> dict:
        return process(text)

    def get_suggestions(self, context: dict | None = None) -> list[dict]:
        return [
            {"text": "Reproduce música de jazz", "icon": "play"},
            {"text": "Recomiéndame algo", "icon": "star"},
            {"text": "¿Quién es Pink Floyd?", "icon": "info"},
        ]

    def cancel(self):
        pass

    @property
    def ready(self) -> bool:
        return self._active
