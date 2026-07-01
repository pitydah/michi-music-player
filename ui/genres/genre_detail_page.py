"""GenreDetailPage — full detail view for a single genre with tabs."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget,
)

from metadata.genre_taxonomy import get_mood_hints

_BG = "#090B11"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class GenreDetailPage(QWidget):
    back_requested = Signal()
    play_requested = Signal(str)
    shuffle_requested = Signal(str)
    queue_requested = Signal(str)
    mix_requested = Signal(str)
    radio_requested = Signal(str)
    playlist_requested = Signal(str)
    cleanup_requested = Signal(str)
    track_play_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._genre_data = None
        self._tracks = []

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

    def set_genre(self, genre_data: dict, tracks: list = None):
        self._genre_data = genre_data
        self._tracks = tracks or []
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        g = self._genre_data
        if not g:
            return

        self._build_hero(g)
        self._build_actions(g)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ background: transparent; border: none; }}"
            f"QTabBar::tab {{ background: rgba(255,255,255,0.03); color: {_TEXT3}; "
            f"border: none; padding: 8px 16px; margin-right: 2px; "
            f"border-top-left-radius: 8px; border-top-right-radius: 8px; }}"
            f"QTabBar::tab:selected {{ background: rgba(143,183,255,0.10); color: {_TEXT}; }}"
            f"QTabBar::tab:hover {{ background: rgba(255,255,255,0.06); }}")

        if self._tracks:
            tracks_tab = self._build_tracks_widget(g)
            tabs.addTab(tracks_tab, "Canciones")

        info_tab = self._build_info_widget(g)
        tabs.addTab(info_tab, "Estadísticas")

        self._layout.addWidget(tabs)
        self._layout.addStretch()

    def _build_hero(self, g: dict):
        card = QFrame()
        card.setObjectName("genreDetailHero")
        card.setStyleSheet(
            "QFrame#genreDetailHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(255,255,255,0.04),stop:1 rgba(143,183,255,0.06));"
            "border: 1px solid rgba(143,183,255,0.08); border-radius: 18px; }"
            "QLabel { background: transparent; border: none; }")

        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(16)

        info = QVBoxLayout()
        info.setSpacing(4)

        name = QLabel(g.get("genre", "—"))
        name.setStyleSheet(f"color: {_TEXT}; font-size: 24px; font-weight: 700;")
        info.addWidget(name)

        stats_parts = [
            f"{g.get('track_count', 0)} canciones",
            f"{g.get('artist_count', 0)} artistas",
            f"{g.get('album_count', 0)} álbumes",
        ]
        dur = _format_dur(g.get("duration_total", 0))
        if dur:
            stats_parts.append(dur)
        s_lbl = QLabel(" · ".join(stats_parts))
        s_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        info.addWidget(s_lbl)

        quality = g.get("dominant_quality", "") or g.get("dominant_format", "")
        if quality:
            q_lbl = QLabel(f"Predomina: {quality}")
            q_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 11px;")
            info.addWidget(q_lbl)

        top.addLayout(info, 1)
        cl.addLayout(top)

        hints = get_mood_hints(g.get("genre", ""))
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

    def _build_actions(self, g: dict):
        row = QHBoxLayout()
        row.setSpacing(8)
        key = g.get("genre", "")
        for label, slot in [
            ("▶ Reproducir todo", lambda: self.play_requested.emit(key)),
            ("🔀 Aleatorio", lambda: self.shuffle_requested.emit(key)),
            ("+ Cola", lambda: self.queue_requested.emit(key)),
            ("🎵 Mix", lambda: self.mix_requested.emit(key)),
            ("📻 Radio", lambda: self.radio_requested.emit(key)),
            ("♫ Playlist", lambda: self.playlist_requested.emit(key)),
            ("🧹 Limpiar", lambda: self.cleanup_requested.emit(key)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.78);"
                "border: 1px solid rgba(255,255,255,0.04); border-radius: 10px;"
                "padding: 7px 12px; font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: rgba(255,255,255,0.08); }")
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch()
        self._layout.addLayout(row)

    def _build_tracks_widget(self, g: dict) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        n = len(self._tracks)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Nº", "Título", "Artista", "Álbum", "Dur."])
        table.setRowCount(n)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setMinimumHeight(200)
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

        for ti, t in enumerate(self._tracks):
            tn = getattr(t, "track_number", 0) or 0
            dur_v = getattr(t, "duration", 0) or 0
            dur_s = f"{int(dur_v // 60)}:{int(dur_v % 60):02d}" if dur_v else ""
            artist = getattr(t, "artist", "") or "—"
            album = getattr(t, "album", "") or "—"
            table.setItem(ti, 0, self._cell(str(tn) if tn else "—"))
            table.setItem(ti, 1, self._cell(t.title or t.filename))
            table.setItem(ti, 2, self._cell(artist))
            table.setItem(ti, 3, self._cell(album))
            table.setItem(ti, 4, self._cell(dur_s))

        table.doubleClicked.connect(
            lambda idx: self.track_play_requested.emit(
                self._tracks[idx.row()].filepath) if self._tracks else None)
        v.addWidget(table)
        return w

    def _build_info_widget(self, g: dict) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        rows = [
            ("Canciones", str(g.get("track_count", 0))),
            ("Artistas", str(g.get("artist_count", 0))),
            ("Álbumes", str(g.get("album_count", 0))),
            ("Duración total", _format_dur(g.get("duration_total", 0)) or "—"),
            ("Formato", g.get("dominant_format", "—")),
            ("Calidad", g.get("dominant_quality", "—")),
            ("Lossless", str(g.get("lossless_count", 0))),
            ("Lossy", str(g.get("lossy_count", 0))),
            ("Hi-Res", str(g.get("hires_count", 0))),
            ("Sin metadata", str(g.get("missing_metadata_count", 0))),
        ]

        grid = QGridLayout()
        grid.setSpacing(3)
        for ri, (label, val) in enumerate(rows):
            kl = QLabel(label)
            kl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
            vl = QLabel(val)
            vl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; font-weight: 600;")
            grid.addWidget(kl, ri, 0, Qt.AlignTop)
            grid.addWidget(vl, ri, 1, Qt.AlignTop)
        v.addLayout(grid)
        v.addStretch()
        return w

    @staticmethod
    def _cell(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item
