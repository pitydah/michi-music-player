"""LibraryHubPage — music library hub with real data and navigation to existing views."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTabWidget, QPushButton,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss


class LibraryHubPage(QWidget):
    def __init__(self, db=None, window=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("libraryHubPage")
        self._db = db
        self._win = window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("libraryHubHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)

        title = QLabel("Biblioteca")
        title.setObjectName("libraryHubTitle")
        header_layout.addWidget(title)

        subtitle = QLabel(
            "Musica local, archivos disponibles y estadisticas de tu coleccion."
        )
        subtitle.setObjectName("libraryHubSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        sources = self._get_sources()
        if len(sources) > 1:
            src_bar = QFrame()
            src_bar.setObjectName("librarySourcesBar")
            sr_layout = QHBoxLayout(src_bar)
            sr_layout.setContentsMargins(20, 8, 20, 8)
            sr_layout.setSpacing(8)

            sr_label = QLabel("Fuentes:")
            sr_label.setStyleSheet("QLabel { color: rgba(255,255,255,0.42); font-size: 11px; }")
            sr_layout.addWidget(sr_label)

            for s in sources:
                chip = QLabel(f"{s.name} ({s.source_type})")
                chip.setStyleSheet(
                    "QLabel { background: rgba(143,183,255,0.06); border: 1px solid rgba(143,183,255,0.08); "
                    "border-radius: 8px; padding: 4px 10px; color: rgba(143,183,255,0.62); font-size: 10px; }"
                )
                sr_layout.addWidget(chip)
            sr_layout.addStretch()
            layout.addWidget(src_bar)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("libraryHubTabs")

        tabs_data = [
            ("canciones", "Canciones", "library", "Toda tu musica local en una tabla con busqueda y filtros."),
            ("albums", "Albumes", "albums", "Caratulas y navegacion visual por album."),
            ("artists", "Artistas", "artists", "Explora tu biblioteca por artista y sus albumes."),
            ("genres", "Generos", "genres", "Atlas de estilos y familias musicales."),
            ("folders", "Carpetas", "folders", "Explorador de archivos por carpeta en tu disco."),
        ]

        stats = self._get_stats()
        for key, label, nav_key, desc in tabs_data:
            tab = self._build_tab(key, label, nav_key, desc, stats)
            self._tabs.addTab(tab, label)

        layout.addWidget(self._tabs, 1)

        self._apply_qss()

    def _get_stats(self) -> dict:
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

    def _build_tab(self, key: str, label: str, nav_key: str,
                   desc: str, stats: dict) -> QWidget:
        w = QWidget()
        w_layout = QVBoxLayout(w)
        w_layout.setContentsMargins(20, 20, 20, 20)
        w_layout.setSpacing(16)

        stats_card = QFrame()
        stats_card.setObjectName(f"libStats_{key}")
        sc_layout = QVBoxLayout(stats_card)
        sc_layout.setContentsMargins(20, 16, 20, 16)
        sc_layout.setSpacing(8)

        if key == "canciones":
            sc_label = QLabel(f"{stats.get('total_songs', 0):,} canciones en tu biblioteca")
        elif key == "artists":
            sc_label = QLabel(f"{stats.get('total_artists', 0):,} artistas")
        elif key == "albums":
            sc_label = QLabel(f"{stats.get('total_albums', 0):,} albumes")
        else:
            sc_label = QLabel("Explora tu coleccion")
        sc_label.setStyleSheet(
            "QLabel { color: rgba(143,183,255,0.78); font-size: 14px; font-weight: 600; "
            "background: transparent; border: none; }"
        )
        sc_layout.addWidget(sc_label)
        stats_card.setStyleSheet(
            "QFrame { background: rgba(143,183,255,0.04); border: 1px solid rgba(143,183,255,0.08); "
            "border-radius: 12px; }"
        )
        w_layout.addWidget(stats_card)

        card = QFrame()
        card.setObjectName(f"libTabCard_{key}")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(8)

        c_title = QLabel(label)
        c_title.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.88); font-size: 14px; font-weight: 600; "
            "background: transparent; border: none; }"
        )
        c_layout.addWidget(c_title)

        c_desc = QLabel(desc)
        c_desc.setWordWrap(True)
        c_desc.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 12px; "
            "background: transparent; border: none; }"
        )
        c_layout.addWidget(c_desc)

        btn = QPushButton(f"Abrir {label}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=None, k=nav_key: self._navigate(k))
        c_layout.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"libTabCard_{key}"))
        btn.setStyleSheet(glass_button_qss("primary"))

        w_layout.addWidget(card)
        w_layout.addStretch()
        return w

    def _navigate(self, target: str):
        w = self._win or self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    @staticmethod
    def _get_sources() -> list:
        from library.library_source import build_default_sources
        return build_default_sources()

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#libraryHubPage { background: #090B11; }
            QFrame#libraryHubHeader { background: transparent; border-bottom: 1px solid rgba(255,255,255,0.03); }
            QLabel#libraryHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#libraryHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
            QTabWidget#libraryHubTabs::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
                border-radius: 8px; padding: 8px 20px; color: rgba(255,255,255,0.52);
                font-size: 13px; margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: rgba(143,183,255,0.08); border: 1px solid rgba(143,183,255,0.12);
                color: rgba(143,183,255,0.85);
            }
        """)
