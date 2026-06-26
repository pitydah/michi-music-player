"""MixHubPage — smart mixes, recommendations, and mixed-source playlists."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss,
    card_title_qss, card_desc_qss,
    page_title_qss, page_subtitle_qss,
)


class MixHubPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("mixHubPage")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("mixHubScroll")

        content = QWidget()
        content.setObjectName("mixHubContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 32)
        content_layout.setSpacing(20)

        title = QLabel("Mix")
        title.setObjectName("mixHubTitle")
        content_layout.addWidget(title)

        subtitle = QLabel(
            "Smart mixes, recomendaciones inteligentes y playlists que combinan "
            "música local y remota."
        )
        subtitle.setObjectName("mixHubSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        discover_card = self._build_card(
            "discover", "Descubrir",
            "Smart mixes diarios, no escuchadas, más populares y redescubrimiento.",
            "Explorar",
            "discover",
        )
        cards_layout.addWidget(discover_card, 1)

        recommend_card = self._build_card(
            "recommend", "Recomendaciones IA",
            "Michi Assistant te recomienda música basada en tus gustos, géneros y estado de ánimo.",
            "Abrir asistente",
            "assistant",
        )
        cards_layout.addWidget(recommend_card, 1)

        content_layout.addLayout(cards_layout)

        scopes = self._get_scopes()
        mixed = [s for s in scopes if s.mode == "mixed_sources"]
        if mixed:
            scope_card = self._build_card(
                "mixed", "Scopes de mezcla",
                "Combinaciones de fuentes disponibles para descubrimiento y mixes inteligentes.",
                "Explorar scopes",
                "discover",
            )
            content_layout.addWidget(scope_card)

        playlist_card = self._build_card(
            "playlists", "Playlists y listas inteligentes",
            "Organiza, mezcla e importa tus listas de reproducción. "
            "Combina fuentes locales y remotas.",
            "Gestionar playlists",
            "playlist_hub",
        )
        content_layout.addWidget(playlist_card)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _build_card(self, key: str, title: str, description: str,
                    btn_text: str, navigate_to: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"mixCard_{key}")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        card_title = QLabel(title)
        card_title.setObjectName("mixCardTitle")
        card_title.setStyleSheet(card_title_qss())
        card_layout.addWidget(card_title)

        card_desc = QLabel(description)
        card_desc.setObjectName("mixCardDesc")
        card_desc.setWordWrap(True)
        card_desc.setStyleSheet(card_desc_qss())
        card_layout.addWidget(card_desc)

        card_layout.addStretch()

        btn = QPushButton(btn_text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=None, t=navigate_to: self._navigate(t))
        card_layout.addWidget(btn)

        return card

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    @staticmethod
    def _get_scopes() -> list:
        from library.library_source import build_default_sources, build_default_scopes
        sources = build_default_sources()
        return build_default_scopes(sources)

    def _apply_qss(self):
        self.setStyleSheet(
            page_title_qss() + page_subtitle_qss() + """
            QWidget#mixHubPage { background: #090B11; }
            QScrollArea#mixHubScroll { background: transparent; border: none; }
            QWidget#mixHubContent { background: transparent; }
            QLabel#mixHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#mixHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
        for key, act in [("discover", "secondary"), ("recommend", "accent"), ("playlists", "secondary")]:
            card = self.findChild(QFrame, f"mixCard_{key}")
            if card:
                card.setStyleSheet(glass_card_qss(f"mixCard_{key}"))
            for lbl in (card.findChildren(QLabel) if card else []):
                name = lbl.objectName()
                if "Title" in name:
                    lbl.setStyleSheet(card_title_qss())
                elif "Desc" in name:
                    lbl.setStyleSheet(card_desc_qss())
            for btn in (card.findChildren(QPushButton) if card else []):
                btn.setStyleSheet(glass_button_qss(act))
