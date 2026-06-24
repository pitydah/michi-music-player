"""Playlist Detail View — premium banner + track list for individual playlists."""
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QScrollArea,
)

from ui.services.playlist_cover_service import get_playlist_cover

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
        background: rgba(255,255,255,0.065);
        color: {_TEXT};
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 8px 16px;
        font-size: 12.5px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.095);
        border: 1px solid rgba(255,255,255,0.15);
    }}
"""


class PlaylistDetailView(QWidget):
    play_requested = Signal(int)
    queue_requested = Signal(int)
    edit_requested = Signal(int)
    export_requested = Signal(int)
    track_double_clicked = Signal(str)
    track_activated = Signal(int, str)  # row index, filepath

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._playlist: dict | None = None
        self._tracks: list = []

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {_BG}; border: none; }}
            QScrollBar:vertical {{ background: rgba(255,255,255,0.02); width: 10px;
              margin: 4px; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.16);
              min-height: 44px; border-radius: 5px; }}
            QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.28); }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(28, 20, 28, 32)
        self._layout.setSpacing(20)

        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def set_playlist(self, playlist: dict, tracks: list):
        sig = (playlist.get("id"), playlist.get("name"), playlist.get("cover_path"),
               len(tracks), sum(getattr(t, 'duration', 0) or 0 for t in tracks))
        if sig == getattr(self, '_last_detail_sig', None):
            return
        self._last_detail_sig = sig
        self._playlist = playlist
        self._tracks = tracks
        self._rebuild()

    def _clear_layout(self, layout):
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

        if not self._playlist:
            return

        self._build_banner()
        self._build_actions()
        self._build_tracklist()
        self._layout.addStretch()

    def _build_banner(self):
        pl = self._playlist
        tracks = self._tracks

        banner = QHBoxLayout()
        banner.setSpacing(22)

        # Cover — 170px
        cover = get_playlist_cover(pl, tracks)
        cover_lbl = QLabel()
        cover_lbl.setFixedSize(170, 170)
        if cover and not cover.isNull():
            cover_lbl.setPixmap(cover.scaled(170, 170, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        cover_lbl.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.04); border-radius: 16px; }")
        banner.addWidget(cover_lbl)

        # Info
        info = QVBoxLayout()
        info.setSpacing(6)

        name = pl.get("name", "Sin nombre")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 26px; font-weight: 800; background: transparent;")
        name_lbl.setWordWrap(True)
        info.addWidget(name_lbl)

        desc = pl.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color: {_TEXT2}; font-size: 13px; background: transparent;")
            info.addWidget(desc_lbl)

        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = ""
        if dur:
            s = int(dur)
            dur_str = f"{s // 3600} h {(s % 3600) // 60} min" if s >= 3600 else f"{s // 60} min"

        meta = f"{count} canciones"
        if dur_str:
            meta += f" · {dur_str}"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(
            f"color: {_TEXT3}; font-size: 13px; background: transparent;")
        info.addWidget(meta_lbl)

        info.addStretch()
        banner.addLayout(info)
        banner.addStretch()

        self._layout.addLayout(banner)

    def _build_actions(self):
        pid = self._playlist.get("id", 0)
        row = QHBoxLayout()
        row.setSpacing(10)

        for label, sig in [
            ("Reproducir", lambda: self.play_requested.emit(pid)),
            ("Añadir a cola", lambda: self.queue_requested.emit(pid)),
            ("Editar", lambda: self.edit_requested.emit(pid)),
            ("Exportar", lambda: self.export_requested.emit(pid)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_CSS)
            btn.clicked.connect(sig)
            row.addWidget(btn)

        row.addStretch()
        self._layout.addLayout(row)

    def _build_tracklist(self):
        tracks = self._tracks
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["#", "Título", "Artista", "Duración"])
        table.setRowCount(len(tracks))
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)

        table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent; color: {_TEXT}; border: none;
                gridline-color: transparent;
                selection-background-color: {_SELECTED}; selection-color: {_TEXT};
                alternate-background-color: rgba(255,255,255,0.015);
            }}
            QTableWidget::item {{ padding: 6px; color: {_TEXT2}; font-size: 12px; }}
            QTableWidget::item:hover {{ background: {_HOVER}; }}
            QHeaderView::section {{
                background: rgba(255,255,255,0.030); color: {_TEXT3};
                border: none; border-bottom: 1px solid rgba(255,255,255,0.02);
                padding: 8px 10px; font-size: 11px; font-weight: 600;
            }}
        """)

        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 40)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(2, 180)
        table.setColumnWidth(3, 70)

        for i, t in enumerate(tracks):
            fp = getattr(t, 'filepath', '')
            title = getattr(t, 'title', '') or (fp and os.path.basename(fp)) or "—"
            artist = getattr(t, 'artist', '') or "—"
            dur = getattr(t, 'duration', 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "—"

            table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            table.setItem(i, 1, QTableWidgetItem(title))
            table.setItem(i, 2, QTableWidgetItem(artist))
            table.setItem(i, 3, QTableWidgetItem(dur_s))

        table.itemDoubleClicked.connect(
            lambda item: (self.track_double_clicked.emit(
                getattr(tracks[item.row()], 'filepath', '')),
                self.track_activated.emit(
                item.row(), getattr(tracks[item.row()], 'filepath', ''))))

        self._layout.addWidget(table)
