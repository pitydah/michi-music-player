"""MichiAIPage — main dashboard for Michi AI contextual intelligence."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget


class MichiAIPage(QFrame):
    navigation_requested = Signal(str)
    plan_requested = Signal(str)
    tool_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("michiAIPage")
        self._insight_cards: list[QFrame] = []
        self._action_cards: list[QFrame] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setObjectName("michiAIContent")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(16)

        header = QLabel("Michi AI")
        header.setStyleSheet("font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.9);")
        self._layout.addWidget(header)

        subtitle = QLabel("Contexto, analisis y acciones inteligentes para tu biblioteca.")
        subtitle.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: 8px;")
        subtitle.setWordWrap(True)
        self._layout.addWidget(subtitle)

        self._status_label = QLabel("Cargando contexto...")
        self._status_label.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.5); padding: 8px;")
        self._layout.addWidget(self._status_label)

        self._insight_section = QVBoxLayout()
        self._insight_section.setSpacing(8)
        insight_header = QLabel("INSIGHTS")
        insight_header.setStyleSheet("font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.4); letter-spacing: 1px; padding-top: 8px;")
        self._insight_section.addWidget(insight_header)
        self._insight_container = QVBoxLayout()
        self._insight_container.setSpacing(6)
        self._insight_section.addLayout(self._insight_container)
        self._layout.addLayout(self._insight_section)

        self._action_section = QVBoxLayout()
        self._action_section.setSpacing(8)
        action_header = QLabel("ACCIONES SUGERIDAS")
        action_header.setStyleSheet("font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.4); letter-spacing: 1px; padding-top: 8px;")
        self._action_section.addWidget(action_header)
        self._action_container = QVBoxLayout()
        self._action_container.setSpacing(6)
        self._action_section.addLayout(self._action_container)
        self._layout.addLayout(self._action_section)

        self._layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._status_label.setText(f"Seccion: {snapshot.get('route', {}).get('current_section', '—')}")

    def set_insights(self, insights: list[dict[str, Any]]) -> None:
        self._clear_layout(self._insight_container)
        self._insight_cards = []
        for ins in insights:
            card = self._build_insight_card(ins)
            self._insight_container.addWidget(card)
            self._insight_cards.append(card)

    def set_actions(self, actions: list[dict[str, Any]]) -> None:
        self._clear_layout(self._action_container)
        self._action_cards = []
        for act in actions:
            card = self._build_action_card(act)
            self._action_container.addWidget(card)
            self._action_cards.append(card)

    def _build_insight_card(self, ins: dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("insightCard")
        card.setStyleSheet("""
            QFrame#insightCard { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 10px; }
            QLabel#insightTitle { color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 600; }
            QLabel#insightDesc { color: rgba(255,255,255,0.55); font-size: 11px; }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        title = QLabel(ins.get("title", ""))
        title.setObjectName("insightTitle")
        layout.addWidget(title)
        desc = QLabel(ins.get("description", ""))
        desc.setObjectName("insightDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        return card

    def _build_action_card(self, act: dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("actionCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet("""
            QFrame#actionCard { background: rgba(143,183,255,0.06); border: 1px solid rgba(143,183,255,0.15); border-radius: 10px; padding: 10px; }
            QFrame#actionCard:hover { background: rgba(143,183,255,0.12); }
            QLabel#actionTitle { color: rgba(143,183,255,0.85); font-size: 12px; font-weight: 600; }
            QLabel#actionDesc { color: rgba(255,255,255,0.55); font-size: 11px; }
        """)
        action = act.get("suggested_action", "")
        card.mousePressEvent = lambda e, a=action: self.tool_requested.emit(a, {})
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        title = QLabel(act.get("title", action))
        title.setObjectName("actionTitle")
        layout.addWidget(title)
        desc = QLabel(act.get("description", ""))
        desc.setObjectName("actionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        return card

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
