"""PlaybackHubPage — real queue, history, favorites, radio, lyrics."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss,
    card_title_qss, card_desc_qss,
    page_title_qss, page_subtitle_qss,
)


class PlaybackHubPage(QWidget):
    def __init__(self, db=None, playback=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("playbackHubPage")
        self._db = db
        self._playback = playback
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("playbackHubScroll")

        content = QWidget()
        content.setObjectName("playbackHubContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 32)
        content_layout.setSpacing(20)

        title = QLabel("Reproducción")
        title.setObjectName("playbackHubTitle")
        content_layout.addWidget(title)

        stats = self._get_stats()
        subtitle = QLabel(
            f"Cola actual, historial, favoritos ({stats.get('fav_count', 0)}), "
            f"radio y letras."
        )
        subtitle.setObjectName("playbackHubSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        actions = [
            ("favs", "Favoritos", f"{stats.get('fav_count', 0)} canciones marcadas como favoritas."),
            ("recent", "Historial", "Canciones reproducidas recientemente."),
            ("radio", "Radio / Flow", "Emisoras de radio por URL y estaciones guardadas."),
        ]

        for key, label, desc in actions:
            card = self._build_card(key, label, desc)
            content_layout.addWidget(card)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _get_stats(self) -> dict:
        stats = {"fav_count": 0}
        try:
            if self._db and hasattr(self._db, "get_favorites"):
                favs = self._db.get_favorites() or []
                stats["fav_count"] = len(favs)
        except Exception:
            pass
        return stats

    def _build_card(self, key: str, title: str, description: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"playbackCard_{key}")

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(8)

        c_title = QLabel(title)
        c_title.setObjectName("playbackCardTitle")
        c_title.setStyleSheet(card_title_qss())
        c_layout.addWidget(c_title)

        c_desc = QLabel(description)
        c_desc.setObjectName("playbackCardDesc")
        c_desc.setWordWrap(True)
        c_desc.setStyleSheet(card_desc_qss())
        c_layout.addWidget(c_desc)

        btn = QPushButton(f"Abrir {title}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=None, k=key: self._navigate(k))
        c_layout.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"playbackCard_{key}"))
        return card

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    def _apply_qss(self):
        self.setStyleSheet(
            page_title_qss() + page_subtitle_qss() + """
            QWidget#playbackHubPage { background: #090B11; }
            QScrollArea#playbackHubScroll { background: transparent; border: none; }
            QWidget#playbackHubContent { background: transparent; }
            QLabel#playbackHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#playbackHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
        for key, act in [("favs", "secondary"), ("recent", "secondary"), ("radio", "secondary")]:
            card = self.findChild(QFrame, f"playbackCard_{key}")
            if card:
                card.setStyleSheet(glass_card_qss(f"playbackCard_{key}"))
            for lbl in (card.findChildren(QLabel) if card else []):
                name = lbl.objectName()
                if "Title" in name:
                    lbl.setStyleSheet(card_title_qss())
                elif "Desc" in name:
                    lbl.setStyleSheet(card_desc_qss())
            for btn in (card.findChildren(QPushButton) if card else []):
                btn.setStyleSheet(glass_button_qss(act))
