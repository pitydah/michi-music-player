"""LibraryHubPage — music library hub with embedded songs table and tab navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTabWidget, QPushButton,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss, tab_bar_qss

_TAB_TO_SECTION = {0: "library", 1: "albums", 2: "artists", 3: "genres", 4: "folders"}


class LibraryHubPage(QWidget):
    tab_changed = Signal(str)
    def __init__(self, db=None, window=None, songs_widget: QWidget | None = None,
                 albums_widget: QWidget | None = None,
                 artists_widget: QWidget | None = None,
                 genres_widget: QWidget | None = None,
                 folders_widget: QWidget | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("libraryHubPage")
        self._db = db
        self._win = window
        self._songs_widget = songs_widget
        self._albums_widget = albums_widget
        self._artists_widget = artists_widget
        self._genres_widget = genres_widget
        self._folders_widget = folders_widget
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
            "Música local, archivos disponibles y estadísticas de tu colección."
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
        self._tabs.setStyleSheet(tab_bar_qss())

        tabs_data = [
            ("canciones", "Canciones", "library",             "Toda tu música local en una tabla con búsqueda y filtros.", "primary"),
            ("albums", "Álbumes", "albums", "Carátulas y navegación visual por álbum.", "secondary"),
            ("artists", "Artistas", "artists", "Explora tu biblioteca por artista y sus álbumes.", "secondary"),
            ("genres", "Géneros", "genres", "Atlas de estilos y familias musicales.", "secondary"),
            ("folders", "Carpetas", "folders", "Explorador de archivos por carpeta en tu disco.", "secondary"),
        ]

        stats = self._get_stats()
        for key, label, nav_key, desc, btn_kind in tabs_data:
            tab = self._build_tab(key, label, nav_key, desc, stats, btn_kind)
            self._tabs.addTab(tab, label)

        layout.addWidget(self._tabs, 1)

        self._tabs.currentChanged.connect(self._on_tab_index_changed)

        self._apply_qss()

    def _on_tab_index_changed(self, index: int):
        section_key = _TAB_TO_SECTION.get(index, "library")
        self.tab_changed.emit(section_key)

    def set_current_section(self, section_key: str, emit: bool = False):
        idx = {v: k for k, v in _TAB_TO_SECTION.items()}.get(section_key, 0)
        self._tabs.setCurrentIndex(idx)
        if emit:
            self.tab_changed.emit(section_key)

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
                    artists.add(a or "artista desconocido")
                    albums.add(al or "sin album")
                stats["total_artists"] = len(artists)
                stats["total_albums"] = len(albums)
        except Exception:
            pass
        return stats

    def _build_tab(self, key: str, label: str, nav_key: str,
                   desc: str, stats: dict, btn_kind: str = "primary") -> QWidget:
        w = QWidget()
        w_layout = QVBoxLayout(w)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.setSpacing(0)

        if key == "canciones" and self._songs_widget is not None:
            w_layout.addWidget(self._songs_widget, 1)
            return w

        if key == "albums" and self._albums_widget is not None:
            w_layout.addWidget(self._albums_widget, 1)
            return w

        if key == "artists" and self._artists_widget is not None:
            w_layout.addWidget(self._artists_widget, 1)
            return w

        if key == "genres" and self._genres_widget is not None:
            w_layout.addWidget(self._genres_widget, 1)
            return w

        if key == "folders" and self._folders_widget is not None:
            w_layout.addWidget(self._folders_widget, 1)
            return w

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
            sc_label = QLabel(f"{stats.get('total_albums', 0):,} álbumes")
        else:
            sc_label = QLabel("Explora tu colección")
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

        card.setStyleSheet(glass_card_qss(f"libTabCard_{key}", "elevated"))
        btn.setStyleSheet(glass_button_qss(btn_kind))

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
                border-radius: 8px; padding: 8px 20px; color: rgba(255,255,255,0.68);
                font-size: 13px; margin-right: 4px;
            }
            QTabBar::tab:hover {
                color: rgba(255,255,255,0.86);
            }
            QTabBar::tab:selected {
                background: rgba(143,183,255,0.13); border: 1px solid rgba(143,183,255,0.22);
                color: rgba(255,255,255,0.96);
            }
        """)
