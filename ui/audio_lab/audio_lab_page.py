"""AudioLabPage — main hub for audio lab tools."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss


class AudioLabPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("audioLabPage")
        self._build_ui()
        self._apply_qss()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("audioLabScroll")

        content = QWidget()
        content.setObjectName("audioLabContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 16, 40, 32)
        content_layout.setSpacing(24)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        metadata_card = self._build_card(
            "metadata_editor", "Metadata Studio",
            "Edita metadatos, carátulas, artistas, álbumes y organiza "
            "tu biblioteca con asistencia inteligente.",
            "Abrir Metadata Studio",
        )
        cards_layout.addWidget(metadata_card, 1)

        disc_card = self._build_card(
            "michi_disc_lab", "Michi Disc Lab",
            "Importa CDs de música a FLAC, WAV, ALAC, MP3, Opus u otros "
            "formatos, con extracción segura y metadatos automáticos.",
            "Abrir Michi Disc Lab",
        )
        cards_layout.addWidget(disc_card, 1)

        content_layout.addLayout(cards_layout)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_card(self, key: str, title: str, description: str,
                    btn_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"audioLabCard_{key}")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        card_title = QLabel(title)
        card_title.setObjectName(f"audioLabCardTitle_{key}")
        card_layout.addWidget(card_title)

        card_desc = QLabel(description)
        card_desc.setObjectName(f"audioLabCardDesc_{key}")
        card_desc.setWordWrap(True)
        card_layout.addWidget(card_desc)

        card_layout.addStretch()

        btn = QPushButton(btn_text)
        btn.setObjectName(f"audioLabCardBtn_{key}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.navigate_requested.emit(key))
        card_layout.addWidget(btn)

        return card

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#audioLabPage {
                background: #090B11;
            }
            QScrollArea#audioLabScroll {
                background: transparent;
                border: none;
            }
            QWidget#audioLabContent {
                background: transparent;
            }
        """)
        for key in ("metadata_editor", "michi_disc_lab"):
            card = self.findChild(QFrame, f"audioLabCard_{key}")
            if card:
                card.setStyleSheet(glass_card_qss(f"audioLabCard_{key}"))
            title_lbl = self.findChild(QLabel, f"audioLabCardTitle_{key}")
            if title_lbl:
                title_lbl.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.88); font-size: 16px; "
                    "font-weight: 600; background: transparent; border: none; }"
                )
            desc_lbl = self.findChild(QLabel, f"audioLabCardDesc_{key}")
            if desc_lbl:
                desc_lbl.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.58); font-size: 12px; "
                    "background: transparent; border: none; }"
                )
            btn = self.findChild(QPushButton, f"audioLabCardBtn_{key}")
            if btn:
                btn.setStyleSheet(glass_button_qss("primary"))
