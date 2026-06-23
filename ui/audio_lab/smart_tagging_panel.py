"""Smart Tagging panel — preview and approve metadata suggestions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QCheckBox, QProgressBar,
)

from ui.audio_lab.models import TagSuggestion
from ui.central.central_styles import glass_button_qss


class SmartTaggingPanel(QWidget):
    suggestions_accepted = Signal(list)
    suggestions_rejected = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("smartTaggingPanel")
        self._suggestions: list[TagSuggestion] = []
        self._checkboxes: list[QCheckBox] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("smartTaggingHeader")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 12, 20, 12)

        self._title = QLabel("Smart Tagging")
        self._title.setObjectName("smartTaggingTitle")
        h_layout.addWidget(self._title)

        self._status_label = QLabel(
            "Busca metadata en MusicBrainz para completar y normalizar tus tags."
        )
        self._status_label.setObjectName("smartTaggingStatus")
        self._status_label.setWordWrap(True)
        h_layout.addWidget(self._status_label)

        layout.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("smartTaggingScroll")

        self._content = QWidget()
        self._content.setObjectName("smartTaggingContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 8, 16, 16)
        self._content_layout.setSpacing(8)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(16, 8, 16, 16)
        actions.setSpacing(8)

        self._progress = QProgressBar()
        self._progress.setObjectName("smartTaggingProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        actions.addWidget(self._progress)

        actions.addStretch()

        self._accept_all_btn = QPushButton("Aceptar todas")
        self._accept_all_btn.setObjectName("stAcceptAll")
        self._accept_all_btn.setCursor(Qt.PointingHandCursor)
        self._accept_all_btn.clicked.connect(lambda: self._on_accept(True))
        actions.addWidget(self._accept_all_btn)

        self._reject_all_btn = QPushButton("Rechazar todas")
        self._reject_all_btn.setObjectName("stRejectAll")
        self._reject_all_btn.setCursor(Qt.PointingHandCursor)
        self._reject_all_btn.clicked.connect(lambda: self._on_accept(False))
        actions.addWidget(self._reject_all_btn)

        self._apply_btn = QPushButton("Aplicar seleccionadas")
        self._apply_btn.setObjectName("stApply")
        self._apply_btn.setCursor(Qt.PointingHandCursor)
        self._apply_btn.clicked.connect(self._on_apply)
        actions.addWidget(self._apply_btn)

        layout.addLayout(actions)

        self._apply_qss()

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#smartTaggingPanel {
                background: transparent;
            }
            QFrame#smartTaggingHeader {
                background: transparent;
                border-bottom: 1px solid rgba(255,255,255,0.03);
            }
            QLabel#smartTaggingTitle {
                color: rgba(255,255,255,0.88);
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#smartTaggingStatus {
                color: rgba(255,255,255,0.52);
                font-size: 12px;
                margin-top: 2px;
            }
            QScrollArea#smartTaggingScroll {
                background: transparent;
                border: none;
            }
            QWidget#smartTaggingContent {
                background: transparent;
            }
        """)
        for btn_name in ("stAcceptAll", "stRejectAll"):
            btn = self.findChild(QPushButton, btn_name)
            if btn:
                btn.setStyleSheet(glass_button_qss("ghost"))
        apply_btn = self.findChild(QPushButton, "stApply")
        if apply_btn:
            apply_btn.setStyleSheet(glass_button_qss("primary"))

    def set_suggestions(self, suggestions: list[TagSuggestion]):
        self._suggestions = suggestions
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._checkboxes.clear()

        if not suggestions:
            label = QLabel("No se encontraron sugerencias de metadata.")
            label.setStyleSheet("color: rgba(255,255,255,0.42); font-size: 12px; padding: 20px;")
            idx = self._content_layout.count() - 1
            self._content_layout.insertWidget(max(0, idx), label)
            self._status_label.setText("Sin sugerencias. Busca metadata con MusicBrainz.")
            self._apply_btn.setEnabled(False)
            return

        self._status_label.setText(
            f"{len(suggestions)} sugerencias encontradas. "
            "Revisa y selecciona las que quieras aplicar."
        )
        self._apply_btn.setEnabled(True)

        for sug in suggestions:
            card = self._build_suggestion_card(sug)
            idx = self._content_layout.count() - 1
            self._content_layout.insertWidget(max(0, idx), card)

    def _build_suggestion_card(self, sug: TagSuggestion) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 10px; background: rgba(255,255,255,0.015); padding: 8px; }"
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        chk = QCheckBox()
        chk.setChecked(sug.confidence >= 0.85)
        chk.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; }")
        self._checkboxes.append(chk)
        layout.addWidget(chk)

        info = QVBoxLayout()
        field_label = QLabel(sug.field.upper())
        field_label.setStyleSheet(
            "QLabel { color: rgba(143,183,255,0.78); font-size: 11px; font-weight: 600; }"
        )
        info.addWidget(field_label)

        change_text = f"'{sug.current or '(vacio)'}' → '{sug.suggested}'"
        change_label = QLabel(change_text)
        change_label.setStyleSheet("QLabel { color: rgba(255,255,255,0.72); font-size: 12px; }")
        change_label.setWordWrap(True)
        info.addWidget(change_label)

        meta_row = QHBoxLayout()
        src = QLabel(f"{sug.source} · {sug.confidence:.0%}")
        src.setStyleSheet("QLabel { color: rgba(255,255,255,0.35); font-size: 10px; }")
        meta_row.addWidget(src)
        meta_row.addStretch()
        info.addLayout(meta_row)

        layout.addLayout(info, 1)

        return card

    def _on_accept(self, accept: bool):
        for chk in self._checkboxes:
            chk.setChecked(accept)

    def _on_apply(self):
        accepted = []
        for i, chk in enumerate(self._checkboxes):
            if chk.isChecked() and i < len(self._suggestions):
                sug = self._suggestions[i]
                sug.apply = True
                accepted.append(sug)
        self.suggestions_accepted.emit(accepted)

    def set_loading(self, loading: bool):
        self._progress.setVisible(loading)
        self._apply_btn.setEnabled(not loading)
        self._accept_all_btn.setEnabled(not loading)
        self._reject_all_btn.setEnabled(not loading)
        if loading:
            self._status_label.setText("Buscando metadata en MusicBrainz...")
