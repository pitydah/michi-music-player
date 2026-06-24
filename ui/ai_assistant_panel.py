"""AI Assistant chat panel — premium, privacy-focused, with pending action cards."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLineEdit, QPushButton, QLabel, QFrame, QSizePolicy,
)

_PRIVACY_NOTICE = (
    "IA local · Datos protegidos · Sin rutas sensibles"
)

_PLACEHOLDER = "Pregunta algo sobre tu biblioteca musical..."

_EXAMPLE_CHIPS = [
    "Recomiéndame algo para escuchar",
    "Busca álbumes sin carátula",
    "Crea una playlist tranquila",
    "Revisa metadatos pendientes",
]


class AiAssistantPanel(QWidget):
    send_requested = Signal(str)
    action_confirmed = Signal(str)
    action_cancelled = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("aiAssistantPanel")
        self._messages: list[dict[str, str]] = []
        self._ollama_available = False
        self._build_ui()
        self._apply_qss()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setObjectName("assistantHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 16, 20, 12)
        hl.setSpacing(4)

        hrow = QHBoxLayout()
        h_title = QLabel("Michi Assistant")
        h_title.setObjectName("assistantHeaderTitle")
        hrow.addWidget(h_title)
        hrow.addStretch()
        self._status_badge = QLabel("Ollama no disponible")
        self._status_badge.setObjectName("assistantStatusBadge")
        hrow.addWidget(self._status_badge)
        hl.addLayout(hrow)

        h_sub = QLabel("IA local para explorar, organizar y mejorar tu biblioteca.")
        h_sub.setWordWrap(True)
        h_sub.setObjectName("assistantHeaderSubtitle")
        hl.addWidget(h_sub)
        layout.addWidget(header)

        # ── Chat area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setObjectName("assistantChatScroll")

        self._chat_container = QWidget()
        self._chat_container.setObjectName("assistantChatContainer")
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(16, 12, 16, 12)
        self._chat_layout.setSpacing(10)

        self._empty_state = self._build_empty_state()
        self._chat_layout.addWidget(self._empty_state)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._chat_container)
        layout.addWidget(self._scroll, 1)

        # ── Privacy badge ──
        self._privacy_badge = QLabel(_PRIVACY_NOTICE)
        self._privacy_badge.setObjectName("assistantPrivacyBadge")
        self._privacy_badge.setWordWrap(True)
        self._privacy_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._privacy_badge)

        # ── Input ──
        input_row = QHBoxLayout()
        input_row.setContentsMargins(12, 8, 12, 12)
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("assistantInput")
        self._input.setPlaceholderText(_PLACEHOLDER)
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input, 1)

        self._send_btn = QPushButton("Enviar")
        self._send_btn.setObjectName("assistantSendBtn")
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self._send_btn)

        layout.addLayout(input_row)

    def _build_empty_state(self) -> QWidget:
        w = QWidget()
        w.setObjectName("assistantEmptyState")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 40, 0, 40)
        vl.setAlignment(Qt.AlignCenter)
        vl.setSpacing(12)

        et = QLabel("Pregunta por tu música")
        et.setObjectName("assistantEmptyTitle")
        et.setAlignment(Qt.AlignCenter)
        vl.addWidget(et)

        ed = QLabel("Podés pedir recomendaciones, revisar metadatos o explorar tu biblioteca.")
        ed.setObjectName("assistantEmptyDesc")
        ed.setAlignment(Qt.AlignCenter)
        ed.setWordWrap(True)
        vl.addWidget(ed)

        chip_row = QHBoxLayout()
        chip_row.setAlignment(Qt.AlignCenter)
        chip_row.setSpacing(8)
        for chip_text in _EXAMPLE_CHIPS:
            chip = QPushButton(chip_text)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setObjectName("assistantChip")
            chip.clicked.connect(lambda c=None, t=chip_text: self._fill_example(t))
            chip_row.addWidget(chip)
        vl.addLayout(chip_row)

        return w

    def _fill_example(self, text: str):
        self._input.setText(text)
        self._input.setFocus()

    def _hide_empty_state(self):
        if self._empty_state and not self._empty_state.isHidden():
            self._empty_state.hide()

    @staticmethod
    def _build_panel_qss() -> str:
        return (
            "QWidget#aiAssistantPanel {"
            "  background: #090B11;"
            "}"
            "QFrame#assistantHeader {"
            "  background: rgba(255,255,255,0.025);"
            "  border-bottom: 1px solid rgba(255,255,255,0.04);"
            "}"
            "QLabel#assistantHeaderTitle {"
            "  color: rgba(255,255,255,0.92); font-size: 18px; font-weight: 700; background: transparent;"
            "}"
            "QLabel#assistantHeaderSubtitle {"
            "  color: rgba(255,255,255,0.56); font-size: 12px; background: transparent;"
            "}"
            "QLabel#assistantStatusBadge {"
            "  color: rgba(255,255,255,0.54); font-size: 11px; font-weight: 500;"
            "  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.04);"
            "  border-radius: 8px; padding: 3px 10px;"
            "}"
            "QLabel#assistantEmptyTitle {"
            "  color: rgba(255,255,255,0.56); font-size: 17px; font-weight: 600; background: transparent;"
            "}"
            "QLabel#assistantEmptyDesc {"
            "  color: rgba(255,255,255,0.42); font-size: 13px; background: transparent; max-width: 400px;"
            "}"
            "QPushButton#assistantChip {"
            "  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.04);"
            "  border-radius: 10px; padding: 6px 14px; color: rgba(255,255,255,0.62);"
            "  font-size: 11px; font-weight: 500;"
            "}"
            "QPushButton#assistantChip:hover {"
            "  background: rgba(143,183,255,0.08); border: 1px solid rgba(143,183,255,0.12);"
            "  color: rgba(255,255,255,0.84);"
            "}"
            "QScrollArea#assistantChatScroll {"
            "  background: transparent;"
            "  border: none;"
            "}"
            "QWidget#assistantChatContainer {"
            "  background: transparent;"
            "}"
            "QLabel#assistantPrivacyBadge {"
            "  color: rgba(255,255,255,0.48);"
            "  font-size: 11px;"
            "  padding: 6px 16px;"
            "  background: rgba(143,183,255,0.04);"
            "  border-top: 1px solid rgba(255,255,255,0.04);"
            "}"
            "QLineEdit#assistantInput {"
            "  background: rgba(255,255,255,0.04);"
            "  border: 1px solid rgba(255,255,255,0.05);"
            "  border-radius: 12px;"
            "  padding: 10px 14px;"
            "  color: rgba(255,255,255,0.92);"
            "  font-size: 13px;"
            "}"
            "QLineEdit#assistantInput:focus {"
            "  border: 1px solid rgba(143,183,255,0.18);"
            "  background: rgba(255,255,255,0.05);"
            "}"
            "QPushButton#assistantSendBtn {"
            "  background: rgba(143,183,255,0.12);"
            "  border: 1px solid rgba(143,183,255,0.14);"
            "  border-radius: 12px;"
            "  padding: 10px 20px;"
            "  color: rgba(255,255,255,0.92);"
            "  font-size: 13px;"
            "  font-weight: 600;"
            "}"
            "QPushButton#assistantSendBtn:hover {"
            "  background: rgba(143,183,255,0.20);"
            "  border: 1px solid rgba(143,183,255,0.22);"
            "}"
            "QPushButton#assistantSendBtn:pressed {"
            "  background: rgba(143,183,255,0.08);"
            "}"
        )

class _ChatBubble(QFrame):
    def __init__(self, role: str, content: str, parent: QWidget):
        super().__init__(parent)
        self.setObjectName(f"chatBubble_{role}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(content)
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if role == "user":
            label.setObjectName("bubbleUser")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(label)
            layout.setAlignment(Qt.AlignRight)
        else:
            label.setObjectName("bubbleAssistant")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(label)
            layout.setAlignment(Qt.AlignLeft)

        label.setStyleSheet(
            "QLabel#bubbleUser {"
            "  background: rgba(143,183,255,0.10);"
            "  border: 1px solid rgba(143,183,255,0.12);"
            "  border-radius: 14px;"
            "  padding: 10px 16px;"
            "  color: rgba(255,255,255,0.90);"
            "  font-size: 13px;"
            "  max-width: 520px;"
            "}"
            "QLabel#bubbleAssistant {"
            "  background: rgba(255,255,255,0.030);"
            "  border: 1px solid rgba(255,255,255,0.04);"
            "  border-radius: 14px;"
            "  padding: 10px 16px;"
            "  color: rgba(255,255,255,0.84);"
            "  font-size: 13px;"
            "  max-width: 620px;"
            "}"
        )


class _PendingActionCard(QFrame):
    confirmed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, pending: dict, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("pendingActionCard")
        self._action_id = pending.get("action_id", "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel(pending.get("title", "Acción pendiente"))
        title.setObjectName("pendingTitle")
        title.setStyleSheet(
            "QLabel#pendingTitle {"
            "  color: rgba(255,255,255,0.92);"
            "  font-size: 14px;"
            "  font-weight: 600;"
            "}"
        )
        layout.addWidget(title)

        desc = pending.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(
                "QLabel {"
                "  color: rgba(255,255,255,0.62);"
                "  font-size: 12px;"
                "}"
            )
            layout.addWidget(desc_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        confirm_btn = QPushButton("Confirmar")
        confirm_btn.setObjectName("pendingConfirmBtn")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.clicked.connect(lambda: self.confirmed.emit(self._action_id))
        btn_row.addWidget(confirm_btn)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("pendingCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(lambda: self.cancelled.emit(self._action_id))
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

        self.setStyleSheet(
            "QFrame#pendingActionCard {"
            "  background: rgba(143,183,255,0.04);"
            "  border: 1px solid rgba(143,183,255,0.10);"
            "  border-radius: 14px;"
            "}"
            "QPushButton#pendingConfirmBtn {"
            "  background: rgba(143,183,255,0.14);"
            "  border: 1px solid rgba(143,183,255,0.16);"
            "  border-radius: 10px;"
            "  padding: 8px 18px;"
            "  color: rgba(255,255,255,0.94);"
            "  font-size: 12px;"
            "  font-weight: 600;"
            "}"
            "QPushButton#pendingConfirmBtn:hover {"
            "  background: rgba(143,183,255,0.22);"
            "}"
            "QPushButton#pendingCancelBtn {"
            "  background: rgba(255,255,255,0.03);"
            "  border: 1px solid rgba(255,255,255,0.05);"
            "  border-radius: 10px;"
            "  padding: 8px 18px;"
            "  color: rgba(255,255,255,0.58);"
            "  font-size: 12px;"
            "  font-weight: 500;"
            "}"
            "QPushButton#pendingCancelBtn:hover {"
            "  background: rgba(255,255,255,0.06);"
            "  color: rgba(255,255,255,0.78);"
            "}"
        )
