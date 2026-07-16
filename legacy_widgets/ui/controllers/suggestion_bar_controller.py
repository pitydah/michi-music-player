"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""
from __future__ import annotations

"""SuggestionBarController — connects ContextSuggestionBar to ContextService.

This controller creates and manages the suggestion bar, connects it to the
context system for automatic section-based suggestions.
"""


from typing import Any

from PySide6.QtCore import QObject, QTimer

from integrations.ai_assistant.contextual_suggestion_engine import (
    ContextualSuggestionEngine,
)
from ui.assistant.context_suggestion_bar import ContextSuggestionBar


class SuggestionBarController(QObject):
    def __init__(self, context_service=None, parent=None):
        super().__init__(parent)
        self._context_svc = context_service
        self._engine = ContextualSuggestionEngine()
        self._bar = ContextSuggestionBar(parent=parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._refresh_suggestions)

        self._bar.suggestion_clicked.connect(self._on_suggestion_clicked)
        self._bar.ask_assistant_requested.connect(self._on_ask_assistant)

    def bar(self) -> ContextSuggestionBar:
        return self._bar

    def refresh(self) -> None:
        if self._debounce.isActive():
            self._debounce.stop()
        self._debounce.start()

    def set_section(self, section_key: str, title: str = "") -> None:
        self._bar.set_section(section_key, title)
        self.refresh()

    def clear(self) -> None:
        self._bar.clear_suggestions()
        self._engine.clear()

    def _refresh_suggestions(self) -> None:
        if self._context_svc is None:
            return
        snapshot = self._context_svc.get_current_section_snapshot()
        provider_suggestions = self._context_svc.get_current_section_suggestions()
        suggestions = self._engine.get_suggestions(snapshot, provider_suggestions)
        self._bar.set_suggestions(suggestions)

    def _on_suggestion_clicked(self, suggestion: dict[str, Any]) -> None:
        pass

    def _on_ask_assistant(self, section_key: str) -> None:
        pass
