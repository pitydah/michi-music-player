"""MichiAIService — wraps the local AI engine for the QML bridge."""
from __future__ import annotations

from typing import Any, Callable

from michi_ai.engine import process
from michi_ai.recommender import set_library_provider


def _make_library_provider(db) -> Callable[[], list[dict[str, str]]]:
    def provider() -> list[dict[str, str]]:
        try:
            rows = db.execute("SELECT artist, album, title, genre FROM media WHERE kind='audio' LIMIT 1000").fetchall()
            result = []
            for row in rows:
                result.append({
                    "artist": row[0] or "",
                    "album": row[1] or "",
                    "title": row[2] or "",
                    "genre": row[3] or "",
                })
            return result
        except Exception:
            return []
    return provider


class MichiAIService:
    def __init__(self, db=None, library_provider: Callable[[], list[dict[str, str]]] | None = None):
        self._active = True
        if library_provider:
            set_library_provider(library_provider)
        elif db:
            set_library_provider(_make_library_provider(db))

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
