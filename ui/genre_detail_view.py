"""Genre Detail View — premium page for a genre with tracks, albums, and artists."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from metadata.genre_grouping import GenreGroup
from metadata.genre_taxonomy import get_mood_hints
from library.album_art import load_cover_pixmap

_BG = "#090B11"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"

_BTN = """
    QPushButton { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.78);
    border: 1px solid rgba(255,255,255,0.04); border-radius: 10px;
    padding: 7px 12px; font-size: 12px; font-weight: 600; }
    QPushButton:hover { background: rgba(255,255,255,0.08); }
"""


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class GenreDetailView(QWidget):
    back_requested = Signal()
    play_requested = Signal(str)
    shuffle_requested = Signal(str)
    queue_requested = Signal(str)
    playlist_requested = Signal(str)
    metadata_requested = Signal(str)
    normalize_requested = Signal(str)
    track_play_requested = Signal(str)
    track_queue_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._genre: GenreGroup | None = None

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {_BG}; border: none; }}"
            "QScrollBar:vertical { background: transparent; width: 4px; margin: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.10); border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(28, 14, 28, 36)
        self._layout.setSpacing(18)

        self._scroll.setWidget(self._container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def set_genre(self, genre: GenreGroup):
        self._genre = genre
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        g = self._genre
        if not g:
            return

        self._build_hero(g)
        self._build_actions(g)

        if g.tracks:
            self._build_tracks(g)

        if g.artists:
            self._build_artists(g)

        self._build_info(g)
        self._layout.addStretch()

    def _build_hero(self, g: GenreGroup):
        card = _SectionCard("genreDetailHero")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(8)

        # Mosaic + name
        top = QHBoxLayout()
        top.setSpacing(16)
        cover = QFrame()
        cover.setFixedSize(80, 80)
        cover.setStyleSheet("background: transparent; border-radius: 12px;")
        cv = QGridLayout(cover)
        cv.setContentsMargins(2, 2, 2, 2)
        cv.setSpacing(1)
        for ci, cp in enumerate(g.cover_paths[:4]):
            pix = load_cover_pixmap(cp, 38) if cp else None
            lbl = QLabel()
            if pix and not pix.isNull():
                lbl.setPixmap(pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lbl.setAlignment(Qt.AlignCenter)
            cv.addWidget(lbl, ci // 2, ci % 2)
        top.addWidget(cover)

        info = QVBoxLayout()
        info.setSpacing(4)
        name = QLabel(g.name)
        name.setStyleSheet(f"color: {_TEXT}; font-size: 24px; font-weight: 700;")
        info.addWidget(name)

        family = QLabel(g.family)
        family.setStyleSheet(f"color: {_ACCENT}; font-size: 12px; font-weight: 600;")
        info.addWidget(family)

        stats = f"{g.track_count} canciones · {g.artist_count} artistas · {g.album_count} álbumes"
        dur = _format_dur(g.total_duration)
        if dur:
            stats += f" · {dur}"
        s_lbl = QLabel(stats)
        s_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        info.addWidget(s_lbl)
        top.addLayout(info, 1)
        cl.addLayout(top)

        # Mood chips
        hints = get_mood_hints(g.name)
        if hints.get("mood"):
            chips = QHBoxLayout()
            chips.setSpacing(5)
            for mood in hints["mood"][:4]:
                chip = QLabel(mood)
                chip.setStyleSheet(
                    f"background: rgba(143,183,255,0.08); color: {_ACCENT};"
                    f"border-radius: 6px; padding: 2px 8px; font-size: 10px;")
                chips.addWidget(chip)
            chips.addStretch()
            cl.addLayout(chips)

        self._layout.addWidget(card)

    def _build_actions(self, g: GenreGroup):
        row = QHBoxLayout()
        row.setSpacing(8)
        for label, slot in [
            ("▶ Reproducir todo", lambda: self.play_requested.emit(g.key)),
            ("🔀 Aleatorio", lambda: self.shuffle_requested.emit(g.key)),
            ("+ Cola", lambda: self.queue_requested.emit(g.key)),
            ("♫ Crear playlist", lambda: self.playlist_requested.emit(g.key)),
            ("🔧 Normalizar", lambda: self.normalize_requested.emit(g.key)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch()
        self._layout.addLayout(row)

    def _build_tracks(self, g: GenreGroup):
        card = _SectionCard("genreTracks")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 14, 18, 14)
        cv.setSpacing(8)

        hdr = QLabel("Canciones")
        hdr.setStyleSheet(f"color: {_TEXT}; font-size: 15px; font-weight: 700;")
        cv.addWidget(hdr)

        n = len(g.tracks)
        visible = min(n, 10)
        th = 28 + visible * 26 + 10
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Nº", "Título", "Artista", "Álbum", "Dur."])
        table.setRowCount(n)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        if n > 10:
            table.setMaximumHeight(400)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            table.setFixedHeight(th)
        table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; color: {_TEXT}; border: none; gridline-color: transparent;
              selection-background-color: rgba(143,183,255,0.14); selection-color: {_TEXT}; }}
            QTableWidget::item {{ padding: 3px; color: {_TEXT2}; font-size: 11px; border: none; }}
            QHeaderView::section {{ background: rgba(255,255,255,0.02); color: {_TEXT3};
              border: none; border-bottom: 1px solid rgba(255,255,255,0.02); padding: 4px; font-size: 10px; }}
        """)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 32)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(2, 130)
        table.setColumnWidth(3, 130)
        table.setColumnWidth(4, 45)

        for ti, t in enumerate(g.tracks):
            tn = getattr(t, "track_number", 0) or 0
            dur_v = getattr(t, "duration", 0) or 0
            dur_s = f"{int(dur_v // 60)}:{int(dur_v % 60):02d}" if dur_v else ""
            artist = getattr(t, "artist", "") or "—"
            album = getattr(t, "album", "") or "—"
            table.setItem(ti, 0, _cell(str(tn) if tn else "—"))
            table.setItem(ti, 1, _cell(t.title or t.filename))
            table.setItem(ti, 2, _cell(artist))
            table.setItem(ti, 3, _cell(album))
            table.setItem(ti, 4, _cell(dur_s))

        table.doubleClicked.connect(lambda idx: self.track_play_requested.emit(
            g.tracks[idx.row()].filepath) if g.tracks else None)
        cv.addWidget(table)
        self._layout.addWidget(card)

    def _build_artists(self, g: GenreGroup):
        card = _SectionCard("genreArtists")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 14, 18, 14)
        cv.setSpacing(8)

        hdr = QLabel("Artistas")
        hdr.setStyleSheet(f"color: {_TEXT}; font-size: 15px; font-weight: 700;")
        cv.addWidget(hdr)

        artists = sorted(g.artists)[:20]
        for a in artists:
            row = QHBoxLayout()
            row.setSpacing(8)
            icon = QLabel()
            icon.setFixedSize(24, 24)
            icon.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 8px;")
            icon.setAlignment(Qt.AlignCenter)
            al = QLabel(a)
            al.setStyleSheet(f"color: {_TEXT2}; font-size: 13px; font-weight: 600;")
            row.addWidget(icon)
            row.addWidget(al)
            row.addStretch()
            cv.addLayout(row)

        if len(g.artists) > 20:
            more = QLabel(f"+{len(g.artists) - 20} más")
            more.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
            cv.addWidget(more)

        self._layout.addWidget(card)

    def _build_info(self, g: GenreGroup):
        card = _SectionCard("genreInfo")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 14, 18, 14)
        cv.setSpacing(4)

        hdr = QLabel("Información")
        hdr.setStyleSheet(f"color: {_TEXT}; font-size: 15px; font-weight: 700;")
        cv.addWidget(hdr)

        rows = [
            ("Familia", g.family),
            ("Canciones", str(g.track_count)),
            ("Artistas", str(g.artist_count)),
            ("Álbumes", str(g.album_count)),
            ("Duración total", _format_dur(g.total_duration) or "—"),
            ("Calidad", g.quality_summary or "—"),
            ("Lossless", str(g.lossless_count)),
            ("Hi-Res", str(g.hi_res_count)),
        ]
        if g.year_min:
            rows.append(("Años", f"{g.year_min} – {g.year_max}"))
        if g.dominant_decade:
            rows.append(("Década dominante", g.dominant_decade))
        if g.avg_bpm:
            rows.append(("BPM promedio", str(int(g.avg_bpm))))

        grid = QGridLayout()
        grid.setSpacing(3)
        for ri, (label, val) in enumerate(rows):
            kl = QLabel(label)
            kl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
            vl = QLabel(val)
            vl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; font-weight: 600;")
            grid.addWidget(kl, ri, 0, Qt.AlignTop)
            grid.addWidget(vl, ri, 1, Qt.AlignTop)
        cv.addLayout(grid)
        self._layout.addWidget(card)


def _cell(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    return item


class _SectionCard(QFrame):
    def __init__(self, name: str):
        super().__init__()
        self.setObjectName(name)
        self.setStyleSheet(f"""
            QFrame#{name} {{ background: rgba(255,255,255,0.035);
              border: 1px solid rgba(255,255,255,0.045); border-radius: 14px; }}
            QFrame#{name} QLabel {{ background: transparent; border: none; }}
        """)
