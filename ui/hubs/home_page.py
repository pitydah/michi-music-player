"""HomePage — main landing hub with library stats, continue, recents and quick actions."""

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
                    if a:
                        artists.add(a)
                    al = str(getattr(item, "album", "") or "").strip().lower()
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
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(24)

        title = QLabel("Inicio")
        title.setObjectName("homeTitle")
        cl.addWidget(title)

        stats = self._get_home_stats()
        subtitle = QLabel(
            f"Tu música, tus dispositivos y tus herramientas musicales en un solo lugar. "
            f"{stats.get('total_songs', 0):,} canciones en tu biblioteca."
        )
        subtitle.setObjectName("homeSubtitle")
        subtitle.setWordWrap(True)
        cl.addWidget(subtitle)

        # ── Principal ──
        sec1 = QLabel("ESCUCHAR")
        sec1.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
        cl.addWidget(sec1)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        continue_card = self._build_card(
            "continue", "Continuar escuchando",
            "Retomá donde lo dejaste. La última canción o playlist que estabas reproduciendo.",
            "Reanudar", "primary",
        )
        cards_row.addWidget(continue_card, 1)
        recent_card = self._build_card(
            "recent", "Actividad reciente",
            "Explorá lo que escuchaste recientemente y redescubrí tus favoritos.",
            "Ver recientes", "secondary",
        )
        cards_row.addWidget(recent_card, 1)
        cl.addLayout(cards_row)

        # ── Explorar ──
        sec2 = QLabel("EXPLORAR")
        sec2.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
        cl.addWidget(sec2)
        quick_row = QHBoxLayout()
        quick_row.setSpacing(12)
        for label, target, kind in [
            ("Buscar música", "library", "secondary"),
            ("Playlists", "playlist_hub", "secondary"),
            ("Mix", "mix_hub", "secondary"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss(kind))
            btn.clicked.connect(lambda c=None, t=target: self._navigate(t))
            quick_row.addWidget(btn)
        quick_row.addStretch()
        cl.addLayout(quick_row)

        # ── Herramientas ──
        sec3 = QLabel("MEJORAR COLECCIÓN")
        sec3.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
        cl.addWidget(sec3)
        tool_row = QHBoxLayout()
        tool_row.setSpacing(12)
        for label, target, kind in [
            ("Conexiones", "connections_hub", "secondary"),
            ("Michi Sync", "devices_page", "accent"),
            ("Audio Lab", "audio_lab", "secondary"),
            ("Asistente IA", "assistant", "accent"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss(kind))
            btn.clicked.connect(lambda c=None, t=target: self._navigate(t))
            tool_row.addWidget(btn)
        tool_row.addStretch()
        cl.addLayout(tool_row)

        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _build_card(self, key: str, title: str, description: str,
                    btn_text: str, btn_kind: str = "primary") -> QFrame:
        card = QFrame()
        card.setObjectName(f"homeCard_{key}")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 20, 20, 20)
        cv.setSpacing(10)

        ct = QLabel(title)
        ct.setObjectName(f"homeCardTitle_{key}")
        ct.setStyleSheet(card_title_qss())
        cv.addWidget(ct)

        cd = QLabel(description)
        cd.setObjectName(f"homeCardDesc_{key}")
        cd.setWordWrap(True)
        cd.setStyleSheet(card_desc_qss())
        cv.addWidget(cd)

        cv.addStretch()

        btn = QPushButton(btn_text)
        btn.setObjectName(f"homeCardBtn_{key}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss(btn_kind))
        cv.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"homeCard_{key}", "elevated"))
        return card

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    def _apply_qss(self):
        self.setStyleSheet(
            page_title_qss() + page_subtitle_qss() + """
            QWidget#homePage { background: #090B11; }
            QScrollArea#homeScroll { background: transparent; border: none; }
            QWidget#homeContent { background: transparent; }
            QLabel#homeTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#homeSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
