"""Playlist Hub — premium central panel with smart cards and quick actions."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QFrame, QPushButton,
)

HERE = Path(__file__).parent.parent

# ═══════════════════════════════════════════════════════════
# Color tokens
# ═══════════════════════════════════════════════════════════
_HERO_BG = (
    "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
    "stop:0 rgba(255,255,255,0.075),"
    "stop:0.55 rgba(255,255,255,0.040),"
    "stop:1 rgba(255,255,255,0.025))"
)


def _icon_pixmap(name: str, size: int = 32) -> QPixmap:
    from ui.icons import get_icon
    path = get_icon(name)
    if path:
        return QPixmap(path).scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    return pix


def _glass_btn_css(extra: str = "") -> str:
    return f"""
        QPushButton {{
            background: rgba(255,255,255,0.060);
            color: rgba(255,255,255,0.90);
            border: 1px solid rgba(255,255,255,0.095);
            border-radius: 14px;
            padding: 10px 14px;
            font-size: 12.5px;
            font-weight: 650;
            {extra}
        }}
        QPushButton:hover {{
            background: rgba(255,255,255,0.095);
            border: 1px solid rgba(255,255,255,0.150);
        }}
        QPushButton:pressed {{
            background: rgba(255,255,255,0.125);
        }}
    """


def _card_css(name: str, hover_bg: str = "0.055") -> str:
    return f"""
        QFrame#{name} {{
            background: rgba(255,255,255,0.040);
            border: 1px solid rgba(255,255,255,0.070);
            border-radius: 16px;
        }}
        QFrame#{name}:hover {{
            background: rgba(255,255,255,{hover_bg});
            border: 1px solid rgba(255,255,255,0.125);
        }}
    """


# ═══════════════════════════════════════════════════════════
# Smart playlist definitions
# ═══════════════════════════════════════════════════════════

SMART_PLAYLISTS = [
    ("favorites", "Favoritos", "Tu música marcada como favorita", "♥"),
    ("recent", "Recién agregadas", "Canciones añadidas recientemente", "⟳"),
    ("popular", "Más reproducidas", "Lo que más has escuchado", "★"),
    ("unplayed", "No escuchadas", "Descubre canciones pendientes", "⊙"),
    ("flac", "Solo FLAC", "Biblioteca en formato sin pérdida", "〰"),
    ("no_cover", "Sin carátula", "Álbumes que necesitan portada", "□"),
]

CREATE_AUTO = [
    ("from_folder", "Desde carpeta", "Crear playlist desde una carpeta del sistema"),
    ("from_album", "Desde álbum", "Selecciona un álbum y conviértelo en playlist"),
    ("from_artist", "Desde artista", "Todas las canciones de un mismo artista"),
    ("from_genre", "Desde género", "Agrupa por género musical"),
    ("from_search", "Desde búsqueda actual", "Guarda los resultados de búsqueda como playlist"),
    ("from_queue", "Desde cola actual", "Convierte la cola de reproducción en playlist"),
]

IMPORT_TOOLS = [
    ("import_m3u", "Importar M3U / M3U8", "Carga playlists desde archivos externos"),
    ("export_all", "Exportar playlists", "Guarda tus playlists como archivos M3U"),
    ("export_text", "Exportar como texto", "Lista de canciones en formato legible"),
]

UTILITY_TOOLS = [
    ("duplicates", "Detectar duplicados", "Encuentra canciones repetidas en tu biblioteca"),
    ("metadata", "Revisar metadatos", "Busca archivos sin etiquetas completas"),
    ("missing_cover", "Buscar carátulas faltantes", "Álbumes sin portada en la biblioteca"),
    ("empty_pl", "Limpiar playlists vacías", "Elimina playlists sin canciones"),
    ("lost_files", "Encontrar canciones perdidas", "Referencias a archivos que ya no existen"),
]


# ═══════════════════════════════════════════════════════════
# PlaylistHubWidget
# ═══════════════════════════════════════════════════════════

class PlaylistHubWidget(QWidget):
    create_playlist_requested = Signal()
    import_m3u_requested = Signal()
    export_playlists_requested = Signal()
    smart_playlist_requested = Signal(str)
    playlist_open_requested = Signal(int)
    playlist_play_requested = Signal(int)
    playlist_queue_requested = Signal(int)
    playlist_edit_requested = Signal(int)  # new
    create_from_folder_requested = Signal()
    create_from_queue_requested = Signal()
    create_from_album_requested = Signal()
    create_from_artist_requested = Signal()
    create_from_genre_requested = Signal()
    create_from_search_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("playlistHub")
        self.setStyleSheet("QWidget#playlistHub { background: #090B11; }")

        self._playlists: list[dict] = []

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #090B11; border: none; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.025);
                width: 10px; margin: 4px; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                min-height: 44px; border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.30);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(32, 24, 32, 40)
        self._layout.setSpacing(28)

        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def set_playlists(self, playlists: list[dict]):
        self._playlists = playlists or []
        sig = tuple(
            (p.get("id"), p.get("name"), len(p.get("tracks", []) or []), p.get("cover_path"))
            for p in self._playlists
        )
        if sig == getattr(self, '_last_p_sig', None):
            return
        self._last_p_sig = sig
        self._rebuild()

    # ── Build ──

    def _clear_layout(self, layout):
        """Recursively clean a QLayout, deleting all widgets and sub-layouts."""
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    def _rebuild(self):
        self._clear_layout(self._layout)
        self._build_hero()
        self._build_quick_actions()
        if self._playlists:
            self._build_my_playlists()
        self._build_smart_playlists()
        self._build_create_auto()
        self._build_import_tools()
        self._build_utility_tools()
        self._layout.addStretch()

    # ── Hero ──

    def _build_hero(self):
        card = QFrame()
        card.setObjectName("heroCard")
        card.setStyleSheet(f"QFrame#heroCard {{ background: {_HERO_BG}; border: 1px solid rgba(255,255,255,0.085); border-radius: 22px; }}")
        card.setFixedHeight(152)

        h = QHBoxLayout(card)
        h.setContentsMargins(28, 24, 28, 24)
        h.setSpacing(20)

        # Icon
        icon_lbl = QLabel()
        icon_pix = _icon_pixmap("sidebar_playlists", 56)
        if not icon_pix.isNull():
            icon_lbl.setPixmap(icon_pix)
            icon_lbl.setFixedSize(56, 56)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        h.addWidget(icon_lbl)

        v = QVBoxLayout()
        v.setSpacing(4)

        title = QLabel("Playlist")
        title.setObjectName("heroTitle")
        title.setStyleSheet(
            "QLabel#heroTitle { color: #FFFFFF; font-size: 26px; font-weight: 800;"
            "  background: transparent; border: none; }")
        v.addWidget(title)

        sub = QLabel("Organiza, mezcla e importa tus listas de reproducción")
        sub.setObjectName("heroSubtitle")
        sub.setStyleSheet(
            "QLabel#heroSubtitle { color: rgba(255,255,255,0.76); font-size: 13px;"
            "  font-weight: 500; background: transparent; border: none; }")
        v.addWidget(sub)

        pl_count = len(self._playlists)
        total_tracks = sum(len(p.get("tracks", []) or []) for p in self._playlists) if self._playlists else 0
        info = QLabel(f"{pl_count} playlists · {total_tracks} canciones")
        info.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.58); font-size: 11.5px;"
            "  background: transparent; border: none; }")
        v.addWidget(info)

        h.addLayout(v)
        h.addStretch()
        self._layout.addWidget(card)

    # ── Quick Actions ──

    def _build_quick_actions(self):
        self._add_section_heading("Acciones rápidas")
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        row = QHBoxLayout(section)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        actions = [
            ("Nueva playlist", self._on_create_pl),
            ("Importar M3U", self._on_import_m3u),
            ("Exportar", self._on_export),
            ("Desde carpeta", self._on_from_folder),
            ("Desde cola", self._on_from_queue),
        ]
        for label, slot in actions:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_glass_btn_css())
            btn.setFixedHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)

        row.addStretch()
        self._layout.addWidget(section)

    # ── My Playlists ──

    def _build_my_playlists(self):
        self._add_section_heading("Mis playlists", f"{len(self._playlists)} playlists")
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        grid = QGridLayout(section)
        grid.setSpacing(16)
        cols = max(1, (self.width() - 64) // 220)
        for i, pl in enumerate(self._playlists):
            card = self._make_playlist_card(pl)
            grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)
        self._layout.addWidget(section)

    def _make_playlist_card(self, pl: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("playlistCard")
        card.setStyleSheet(_card_css("playlistCard"))
        card.setFixedSize(210, 270)
        card.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(card)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        # Cover — use PlaylistCoverService
        cover_area = QFrame()
        cover_area.setFixedSize(186, 186)
        cover_area.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035); border-radius: 12px; }")

        from ui.services.playlist_cover_service import get_playlist_cover
        tracks = pl.get("tracks", []) or []
        cover = get_playlist_cover(pl, tracks)
        cover_lbl = QLabel()
        if cover and not cover.isNull():
            cover_lbl.setPixmap(cover.scaled(182, 182, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        else:
            cover_lbl.setStyleSheet("background: rgba(255,255,255,0.02); border-radius: 10px;")
        cover_lbl.setAlignment(Qt.AlignCenter)
        cover_lbl.setFixedSize(186, 186)

        cv_layout = QVBoxLayout(cover_area)
        cv_layout.setContentsMargins(0, 0, 0, 0)
        cv_layout.addWidget(cover_lbl)

        v.addWidget(cover_area)

        # Title
        name = pl.get("name", "Sin nombre")
        display_name = name[:22] + "…" if len(name) > 22 else name

        title_lbl = QLabel(display_name)
        title_lbl.setObjectName("playlistTitle")
        title_lbl.setStyleSheet(
            "QLabel#playlistTitle { color: #FFFFFF; font-size: 13px; font-weight: 700;"
            "  background: transparent; border: none; }")
        title_lbl.setWordWrap(False)
        v.addWidget(title_lbl)

        # Meta
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = f"{dur//60}:{int(dur%60):02d}" if dur > 0 else ""
        meta_parts = [f"{count} canciones" if count == 1 else f"{count} canciones"]
        if dur_str:
            meta_parts.append(dur_str)

        meta_lbl = QLabel(" · ".join(meta_parts))
        meta_lbl.setObjectName("playlistMeta")
        meta_lbl.setStyleSheet(
            "QLabel#playlistMeta { color: rgba(255,255,255,0.72); font-size: 11px;"
            "  font-weight: 500; background: transparent; border: none; }")
        v.addWidget(meta_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        play_btn = QPushButton("▶ Reproducir")
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet(_glass_btn_css("padding: 5px 8px; font-size: 10.5px;"))
        play_btn.clicked.connect(lambda: self.playlist_play_requested.emit(pl.get("id", 0)))
        btn_row.addWidget(play_btn)

        queue_btn = QPushButton("+ Cola")
        queue_btn.setCursor(Qt.PointingHandCursor)
        queue_btn.setStyleSheet(_glass_btn_css("padding: 5px 8px; font-size: 10.5px;"))
        queue_btn.clicked.connect(lambda: self.playlist_queue_requested.emit(pl.get("id", 0)))
        btn_row.addWidget(queue_btn)

        edit_btn = QPushButton("✎")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFixedSize(30, 28)
        edit_btn.setStyleSheet(_glass_btn_css("padding: 2px; font-size: 12px;"))
        edit_btn.clicked.connect(lambda: self.playlist_edit_requested.emit(pl.get("id", 0)))
        btn_row.addWidget(edit_btn)

        v.addLayout(btn_row)
        v.addStretch()

        # Click → open
        card.mouseDoubleClickEvent = lambda e: self.playlist_open_requested.emit(pl.get("id", 0))
        return card

    def _load_track_thumb(self, track, size: int) -> QPixmap:
        filepath = getattr(track, 'filepath', '') if not isinstance(track, str) else track
        if filepath and os.path.isfile(filepath):
            try:
                from library.album_art import load_cover_pixmap
                return load_cover_pixmap(filepath, size)
            except Exception:
                import logging
            logging.getLogger("astra").debug("Playlist cover loading failed")
        pix = QPixmap(size, size)
        pix.fill(QColor(255, 255, 255, 12))
        return pix

    # ── Smart Playlists ──

    def _build_smart_playlists(self):
        self._add_section_heading("Inteligentes")
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        grid = QGridLayout(section)
        grid.setSpacing(12)
        cols = max(1, (self.width() - 64) // 220)
        for i, (key, title, desc, symbol) in enumerate(SMART_PLAYLISTS):
            card = self._make_smart_card(key, title, desc, symbol)
            grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)
        self._layout.addWidget(section)

    def _make_smart_card(self, key: str, title: str, desc: str, symbol: str) -> QFrame:
        card = QFrame()
        card.setObjectName("smartCard")
        card.setStyleSheet(_card_css("smartCard"))
        card.setFixedSize(210, 130)
        card.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(6)

        # Icon
        icon_lbl = QLabel(symbol)
        icon_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 20px;"
            "  background: transparent; border: none; }")
        v.addWidget(icon_lbl)

        # Title
        t = QLabel(title)
        t.setStyleSheet(
            "QLabel { color: #FFFFFF; font-size: 13px; font-weight: 650;"
            "  background: transparent; border: none; }")
        v.addWidget(t)

        # Desc
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.60); font-size: 10.5px;"
            "  background: transparent; border: none; }")
        v.addWidget(d)

        v.addStretch()

        card.mouseDoubleClickEvent = lambda e: self.smart_playlist_requested.emit(key)
        return card

    # ── Create automatically ──

    def _build_create_auto(self):
        self._add_section_heading("Crear automáticamente")
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        grid = QGridLayout(section)
        grid.setSpacing(10)
        cols = max(1, (self.width() - 64) // 220)
        for i, (key, title, desc) in enumerate(CREATE_AUTO):
            card = self._make_create_card(key, title, desc)
            grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)
        self._layout.addWidget(section)

    def _make_create_card(self, key: str, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("createCard")
        card.setStyleSheet(_card_css("createCard"))
        card.setFixedSize(210, 110)
        card.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(
            "QLabel { color: #FFFFFF; font-size: 13px; font-weight: 650;"
            "  background: transparent; border: none; }")
        v.addWidget(t)

        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.58); font-size: 10.5px;"
            "  background: transparent; border: none; }")
        v.addWidget(d)

        v.addStretch()

        # Dispatch by key
        signal_map = {
            "from_folder": self.create_from_folder_requested,
            "from_album": self.create_from_album_requested,
            "from_artist": self.create_from_artist_requested,
            "from_genre": self.create_from_genre_requested,
            "from_search": self.create_from_search_requested,
            "from_queue": self.create_from_queue_requested,
        }
        sig = signal_map.get(key)
        if sig:
            card.mouseDoubleClickEvent = lambda e, s=sig: s.emit()
        return card

    # ── Import / Tools ──

    def _build_import_tools(self):
        self._add_section_heading("Importar y exportar")
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        grid = QGridLayout(section)
        grid.setSpacing(10)
        cols = max(1, (self.width() - 64) // 220)
        for i, (key, title, desc) in enumerate(IMPORT_TOOLS):
            card = self._make_tool_card(key, title, desc)
            grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)
        self._layout.addWidget(section)

    def _build_utility_tools(self):
        self._add_section_heading("Herramientas")
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        grid = QGridLayout(section)
        grid.setSpacing(10)
        cols = max(1, (self.width() - 64) // 220)
        for i, (key, title, desc) in enumerate(UTILITY_TOOLS):
            card = self._make_tool_card(key, title, desc)
            grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)
        self._layout.addWidget(section)

    def _make_tool_card(self, key: str, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("toolCard")
        card.setStyleSheet(_card_css("toolCard", "0.050"))
        card.setFixedSize(210, 110)
        card.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(
            "QLabel { color: #FFFFFF; font-size: 12.5px; font-weight: 600;"
            "  background: transparent; border: none; }")
        v.addWidget(t)

        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 10.5px;"
            "  background: transparent; border: none; }")
        v.addWidget(d)

        v.addStretch()
        return card

    # ── Section heading ──

    def _add_section_heading(self, title: str, subtitle: str = ""):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 4, 0, 0)
        h.setSpacing(10)

        t = QLabel(title)
        t.setObjectName("sectionHeading")
        t.setStyleSheet(
            "QLabel#sectionHeading { color: #FFFFFF; font-size: 17px;"
            "  font-weight: 760; background: transparent; border: none; }")
        h.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("sectionSubheading")
            s.setStyleSheet(
                "QLabel#sectionSubheading { color: rgba(255,255,255,0.62);"
                "  font-size: 11.5px; font-weight: 500; background: transparent; border: none; }")
            h.addWidget(s)

        h.addStretch()
        self._layout.addWidget(w)

    # ── Action slots ──

    def _on_create_pl(self):
        self.create_playlist_requested.emit()

    def _on_import_m3u(self):
        self.import_m3u_requested.emit()

    def _on_export(self):
        self.export_playlists_requested.emit()

    def _on_from_folder(self):
        self.create_from_folder_requested.emit()

    def _on_from_queue(self):
        self.create_from_queue_requested.emit()
