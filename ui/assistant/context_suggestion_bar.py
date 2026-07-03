"""ContextSuggestionBar — horizontal bar of contextual suggestion cards."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.assistant.suggestion_card import SuggestionCard


class ContextSuggestionBar(QFrame):
    suggestion_clicked = Signal(str)
    suggestion_dismissed = Signal(str)
    ask_assistant_requested = Signal(str)
    show_more_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[SuggestionCard] = []
        self._section_key = ""
        self._section_title = ""
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("contextSuggestionBar")
        self.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(8, 4, 8, 0)
        self._header_label = QLabel("Sugerencias")
        self._header_label.setObjectName("suggestionBarHeader")
        header_row.addWidget(self._header_label)
        header_row.addStretch()

        show_more_btn = QPushButton("Ver mas")
        show_more_btn.setObjectName("showMoreBtn")
        show_more_btn.setCursor(Qt.PointingHandCursor)
        show_more_btn.clicked.connect(self._on_show_more)
        header_row.addWidget(show_more_btn)
        layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setObjectName("suggestionScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._card_container = QWidget()
        self._card_container.setObjectName("suggestionCardContainer")
        self._card_layout = QHBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(8, 4, 8, 8)
        self._card_layout.setSpacing(8)
        self._card_layout.addStretch()

        scroll.setWidget(self._card_container)
        layout.addWidget(scroll)

    def set_suggestions(self, suggestions: list[dict[str, Any]]):
        self._clear_cards()
        for s in suggestions:
            sid = s.get("id", "")
            title = s.get("title", "")
            description = s.get("description", "")
            card = SuggestionCard(sid, title, description, self)
            card.clicked.connect(self._on_card_clicked)
            card.dismissed.connect(self._on_card_dismissed)
            self._cards.append(card)
            self._card_layout.insertWidget(len(self._cards) - 1, card)
        self.setVisible(len(self._cards) > 0)

    def set_section(self, section_key: str, title: str = ""):
        self._section_key = section_key
        self._section_title = title or section_key.replace("_", " ").title()
        label = f"Sugerencias - {self._section_title}" if self._section_title else "Sugerencias"
        self._header_label.setText(label)

    def clear_suggestions(self):
        self.clear()

    def clear(self):
        self._clear_cards()
        self.setVisible(False)

    def _clear_cards(self):
        for card in self._cards:
            self._card_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

    def _on_card_clicked(self, suggestion_id: str):
        self.suggestion_clicked.emit(suggestion_id)

    def _on_card_dismissed(self, suggestion_id: str):
        self.suggestion_dismissed.emit(suggestion_id)

    def _on_show_more(self):
        self.show_more_requested.emit()
