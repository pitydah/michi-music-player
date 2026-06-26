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
_PANEL = "rgba(255,255,255,0.025)"
_HOVER = "rgba(255,255,255,0.050)"
_BORDER = "rgba(255,255,255,0.025)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"
_ACCENT_BG = "rgba(143,183,255,0.12)"
_ACCENT_BORDER = "rgba(143,183,255,0.18)"

_BTN_CSS = f"""
    QPushButton {{
        background: rgba(255,255,255,0.05); color: {_TEXT2};
        border: 1px solid rgba(255,255,255,0.04); border-radius: 12px;
        padding: 8px 14px; font-size: 12.5px; font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.08); color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.07);
    }}
"""

_MAX_CHIPS = 6
_MAX_CHIP_LEN = 22


def _normalize_artist_tags(artist: ArtistGroup) -> list[str]:
    """Collect, deduplicate and normalize display tags for an artist."""
    seen = set()
    tags = []

    for genre in (artist.genres or []):
        g = genre.strip()
        if g and g.lower() not in seen:
            seen.add(g.lower())
            tags.append(g)

    ext_genre = (getattr(artist, 'genre', '') or getattr(artist, 'style', '') or '').strip()
    if ext_genre and ext_genre.lower() not in seen:
        seen.add(ext_genre.lower())
        tags.append(ext_genre)

    return tags


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
                background: transparent; width: 8px; margin: 4px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.10); min-height: 40px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.18); }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(32, 16, 32, 40)
        self._layout.setSpacing(20)

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
        elif getattr(artist, 'enrichment_status', '') != "loaded":
            self._build_no_bio_placeholder(artist)

        if artist.albums:
            self._build_albums_section(artist)

        if artist.all_tracks:
            self._build_all_tracks(artist)

        self._build_info_card(artist)

        self._layout.addStretch()

    # ── Banner ──

    def _build_banner(self, artist: ArtistGroup):
        card = _SectionCard("artistHero")
        overlay_layout = QVBoxLayout(card)
        overlay_layout.setContentsMargins(28, 24, 28, 24)
        overlay_layout.setSpacing(8)

        # Banner background
        banner_path = getattr(artist, 'banner_path', '') or ''
        if not banner_path:
            fanart = getattr(artist, 'fanart_paths', []) or []
            banner_path = fanart[0] if fanart else ''

        bg_img = ""
        if banner_path and _os.path.exists(banner_path):
            pix = QPixmap(banner_path)
            if not pix.isNull():
                bg_img = (
                    f"background-image: url({banner_path});"
                    f"background-position: center center;"
                    f"background-repeat: no-repeat;"
                    f"background-size: cover;")

        if bg_img:
            card.setStyleSheet(card.styleSheet() + bg_img)

        # Avatar + name row
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        thumb_path = getattr(artist, 'thumb_path', '') or ''
        if thumb_path and _os.path.exists(thumb_path):
            thumb_lbl = QLabel()
            thumb_pix = QPixmap(thumb_path)
            if not thumb_pix.isNull():
                thumb_lbl.setPixmap(thumb_pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            thumb_lbl.setFixedSize(72, 72)
            thumb_lbl.setAlignment(Qt.AlignCenter)
            thumb_lbl.setStyleSheet(
                "background: rgba(0,0,0,0.30); border-radius: 16px;"
                "border: 1px solid rgba(255,255,255,0.10);")
            top_row.addWidget(thumb_lbl)
        elif artist.cover_paths:
            avatar = QFrame()
            avatar.setFixedSize(72, 72)
            avatar.setStyleSheet(
                "background: rgba(0,0,0,0.30); border-radius: 16px;"
                "border: 1px solid rgba(255,255,255,0.08);")
            avl = QGridLayout(avatar)
            avl.setContentsMargins(3, 3, 3, 3)
            avl.setSpacing(1)
            for ci in range(min(4, len(artist.cover_paths))):
                cp = load_cover_pixmap(artist.cover_paths[ci], 33)
                cl = QLabel()
                if cp and not cp.isNull():
                    cl.setPixmap(cp.scaled(31, 31, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                cl.setAlignment(Qt.AlignCenter)
                avl.addWidget(cl, ci // 2, ci % 2)
            top_row.addWidget(avatar)

        # Name
        name = QLabel(artist.display_name)
        name.setStyleSheet(f"color: {_TEXT}; font-size: 28px; font-weight: 700;")
        top_row.addWidget(name, 1)
        top_row.addStretch()
        overlay_layout.addLayout(top_row)

        # Subtitle
        dur = _format_dur(artist.total_duration)
        sub = f"{artist.album_count} álbumes · {artist.track_count} canciones"
        if dur:
            sub += f" · {dur}"
        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 12px; font-weight: 500;")
        overlay_layout.addWidget(sub_lbl)

        # Chips — normalized and limited
        tags = _normalize_artist_tags(artist)
        chips_info = []
        for t in tags[:(_MAX_CHIPS - 3)]:
            chips_info.append(t[:_MAX_CHIP_LEN] + ("…" if len(t) > _MAX_CHIP_LEN else ""))
        if getattr(artist, 'country', ''):
            chips_info.append(artist.country)
        if getattr(artist, 'formed_year', 0):
            chips_info.append(str(artist.formed_year))

        overflow = len(tags) + len(chips_info) - len(chips_info)
        chips_info = chips_info[:_MAX_CHIPS]
        if overflow > 0 or len(tags) > _MAX_CHIPS:
            chips_info.append(f"+{max(overflow, len(tags) - _MAX_CHIPS + 2)}")

        if chips_info:
            chips_layout = QHBoxLayout()
            chips_layout.setSpacing(5)
            for ct in chips_info:
                chip = QLabel(ct)
                chip.setStyleSheet(
                    f"background: rgba(0,0,0,0.35); color: {_TEXT2};"
                    f"font-size: 10px; font-weight: 600;"
                    f"border: 1px solid rgba(255,255,255,0.06);"
                    f"border-radius: 7px; padding: 2px 8px;")
                chips_layout.addWidget(chip)
            chips_layout.addStretch()
            overlay_layout.addLayout(chips_layout)

        overlay_layout.addStretch()
        self._layout.addWidget(card)

    # ── Actions ──

    def _build_actions(self, artist: ArtistGroup):
        row = QHBoxLayout()
        row.setSpacing(8)

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

        refresh_btn = QPushButton("↻ Actualizar metadatos externos")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(
            _BTN_CSS.replace("8px 14px", "6px 12px").replace("12.5px", "11px"))
        refresh_btn.clicked.connect(lambda: self.artist_enrich_requested.emit(artist.key))
        row.addWidget(refresh_btn)

        self._layout.addLayout(row)

    # ── Bio ──

    def _build_bio(self, artist: ArtistGroup):
        card = _SectionCard("artistBio")
        bl = QVBoxLayout(card)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(6)

        bio_title = QLabel("Reseña")
        bio_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 700; background: transparent; border: none;")
        bl.addWidget(bio_title)

        if getattr(artist, 'enrichment_status', '') == "loaded":
            src = QLabel("Información externa")
            src.setStyleSheet(f"color: {_TEXT3}; font-size: 10px; background: transparent; border: none;")
            bl.addWidget(src)

        display_bio = self._bio_full
        truncated = len(display_bio) > 600 and not self._bio_expanded
        if truncated:
            display_bio = display_bio[:600].rsplit(' ', 1)[0] + "…"

        bio_lbl = QLabel(display_bio)
        bio_lbl.setStyleSheet(
            f"color: {_TEXT3}; font-size: 12px; background: transparent; border: none;")
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

        self._layout.addWidget(card)

    def _build_no_bio_placeholder(self, artist: ArtistGroup):
        card = _SectionCard("artistBio")
        bl = QVBoxLayout(card)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(6)
        t = QLabel("No hay reseña disponible. Puedes actualizar la información externa.")
        t.setStyleSheet(f"color: {_TEXT3}; font-size: 12px; background: transparent; border: none;")
        t.setWordWrap(True)
        bl.addWidget(t)
        btn = QPushButton("Actualizar metadatos externos")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(_BTN_CSS.replace("8px 14px", "6px 12px").replace("12.5px", "11px"))
        btn.clicked.connect(lambda: self.artist_enrich_requested.emit(artist.key))
        bl.addWidget(btn)
        self._layout.addWidget(card)

    def _toggle_bio(self):
        self._bio_expanded = not self._bio_expanded
        self._rebuild()

    # ── Albums ──

    def _build_albums_section(self, artist: ArtistGroup):
        card = _SectionCard("artistAlbums")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 16, 20, 16)
        cv.setSpacing(12)

        header = QLabel("Álbumes")
        header.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 700; background: transparent; border: none;")
        cv.addWidget(header)

        cols = max(1, (self.width() - 64) // 280)
        grid = QGridLayout()
        grid.setSpacing(12)

        for i, album in enumerate(artist.albums):
            album_card = self._make_album_card(album)
            row = i // cols
            col = i % cols
            grid.addWidget(album_card, row, col, Qt.AlignTop)

        cv.addLayout(grid)
        self._layout.addWidget(card)

    def _make_album_card(self, album: ArtistAlbumGroup) -> QFrame:
        card = QFrame()
        card.setObjectName("albumCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame#albumCard {{
                background: rgba(255,255,255,0.025);
                border: 1px solid {_BORDER};
                border-radius: 14px;
            }}
            QFrame#albumCard:hover {{
                background: rgba(255,255,255,0.045);
                border: 1px solid rgba(143,183,255,0.10);
            }}
            QFrame#albumCard QLabel {{ background: transparent; border: none; }}
        """)
        card.setMinimumWidth(260)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 12)
        v.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        cover_lbl = QLabel()
        cover_lbl.setFixedSize(68, 68)
        cover_lbl.setAlignment(Qt.AlignCenter)
        pix = load_cover_pixmap(album.cover_path, 64) if album.cover_path else None
        if pix and not pix.isNull():
            cover_lbl.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            cover_lbl.setStyleSheet("border-radius: 10px;")
        else:
            cover_lbl.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 10px;")
        top_row.addWidget(cover_lbl)

        title_info = QVBoxLayout()
        title_info.setSpacing(2)
        title_lbl = QLabel(album.title)
        title_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 13px; font-weight: 700;")
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

        # Format badges — soft chips
        if album.formats:
            fmts_row = QHBoxLayout()
            fmts_row.setSpacing(4)
            for f in album.formats[:3]:
                fb = QLabel(f.upper().lstrip("."))
                fb.setStyleSheet(
                    f"background: rgba(255,255,255,0.04); color: {_TEXT3};"
                    f"font-size: 9px; font-weight: 600;"
                    f"border-radius: 5px; padding: 1px 6px;")
                fmts_row.addWidget(fb)
            fmts_row.addStretch()
            v.addLayout(fmts_row)

        # Track preview — simple rows, no QTableWidget
        preview_count = min(len(album.tracks), 4)
        for ti in range(preview_count):
            track = album.tracks[ti]
            tr = QHBoxLayout()
            tr.setSpacing(6)
            tn = getattr(track, "track_number", 0) or 0
            dur_v = getattr(track, "duration", 0) or 0
            dur_s = f"{int(dur_v // 60)}:{int(dur_v % 60):02d}" if dur_v else ""
            tn_lbl = QLabel(str(tn) if tn else "—")
            tn_lbl.setFixedWidth(24)
            tn_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 10px;")
            tr.addWidget(tn_lbl)
            title_tr = QLabel(track.title or track.filename)
            title_tr.setStyleSheet(f"color: {_TEXT3}; font-size: 10px;")
            tr.addWidget(title_tr, 1)
            dur_tr = QLabel(dur_s)
            dur_tr.setStyleSheet(f"color: {_TEXT3}; font-size: 10px;")
            dur_tr.setFixedWidth(40)
            dur_tr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tr.addWidget(dur_tr)
            v.addLayout(tr)

        if len(album.tracks) > preview_count:
            more = QLabel(f"+{len(album.tracks) - preview_count} más")
            more.setStyleSheet(f"color: {_TEXT3}; font-size: 10px; font-style: italic;")
            v.addWidget(more)

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
        play_btn.clicked.connect(lambda c=False, f=fps: self.play_album_requested.emit(f))
        btn_row.addWidget(play_btn)

        queue_btn = QPushButton("+ Cola")
        queue_btn.setCursor(Qt.PointingHandCursor)
        queue_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(255,255,255,0.05); color: {_TEXT2};"
            f"  border: 1px solid rgba(255,255,255,0.04); border-radius: 8px;"
            f"  padding: 5px 10px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.08); }}")
        queue_btn.clicked.connect(lambda c=False, f=fps: self.queue_album_requested.emit(f))
        btn_row.addWidget(queue_btn)

        btn_row.addStretch()
        v.addLayout(btn_row)

        return card

    # ── All tracks ──

    def _build_all_tracks(self, artist: ArtistGroup):
        card = _SectionCard("artistTracks")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 16, 20, 16)
        cv.setSpacing(8)

        header = QLabel("Todas las canciones")
        header.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 700; background: transparent; border: none;")
        cv.addWidget(header)

        dur = _format_dur(artist.total_duration)
        sub = f"{artist.track_count} canciones"
        if dur:
            sub += f" · {dur}"
        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
        cv.addWidget(sub_lbl)

        all_tracks = artist.all_tracks
        n_tracks = len(all_tracks)

        # Height: header(30) + rows(n) * 28 + padding(12), max 420px
        visible_rows = min(n_tracks, 12)
        table_h = 30 + visible_rows * 28 + 12

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Nº", "Título", "Álbum", "Año", "Dur.", "Formato"])
        table.setRowCount(n_tracks)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setMinimumHeight(min(table_h, 420))
        if n_tracks > 12:
            table.setMaximumHeight(420)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            table.setFixedHeight(table_h)
        table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; color: {_TEXT}; border: none;
              gridline-color: transparent;
              selection-background-color: {_ACCENT_BG}; selection-color: {_TEXT}; }}
            QTableWidget::item {{ padding: 4px; color: {_TEXT2}; font-size: 11px; border: none; }}
            QHeaderView::section {{
                background: rgba(255,255,255,0.025); color: {_TEXT3}; border: none;
                border-bottom: 1px solid rgba(255,255,255,0.03); padding: 5px 6px; font-size: 10.5px;
            }}
        """)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 38)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(2, 130)
        table.setColumnWidth(3, 50)
        table.setColumnWidth(4, 55)
        table.setColumnWidth(5, 55)

        for ti, track in enumerate(all_tracks):
            tn = getattr(track, "track_number", 0) or 0
            dur_v = getattr(track, "duration", 0) or 0
            dur_s = f"{int(dur_v // 60)}:{int(dur_v % 60):02d}" if dur_v else ""
            ext = (getattr(track, "ext", "") or "").upper().lstrip(".")
            year_s = str(getattr(track, "year", 0)) if getattr(track, "year", 0) else "—"
            album_s = getattr(track, "album", "") or "—"

            table.setItem(ti, 0, _cell(str(tn) if tn else "—"))
            table.setItem(ti, 1, _cell(track.title or track.filename))
            table.setItem(ti, 2, _cell(album_s))
            table.setItem(ti, 3, _cell(year_s))
            table.setItem(ti, 4, _cell(dur_s))
            table.setItem(ti, 5, _cell(ext))

        table.doubleClicked.connect(self._on_track_dbl_click)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_track_context)

        cv.addWidget(table)
        self._layout.addWidget(card)

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
        menu.setStyleSheet("""
            QMenu { background: rgba(20,22,28,0.97); border: 1px solid rgba(255,255,255,0.06);
              border-radius: 10px; padding: 6px 4px; color: rgba(255,255,255,0.88); font-size: 12.5px; }
            QMenu::item { padding: 7px 28px 7px 14px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(143,183,255,0.16); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.06); margin: 4px 8px; }
        """)
        menu.addAction("Reproducir", lambda: self.track_play_requested.emit(track.filepath))
        menu.addAction("Añadir a cola", lambda: self.track_queue_requested.emit(track.filepath))
        menu.addSeparator()
        menu.addAction("Editar metadatos", lambda: self.track_metadata_requested.emit(track.filepath))
        menu.exec(table.viewport().mapToGlobal(pos))

    # ── Info card ──

    def _build_info_card(self, artist: ArtistGroup):
        card = _SectionCard("artistInfo")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(4)

        info_title = QLabel("Información adicional")
        info_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 15px; font-weight: 700; background: transparent; border: none;")
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
        grid.setSpacing(3)
        for ri, (label, value) in enumerate(data_rows):
            kl = QLabel(label)
            kl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent; border: none;")
            vl = QLabel(value)
            vl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; font-weight: 600; background: transparent; border: none;")
            vl.setWordWrap(True)
            grid.addWidget(kl, ri, 0, Qt.AlignTop)
            grid.addWidget(vl, ri, 1, Qt.AlignTop)

        cl.addLayout(grid)
        self._layout.addWidget(card)


# ── Helpers ──

def _cell(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    return item


class _SectionCard(QFrame):
    """Soft glass section card with objectName."""
    def __init__(self, name: str):
        super().__init__()
        self.setObjectName(name)
        self.setStyleSheet(f"""
            QFrame#{name} {{
                background: rgba(255,255,255,0.035);
                border: 1px solid rgba(255,255,255,0.045);
                border-radius: 16px;
            }}
            QFrame#{name} QLabel {{
                background: transparent;
                border: none;
            }}
        """)
