"""Album Detail View — full-screen album banner + track list."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QAbstractItemView,
)

from ui.central.central_styles import (
    glass_button_qss, table_qss, table_header_qss,
    card_desc_qss, transparent_scrollbar_qss,
)
from ui.effects.michi_glass import AcrylicBrush


class AlbumDetailView(QWidget):
    back_requested = Signal()
    track_play_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("albumDetailView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(transparent_scrollbar_qss())

        content = QWidget()
        content.setObjectName("albumDetailContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(32, 16, 32, 40)
        cl.setSpacing(24)

        back_btn = QPushButton("← Volver a álbumes")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(glass_button_qss("ghost"))
        back_btn.clicked.connect(self.back_requested.emit)
        cl.addWidget(back_btn)

        self._banner = _AlbumBanner()
        cl.addWidget(self._banner)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["#", "Canción", "Duración"])
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 50)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setColumnWidth(2, 80)
        self._table.setStyleSheet(table_qss() + table_header_qss())
        self._table.setMinimumHeight(120)
        self._table.doubleClicked.connect(self._on_track_dbl)
        cl.addWidget(self._table, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def set_album(self, title, artist, year="",
                  cover_pixmap=None, tracks=None,
                  total_duration="", format_info=""):
        self._banner.set_album(title, artist, year, cover_pixmap,
                               total_duration, format_info)
        self._tracks = tracks or []
        self._populate_tracks()

    def _populate_tracks(self):
        self._table.setRowCount(len(self._tracks))
        for i, t in enumerate(self._tracks):
            tn = getattr(t, "track_number", 0) or i + 1
            title = getattr(t, "title", "") or getattr(t, "filename", "—")
            dur = getattr(t, "duration", 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "—"
            self._table.setItem(i, 0, QTableWidgetItem(str(tn)))
            self._table.setItem(i, 1, QTableWidgetItem(title))
            self._table.setItem(i, 2, QTableWidgetItem(dur_s))

    def _on_track_dbl(self, idx):
        t = self._tracks[idx.row()] if idx.isValid() and hasattr(self, '_tracks') else None
        if t:
            fp = getattr(t, "filepath", "")
            if fp:
                self.track_play_requested.emit(fp)


class _AlbumBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("albumBanner")
        self._brush = AcrylicBrush(tint_opacity=0.10, specular_opacity=22)
        self.setAttribute(Qt.WA_StyledBackground, False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        self._cover = QLabel()
        self._cover.setFixedSize(200, 200)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.04); border-radius: 14px; }")
        layout.addWidget(self._cover)

        info = QVBoxLayout()
        info.setSpacing(6)

        self._title = QLabel("")
        self._title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.95);"
            "background: transparent;")
        self._title.setWordWrap(True)
        info.addWidget(self._title)

        self._artist = QLabel("")
        self._artist.setStyleSheet(card_desc_qss())
        info.addWidget(self._artist)

        self._meta = QLabel("")
        self._meta.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; background: transparent;")
        info.addWidget(self._meta)

        self._format = QLabel("")
        self._format.setStyleSheet(
            "color: rgba(143,183,255,0.60); font-size: 11px; background: transparent;")
        info.addWidget(self._format)

        info.addStretch()
        layout.addLayout(info, 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._brush.paint(self, painter, clip_radius=18)
        painter.end()

    def set_album(self, title, artist, year="", cover_pixmap=None,
                  total_duration="", format_info=""):
        self._title.setText(title)
        self._artist.setText(artist)
        meta_parts = [p for p in [year, total_duration] if p]
        self._meta.setText(" · ".join(meta_parts))
        self._format.setText(format_info)
        if cover_pixmap and not cover_pixmap.isNull():
            self._cover.setPixmap(
                cover_pixmap.scaled(196, 196, Qt.KeepAspectRatio,
                                   Qt.SmoothTransformation))
