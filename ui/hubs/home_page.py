"""HomePage — main landing hub with continue listening, recents, servers, quick actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss


class HomePage(QWidget):
    def __init__(self, db=None, playback=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("homePage")
        self._db = db
        self._playback = playback
        self._build_ui()

    def _get_home_stats(self) -> dict:
        stats = {"total_songs": 0, "total_artists": 0, "total_albums": 0}
        try:
            if self._db and hasattr(self._db, "get_stats"):
                st = self._db.get_stats()
                stats["total_songs"] = st.get("total", 0)
            if self._db and hasattr(self._db, "get_all"):
                items = self._db.get_all() or []
                artists = set()
                albums = set()
                for item in items:
                    a = str(getattr(item, "artist", "") or "").strip().lower()
                    al = str(getattr(item, "album", "") or "").strip().lower()
                    if a:
                        artists.add(a)
                    if al:
                        albums.add(al)
                stats["total_artists"] = len(artists)
                stats["total_albums"] = len(albums)
        except Exception:
            pass
        return stats

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("homeScroll")

        content = QWidget()
        content.setObjectName("homeContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 32)
        content_layout.setSpacing(20)

        title = QLabel("Inicio")
        title.setObjectName("homeTitle")
        content_layout.addWidget(title)

        stats = self._get_home_stats()
        subtitle = QLabel(
            f"Tu música, tus dispositivos y tus servidores en un solo lugar. "
            f"{stats.get('total_songs', 0):,} canciones en tu biblioteca."
        )
        subtitle.setObjectName("homeSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        continue_card = self._build_card(
            "continue", "Continuar escuchando",
            "Retoma donde lo dejaste. La última canción o playlist que estabas reproduciendo.",
            "Reanudar",
        )
        cards_layout.addWidget(continue_card, 1)

        recent_card = self._build_card(
            "recent", "Actividad reciente",
            "Explora lo que has escuchado recientemente y redescubre tus favoritos.",
            "Ver recientes",
        )
        cards_layout.addWidget(recent_card, 1)

        content_layout.addLayout(cards_layout)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(12)

        for label, target in [
            ("Buscar música", "library"),
            ("Playlists", "playlist_hub"),
            ("Recomendaciones", "assistant"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=None, t=target: self._navigate(t))
            quick_row.addWidget(btn)

        quick_row.addStretch()
        content_layout.addLayout(quick_row)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _build_card(self, key: str, title: str, description: str,
                    btn_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"homeCard_{key}")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        card_title = QLabel(title)
        card_title.setObjectName(f"homeCardTitle_{key}")
        card_layout.addWidget(card_title)

        card_desc = QLabel(description)
        card_desc.setObjectName(f"homeCardDesc_{key}")
        card_desc.setWordWrap(True)
        card_layout.addWidget(card_desc)

        card_layout.addStretch()

        btn = QPushButton(btn_text)
        btn.setObjectName(f"homeCardBtn_{key}")
        btn.setCursor(Qt.PointingHandCursor)
        card_layout.addWidget(btn)

        return card

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#homePage { background: #090B11; }
            QScrollArea#homeScroll { background: transparent; border: none; }
            QWidget#homeContent { background: transparent; }
            QLabel#homeTitle {
                color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700;
            }
            QLabel#homeSubtitle {
                color: rgba(255,255,255,0.56); font-size: 13px;
            }
        """)
        button_kinds = {
            "Reanudar": "primary",
            "Ver recientes": "secondary",
            "Buscar música": "secondary",
            "Playlists": "ghost",
            "Recomendaciones": "secondary",
        }
        for key in ("continue", "recent"):
            card = self.findChild(QFrame, f"homeCard_{key}")
            if not card:
                continue
            card.setStyleSheet(glass_card_qss(f"homeCard_{key}", "elevated"))

            title_lbl = card.findChild(QLabel, f"homeCardTitle_{key}")
            if title_lbl:
                title_lbl.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.88); font-size: 16px; "
                    "font-weight: 600; background: transparent; border: none; }"
                )
            desc_lbl = card.findChild(QLabel, f"homeCardDesc_{key}")
            if desc_lbl:
                desc_lbl.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.56); font-size: 12px; "
                    "font-weight: 500; background: transparent; border: none; }"
                )
            card_btn = card.findChild(QPushButton, f"homeCardBtn_{key}")
            if card_btn:
                kind = button_kinds.get(card_btn.text(), "primary")
                card_btn.setStyleSheet(glass_button_qss(kind))

        for btn in self.findChildren(QPushButton):
            if btn.objectName():
                continue
            label = btn.text()
            kind = button_kinds.get(label, "ghost")
            btn.setStyleSheet(glass_button_qss(kind))
