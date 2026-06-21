"""Artist Detail View — premium artist page with hero, bio, albums and full tracklist."""
import os as _os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu,
)

from library.artist_grouping import ArtistGroup, ArtistAlbumGroup
from library.album_art import load_cover_pixmap

_BG = "#090B11"
_PANEL = "rgba(255,255,255,0.035)"
_HOVER = "rgba(255,255,255,0.075)"
_SELECTED = "rgba(255,255,255,0.115)"
_BORDER = "rgba(255,255,255,0.08)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"
_ACCENT_BG = "rgba(143,183,255,0.12)"
_ACCENT_BORDER = "rgba(143,183,255,0.24)"

_BTN_CSS = f"""
    QPushButton {{
        background: rgba(255,255,255,0.06); color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.095); border-radius: 12px;
        padding: 8px 14px; font-size: 12.5px; font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.095);
        border: 1px solid rgba(255,255,255,0.15);
    }}
"""


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class ArtistDetailView(QWidget):
    back_requested = Signal()
    play_all_requested = Signal(str)
    queue_all_requested = Signal(str)
    play_album_requested = Signal(list)
    queue_album_requested = Signal(list)
    playlist_artist_requested = Signal(str)
    metadata_artist_requested = Signal(str)
    metadata_files_requested = Signal(list)
    shuffle_all_requested = Signal(str)
    artist_enrich_requested = Signal(str)

    # Track-level signals
    track_play_requested = Signal(str)
    track_queue_requested = Signal(str)
    track_metadata_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._artist: ArtistGroup | None = None
        self._bio_expanded = False
        self._bio_full = ""

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {_BG}; border: none; }}
            QScrollBar:vertical {{
                background: rgba(255,255,255,0.025); width: 10px;
                margin: 4px; border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.18); min-height: 44px; border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.30); }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(32, 16, 32, 40)
        self._layout.setSpacing(24)

        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def set_artist(self, artist: ArtistGroup):
        self._artist = artist
        self._bio_expanded = False
        self._bio_full = getattr(artist, 'bio', '') or ''
        self._rebuild()

    def set_external_info(self, info):
        """Update artist detail with info from TheAudioDB."""
        if not self._artist or not info:
            return
        self._artist.external_id = getattr(info, 'artist_id', '')
        self._artist.mbid = getattr(info, 'mbid', '')
        self._artist.bio = getattr(info, 'biography_preferred', '')
        self._artist.thumb_url = getattr(info, 'thumb_url', '')
        self._artist.banner_url = getattr(info, 'banner_url', '')
        self._artist.logo_url = getattr(info, 'logo_url', '')
        self._artist.fanart_urls = getattr(info, 'fanart_urls', [])
        self._artist.thumb_path = getattr(info, 'thumb_path', '')
        self._artist.banner_path = getattr(info, 'banner_path', '')
        self._artist.logo_path = getattr(info, 'logo_path', '')
        self._artist.fanart_paths = getattr(info, 'fanart_paths', [])
        self._artist.country = getattr(info, 'country', '')
        self._artist.formed_year = getattr(info, 'formed_year', '')
        self._artist.style = getattr(info, 'style', '')
        self._artist.mood = getattr(info, 'mood', '')
        self._artist.website = getattr(info, 'website', '')
        self._artist.genre = getattr(info, 'genre', '')
        self._artist.enrichment_status = "loaded"
        self._bio_full = getattr(info, 'biography_preferred', '') or ''
        self._bio_expanded = False
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        artist = self._artist
        if not artist:
            return

        self._build_banner(artist)
        self._build_actions(artist)

        if self._bio_full:
            self._build_bio(artist)

        if artist.albums:
            self._build_albums_section(artist)

        if artist.all_tracks:
            self._build_all_tracks(artist)

        self._build_info_card(artist)

        self._layout.addStretch()

    # ── Banner ──

    def _build_banner(self, artist: ArtistGroup):
        banner_card = QFrame()
        banner_card.setObjectName("artistBanner")
        banner_card.setMinimumHeight(240)
        banner_card.setMaximumHeight(300)

        # Resolve banner image
        banner_path = getattr(artist, 'banner_path', '') or ''
        if not banner_path:
            fanart = getattr(artist, 'fanart_paths', []) or []
            banner_path = fanart[0] if fanart else ''

        banner_pix = None
        if banner_path and _os.path.exists(banner_path):
            banner_pix = QPixmap(banner_path)

        if banner_pix and not banner_pix.isNull():
            bg_img = (
                f"background-image: url({banner_path});"
                f"background-position: center center;"
                f"background-repeat: no-repeat;"
                f"background-size: cover;")
        else:
            bg_img = (
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 rgba(255,255,255,0.06),"
                "stop:0.5 rgba(255,255,255,0.03),"
                "stop:1 rgba(143,183,255,0.08));")

        banner_card.setStyleSheet(
            f"QFrame#artistBanner {{ {bg_img}"
            f"  border: 1px solid rgba(143,183,255,0.10);"
            f"  border-radius: 22px; }}"
            f"QLabel {{ background: transparent; }}")

        # Overlay gradient for text readability
        overlay = QVBoxLayout(banner_card)
        overlay.setContentsMargins(28, 24, 28, 24)
        overlay.setSpacing(12)

        # Top row: avatar/thumb + logo
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Artist thumb / avatar
        thumb_path = getattr(artist, 'thumb_path', '') or ''
        if thumb_path and _os.path.exists(thumb_path):
            thumb_lbl = QLabel()
            thumb_pix = QPixmap(thumb_path)
            if not thumb_pix.isNull():
                thumb_lbl.setPixmap(thumb_pix.scaled(
                    80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            thumb_lbl.setFixedSize(80, 80)
            thumb_lbl.setAlignment(Qt.AlignCenter)
            thumb_lbl.setStyleSheet(
                "background: rgba(0,0,0,0.30); border-radius: 16px;"
                "border: 2px solid rgba(255,255,255,0.15);")
            top_row.addWidget(thumb_lbl)
        elif artist.cover_paths:
            # Mosaic as avatar fallback
            avatar = QFrame()
            avatar.setFixedSize(80, 80)
            avatar.setStyleSheet(
                "background: rgba(0,0,0,0.30); border-radius: 16px;"
                "border: 2px solid rgba(255,255,255,0.12);")
            avl = QGridLayout(avatar)
            avl.setContentsMargins(4, 4, 4, 4)
            avl.setSpacing(2)
            for ci in range(min(4, len(artist.cover_paths))):
                cp = load_cover_pixmap(artist.cover_paths[ci], 36)
                cl = QLabel()
                if cp and not cp.isNull():
                    cl.setPixmap(cp.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                cl.setAlignment(Qt.AlignCenter)
                avl.addWidget(cl, ci // 2, ci % 2)
            top_row.addWidget(avatar)

        # Logo
        logo_path = getattr(artist, 'logo_path', '') or ''
        if logo_path and _os.path.exists(logo_path):
            logo_lbl = QLabel()
            logo_pix = QPixmap(logo_path)
            if not logo_pix.isNull():
                logo_lbl.setPixmap(logo_pix.scaled(
                    200, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_lbl.setMaximumHeight(60)
            top_row.addWidget(logo_lbl, 1)
            top_row.addStretch()
        else:
            name = QLabel(artist.display_name)
            name.setStyleSheet(
                f"color: {_TEXT}; font-size: 32px; font-weight: 700;")
            top_row.addWidget(name, 1)
            top_row.addStretch()

        overlay.addLayout(top_row)

        # Name (if logo shown, show smaller name)
        if logo_path and _os.path.exists(logo_path):
            name_small = QLabel(artist.display_name)
            name_small.setStyleSheet(
                "color: rgba(255,255,255,0.62); font-size: 14px; font-weight: 500;")
            overlay.addWidget(name_small)

        # Metadata chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        chips = []

        if artist.genres:
            chips.append(", ".join(artist.genres[:2]))
        external_genre = getattr(artist, 'genre', '') or getattr(artist, 'style', '')
        if external_genre and external_genre not in str(chips):
            chips.append(external_genre)
        if getattr(artist, 'country', ''):
            chips.append(artist.country)
        if getattr(artist, 'formed_year', 0):
            chips.append(str(artist.formed_year))
        chips.append(f"{artist.album_count} álbumes")
        chips.append(f"{artist.track_count} canciones")
        dur = _format_dur(artist.total_duration)
        if dur:
            chips.append(dur)

        for chip_text in chips[:7]:
            chip = QLabel(chip_text)
            chip.setStyleSheet(
                f"background: rgba(0,0,0,0.35); color: {_TEXT2};"
                f"font-size: 10.5px; font-weight: 600;"
                f"border: 1px solid rgba(255,255,255,0.10);"
                f"border-radius: 8px; padding: 3px 10px;")
            chips_layout.addWidget(chip)
        chips_layout.addStretch()
        overlay.addLayout(chips_layout)

        overlay.addStretch()
        self._layout.addWidget(banner_card)

    # ── Actions ──

    def _build_actions(self, artist: ArtistGroup):
        row = QHBoxLayout()
        row.setSpacing(10)

        for label, slot in [
            ("▶ Reproducir todo", lambda: self.play_all_requested.emit(artist.key)),
            ("🔀 Aleatorio", lambda: self.shuffle_all_requested.emit(artist.key)),
            ("+ Cola", lambda: self.queue_all_requested.emit(artist.key)),
            ("♫ Crear playlist", lambda: self.playlist_artist_requested.emit(artist.key)),
            ("✏ Editar metadatos", lambda: self.metadata_artist_requested.emit(artist.key)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_CSS)
            btn.clicked.connect(slot)
            row.addWidget(btn)

        row.addStretch()

        refresh_btn = QPushButton("↻ Actualizar info externa")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(_BTN_CSS.replace("8px 14px", "6px 12px").replace("12.5px", "11px"))
        refresh_btn.clicked.connect(lambda: self.artist_enrich_requested.emit(artist.key))
        row.addWidget(refresh_btn)

        self._layout.addLayout(row)

    # ── Bio ──

    def _build_bio(self, artist: ArtistGroup):
        bio_card = _GlassCard()
        bl = QVBoxLayout(bio_card)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(8)

        bio_title = QLabel("Reseña")
        source = ""
        if getattr(artist, 'enrichment_status', '') == "loaded":
            source = " · Información externa"
        bio_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 700; background: transparent;")
        if source:
            bl.addWidget(bio_title)
            src_lbl = QLabel(source)
            src_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 10px; background: transparent;")
            bl.addWidget(src_lbl)
        else:
            bl.addWidget(bio_title)

        display_bio = self._bio_full
        truncated = len(display_bio) > 600 and not self._bio_expanded
        if truncated:
            display_bio = display_bio[:600].rsplit(' ', 1)[0] + "…"

        bio_lbl = QLabel(display_bio)
        bio_lbl.setStyleSheet(
            f"color: {_TEXT3}; font-size: 12px; background: transparent; line-height: 1.5;")
        bio_lbl.setWordWrap(True)
        bl.addWidget(bio_lbl)

        if len(self._bio_full) > 600:
            toggle = QPushButton("Ver más" if not self._bio_expanded else "Ver menos")
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setStyleSheet(
                "QPushButton { color: rgba(143,183,255,0.72); font-size: 11px;"
                "  background: transparent; border: none; font-weight: 600; }"
                "QPushButton:hover { color: rgba(143,183,255,0.92); }")
            toggle.clicked.connect(self._toggle_bio)
            bl.addWidget(toggle)

        self._layout.addWidget(bio_card)

    def _toggle_bio(self):
        self._bio_expanded = not self._bio_expanded
        self._rebuild()

    # ── Albums ──

    def _build_albums_section(self, artist: ArtistGroup):
        section_lbl = QLabel("Álbumes")
        section_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 17px; font-weight: 700; background: transparent;")
        self._layout.addWidget(section_lbl)

        cols = max(1, (self.width() - 64) // 280)
        grid = QGridLayout()
        grid.setSpacing(14)

        for i, album in enumerate(artist.albums):
            card = self._make_album_card(album)
            row = i // cols
            col = i % cols
            grid.addWidget(card, row, col, Qt.AlignTop)

        self._layout.addLayout(grid)

    def _make_album_card(self, album: ArtistAlbumGroup) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {_BORDER};
                border-radius: 16px;
            }}
            QFrame:hover {{
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.13);
            }}
            QLabel {{ background: transparent; }}
        """)
        card.setMinimumWidth(270)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 12)
        v.setSpacing(8)

        # Top: cover + title
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        cover_lbl = QLabel()
        cover_lbl.setFixedSize(72, 72)
        cover_lbl.setAlignment(Qt.AlignCenter)
        pix = load_cover_pixmap(album.cover_path, 68) if album.cover_path else None
        if pix and not pix.isNull():
            cover_lbl.setPixmap(pix.scaled(68, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            cover_lbl.setStyleSheet("border-radius: 12px;")
        else:
            cover_lbl.setStyleSheet(
                "background: rgba(255,255,255,0.04); border-radius: 12px;")
        top_row.addWidget(cover_lbl)

        title_info = QVBoxLayout()
        title_info.setSpacing(2)
        title_lbl = QLabel(album.title)
        title_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 700;")
        title_lbl.setWordWrap(True)
        title_info.addWidget(title_lbl)

        meta = f"{album.track_count} canciones"
        if album.total_duration:
            meta += f" · {_format_dur(album.total_duration)}"
        if album.year:
            meta = f"{album.year} · {meta}"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        title_info.addWidget(meta_lbl)

        title_info.addStretch()
        top_row.addLayout(title_info, 1)
        v.addLayout(top_row)

        # Album formats
        if album.formats:
            fmts = QLabel(" · ".join(f.upper().lstrip(".") for f in album.formats[:3]))
            fmts.setStyleSheet(f"color: {_TEXT3}; font-size: 10px;")
            v.addWidget(fmts)

        # Tracks preview
        track_table = QTableWidget()
        track_table.setColumnCount(3)
        track_table.setHorizontalHeaderLabels(["Nº", "Título", "Dur."])
        track_table.setRowCount(min(len(album.tracks), 5))
        track_table.verticalHeader().setVisible(False)
        track_table.setShowGrid(False)
        track_table.setFrameShape(QFrame.NoFrame)
        track_table.setSelectionMode(QAbstractItemView.NoSelection)
        track_table.setFixedHeight(28 * min(len(album.tracks), 5) + 30)
        track_table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; color: {_TEXT}; border: none; }}
            QTableWidget::item {{ padding: 2px 4px; color: {_TEXT3}; font-size: 10.5px; }}
            QHeaderView::section {{
                background: transparent; color: {_TEXT3}; border: none;
                font-size: 10px; padding: 2px 4px;
            }}
        """)
        track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        track_table.setColumnWidth(0, 30)
        track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        track_table.setColumnWidth(2, 40)

        for ti, track in enumerate(album.tracks[:5]):
            tn = getattr(track, "track_number", 0) or 0
            dur = getattr(track, "duration", 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else ""
            track_table.setItem(ti, 0, QTableWidgetItem(str(tn) if tn else "—"))
            track_table.setItem(ti, 1, QTableWidgetItem(track.title or track.filename))
            track_table.setItem(ti, 2, QTableWidgetItem(dur_s))

        v.addWidget(track_table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        fps = [t.filepath for t in album.tracks]

        play_btn = QPushButton("▶ Reproducir")
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT_BG}; color: {_ACCENT};"
            f"  border: 1px solid {_ACCENT_BORDER}; border-radius: 8px;"
            f"  padding: 5px 10px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: rgba(143,183,255,0.20); }}")
        play_btn.clicked.connect(lambda checked=False, f=fps: self.play_album_requested.emit(f))
        btn_row.addWidget(play_btn)

        queue_btn = QPushButton("+ Cola")
        queue_btn.setCursor(Qt.PointingHandCursor)
        queue_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(255,255,255,0.06); color: {_TEXT2};"
            f"  border: 1px solid rgba(255,255,255,0.09); border-radius: 8px;"
            f"  padding: 5px 10px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.10); }}")
        queue_btn.clicked.connect(lambda checked=False, f=fps: self.queue_album_requested.emit(f))
        btn_row.addWidget(queue_btn)

        btn_row.addStretch()
        v.addLayout(btn_row)

        return card

    # ── All tracks ──

    def _build_all_tracks(self, artist: ArtistGroup):
        section_lbl = QLabel("Todas las canciones")
        section_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 17px; font-weight: 700; background: transparent;")
        self._layout.addWidget(section_lbl)

        all_tracks = artist.all_tracks
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Nº", "Título", "Álbum", "Año", "Duración", "Formato"])
        table.setRowCount(len(all_tracks))
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; color: {_TEXT}; border: none;
              gridline-color: rgba(255,255,255,0.03);
              selection-background-color: {_ACCENT_BG}; selection-color: {_TEXT}; }}
            QTableWidget::item {{ padding: 5px; color: {_TEXT2}; font-size: 11.5px; }}
            QHeaderView::section {{
                background: rgba(255,255,255,0.035); color: {_TEXT3}; border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06); padding: 6px 8px; font-size: 11px;
            }}
        """)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 42)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(2, 150)
        table.setColumnWidth(3, 55)
        table.setColumnWidth(4, 65)
        table.setColumnWidth(5, 60)

        for ti, track in enumerate(all_tracks):
            tn = getattr(track, "track_number", 0) or 0
            dur = getattr(track, "duration", 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else ""
            ext = (getattr(track, "ext", "") or "").upper().lstrip(".")
            year = str(getattr(track, "year", 0)) if getattr(track, "year", 0) else "—"
            album_title = getattr(track, "album", "") or "—"

            table.setItem(ti, 0, QTableWidgetItem(str(tn) if tn else "—"))
            table.setItem(ti, 1, QTableWidgetItem(track.title or track.filename))
            table.setItem(ti, 2, QTableWidgetItem(album_title))
            table.setItem(ti, 3, QTableWidgetItem(year))
            table.setItem(ti, 4, QTableWidgetItem(dur_s))
            table.setItem(ti, 5, QTableWidgetItem(ext))

        # Double-click → play
        table.doubleClicked.connect(self._on_track_dbl_click)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_track_context)

        self._layout.addWidget(table)

    def _on_track_dbl_click(self, idx):
        track = self._artist.all_tracks[idx.row()] if self._artist else None
        if track:
            self.track_play_requested.emit(track.filepath)

    def _on_track_context(self, pos):
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        idx = table.indexAt(pos)
        if not idx.isValid() or not self._artist:
            return
        track = self._artist.all_tracks[idx.row()]
        if not track:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: rgba(22,24,31,0.97); border: 1px solid rgba(255,255,255,0.10);
              border-radius: 10px; padding: 6px 4px; color: {_TEXT2}; font-size: 12.5px; }}
            QMenu::item {{ padding: 7px 32px 7px 16px; border-radius: 6px; }}
            QMenu::item:selected {{ background: rgba(255,255,255,0.09); }}
            QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.08); margin: 4px 8px; }}
        """)

        menu.addAction("Reproducir", lambda: self.track_play_requested.emit(track.filepath))
        menu.addAction("Añadir a cola", lambda: self.track_queue_requested.emit(track.filepath))
        menu.addSeparator()
        menu.addAction("Editar metadatos", lambda: self.track_metadata_requested.emit(track.filepath))
        menu.exec(table.viewport().mapToGlobal(pos))

    # ── Info card ──

    def _build_info_card(self, artist: ArtistGroup):
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(6)

        info_title = QLabel("Información adicional")
        info_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 700; background: transparent;")
        cl.addWidget(info_title)

        data_rows = []
        ext_genre = getattr(artist, 'genre', '') or getattr(artist, 'style', '') or ', '.join(artist.genres[:2])
        if ext_genre:
            data_rows.append(("Género", ext_genre))
        if getattr(artist, 'country', ''):
            data_rows.append(("País", artist.country))
        if getattr(artist, 'formed_year', 0):
            data_rows.append(("Formación", str(artist.formed_year)))
        if getattr(artist, 'mood', ''):
            data_rows.append(("Mood", artist.mood))
        if getattr(artist, 'website', ''):
            data_rows.append(("Sitio web", artist.website))
        if getattr(artist, 'years', []):
            years = artist.years
            yr = f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])
            data_rows.append(("Años en biblioteca", yr))
        data_rows.append(("Álbumes", str(artist.album_count)))
        data_rows.append(("Canciones", str(artist.track_count)))
        dur = _format_dur(artist.total_duration)
        if dur:
            data_rows.append(("Duración total", dur))
        if getattr(artist, 'mbid', ''):
            data_rows.append(("MusicBrainz ID", artist.mbid))
        if getattr(artist, 'external_id', ''):
            data_rows.append(("ID externo", artist.external_id))

        grid = QGridLayout()
        grid.setSpacing(4)
        for ri, (label, value) in enumerate(data_rows):
            kl = QLabel(label)
            kl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent;")
            vl = QLabel(value)
            vl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; font-weight: 600; background: transparent;")
            vl.setWordWrap(True)
            grid.addWidget(kl, ri, 0, Qt.AlignTop)
            grid.addWidget(vl, ri, 1, Qt.AlignTop)

        cl.addLayout(grid)
        self._layout.addWidget(card)


class _GlassCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035);"
            "  border-radius: 14px;"
            "  border: 1px solid rgba(255,255,255,0.065); }"
            "QLabel { background: transparent; }")
