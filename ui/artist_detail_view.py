"""Artist Detail View — Apple Music-style artist page with albums and tracks."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
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

_BTN_CSS = f"""
    QPushButton {{
        background: rgba(255,255,255,0.06); color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.095); border-radius: 12px;
        padding: 8px 14px; font-size: 12.5px; font-weight: 650;
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


def _alb_badge_css(bg: str = "0.045") -> str:
    return f"""
        QFrame {{
            background: rgba(255,255,255,{bg});
            border: 1px solid {_BORDER};
            border-radius: 14px;
        }}
        QFrame:hover {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.13);
        }}
    """


class ArtistDetailView(QWidget):
    back_requested = Signal()
    play_all_requested = Signal(str)
    queue_all_requested = Signal(str)
    play_album_requested = Signal(list)
    queue_album_requested = Signal(list)
    playlist_artist_requested = Signal(str)
    metadata_artist_requested = Signal(str)
    metadata_files_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._artist: ArtistGroup | None = None

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
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        artist = self._artist
        if not artist:
            return

        self._build_hero(artist)
        self._build_actions(artist)

        if artist.albums:
            self._build_albums_section(artist)

        if artist.loose_tracks:
            self._build_loose_tracks(artist)

        self._layout.addStretch()

    def _build_hero(self, artist: ArtistGroup):
        hero = QHBoxLayout()
        hero.setSpacing(20)

        # Cover collage
        cover_size = 180
        cover_frame = QFrame()
        cover_frame.setFixedSize(cover_size, cover_size)
        cover_frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04); border-radius: 24px; }")
        cover_layout = QGridLayout(cover_frame)
        cover_layout.setContentsMargins(6, 6, 6, 6)
        cover_layout.setSpacing(4)

        if artist.cover_paths:
            for ci in range(min(4, len(artist.cover_paths))):
                pix = load_cover_pixmap(artist.cover_paths[ci], cover_size // 2 - 4)
                lbl = QLabel()
                if pix and not pix.isNull():
                    lbl.setPixmap(pix.scaled(cover_size // 2 - 8, cover_size // 2 - 8,
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    lbl.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 10px;")
                lbl.setAlignment(Qt.AlignCenter)
                cover_layout.addWidget(lbl, ci // 2, ci % 2, Qt.AlignCenter)
        hero.addWidget(cover_frame)

        # Info
        info = QVBoxLayout()
        info.setSpacing(6)

        name_lbl = QLabel(artist.display_name)
        name_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 28px; font-weight: 800; background: transparent;")
        info.addWidget(name_lbl)

        dur = _format_dur(artist.total_duration)
        meta = f"{artist.album_count} álbumes · {artist.track_count} canciones"
        if dur:
            meta += f" · {dur}"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 13px; background: transparent;")
        info.addWidget(meta_lbl)

        extra = ""
        if artist.genres:
            extra = ", ".join(artist.genres[:4])
        if artist.years:
            y_str = f"{artist.years[0]}–{artist.years[-1]}" if len(artist.years) > 1 else str(artist.years[0])
            extra = f"{extra} · {y_str}" if extra else y_str
        if extra:
            extra_lbl = QLabel(extra)
            extra_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11.5px; background: transparent;")
            info.addWidget(extra_lbl)

        info.addStretch()
        hero.addLayout(info)
        hero.addStretch()
        self._layout.addLayout(hero)

    def _build_actions(self, artist: ArtistGroup):
        row = QHBoxLayout()
        row.setSpacing(10)

        for label, signal in [
            ("Reproducir todo", lambda: self.play_all_requested.emit(artist.key)),
            ("Aleatorio", lambda: self.play_all_requested.emit(artist.key)),  # shuffle not implemented yet
            ("Añadir a cola", lambda: self.queue_all_requested.emit(artist.key)),
            ("Crear playlist", lambda: self.playlist_artist_requested.emit(artist.key)),
            ("Editar metadatos", lambda: self.metadata_artist_requested.emit(artist.key)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_CSS)
            btn.clicked.connect(signal)
            row.addWidget(btn)

        row.addStretch()
        self._layout.addLayout(row)

    def _build_albums_section(self, artist: ArtistGroup):
        section = QLabel("Álbumes")
        section.setStyleSheet(f"color: {_TEXT}; font-size: 17px; font-weight: 760; background: transparent;")
        self._layout.addWidget(section)

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
        card.setStyleSheet(_alb_badge_css())
        card.setMinimumWidth(260)

        h = QHBoxLayout(card)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(12)

        # Cover
        cover_lbl = QLabel()
        cover_lbl.setFixedSize(64, 64)
        cover_lbl.setAlignment(Qt.AlignCenter)
        pix = load_cover_pixmap(album.cover_path, 60) if album.cover_path else None
        if pix and not pix.isNull():
            cover_lbl.setPixmap(pix.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            cover_lbl.setStyleSheet(
                "background: rgba(255,255,255,0.04); border-radius: 10px;")
        cover_lbl.setStyleSheet(cover_lbl.styleSheet() + " border-radius: 12px;")
        h.addWidget(cover_lbl)

        # Info
        info = QVBoxLayout()
        info.setSpacing(3)

        title = QLabel(album.title)
        title.setStyleSheet(f"color: {_TEXT}; font-size: 13px; font-weight: 650; background: transparent;")
        info.addWidget(title)

        meta = f"{album.track_count} canciones"
        if album.total_duration:
            meta += f" · {_format_dur(album.total_duration)}"
        if album.year:
            meta = f"{album.year} · {meta}"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px; background: transparent;")
        info.addWidget(meta_lbl)

        # Tracks sub-table
        track_table = QTableWidget()
        track_table.setColumnCount(3)
        track_table.setHorizontalHeaderLabels(["Nº", "Título", "Dur."])
        track_table.setRowCount(min(len(album.tracks), 6))
        track_table.verticalHeader().setVisible(False)
        track_table.setShowGrid(False)
        track_table.setFrameShape(QFrame.NoFrame)
        track_table.setSelectionMode(QAbstractItemView.NoSelection)
        track_table.setMinimumHeight(28 * min(len(album.tracks), 6) + 30)
        track_table.setMaximumHeight(28 * min(len(album.tracks), 6) + 30)
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

        for ti, track in enumerate(album.tracks[:6]):
            tn = getattr(track, "track_number", 0) or 0
            dur = getattr(track, "duration", 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else ""
            track_table.setItem(ti, 0, QTableWidgetItem(str(tn) if tn else "—"))
            track_table.setItem(ti, 1, QTableWidgetItem(track.title or track.filename))
            track_table.setItem(ti, 2, QTableWidgetItem(dur_s))

        info.addWidget(track_table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(5)
        fps = [t.filepath for t in album.tracks]

        play_btn = QPushButton("▶")
        play_btn.setFixedSize(30, 28)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet(_BTN_CSS.replace("8px 14px", "2px").replace("12.5px", "11px"))
        play_btn.clicked.connect(lambda checked=False, f=fps: self.play_album_requested.emit(f))
        btn_row.addWidget(play_btn)

        queue_btn = QPushButton("+ Cola")
        queue_btn.setFixedHeight(28)
        queue_btn.setCursor(Qt.PointingHandCursor)
        queue_btn.setStyleSheet(_BTN_CSS.replace("8px 14px", "3px 8px").replace("12.5px", "10px"))
        queue_btn.clicked.connect(lambda checked=False, f=fps: self.queue_album_requested.emit(f))
        btn_row.addWidget(queue_btn)

        btn_row.addStretch()
        info.addLayout(btn_row)

        h.addLayout(info)
        return card

    def _build_loose_tracks(self, artist: ArtistGroup):
        section = QLabel("Canciones sin álbum")
        section.setStyleSheet(f"color: {_TEXT}; font-size: 17px; font-weight: 760; background: transparent;")
        self._layout.addWidget(section)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Nº", "Título", "Duración", "Formato"])
        table.setRowCount(len(artist.loose_tracks))
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; color: {_TEXT}; border: none;
              gridline-color: rgba(255,255,255,0.04);
              selection-background-color: {_SELECTED}; selection-color: {_TEXT}; }}
            QTableWidget::item {{ padding: 5px; color: {_TEXT2}; font-size: 11.5px; }}
            QHeaderView::section {{
                background: rgba(255,255,255,0.035); color: {_TEXT3}; border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06); padding: 6px 8px; font-size: 11px;
            }}
        """)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 40)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(2, 60)
        table.setColumnWidth(3, 60)

        for ti, track in enumerate(artist.loose_tracks):
            tn = getattr(track, "track_number", 0) or 0
            dur = getattr(track, "duration", 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else ""
            ext = (getattr(track, "ext", "") or "").upper().lstrip(".")

            table.setItem(ti, 0, QTableWidgetItem(str(tn) if tn else "—"))
            table.setItem(ti, 1, QTableWidgetItem(track.title or track.filename))
            table.setItem(ti, 2, QTableWidgetItem(dur_s))
            table.setItem(ti, 3, QTableWidgetItem(ext))

        self._layout.addWidget(table)
