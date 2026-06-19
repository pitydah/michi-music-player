"""Album grid — 2D grid of album covers with titles."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGridLayout,
    QPushButton, QLabel, QSizePolicy,
)

from library.album_art import load_covers_for_albums
from library.library_db import MediaItem


class AlbumGridWidget(QWidget):
    album_double_clicked = Signal(list)  # list of filepaths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}")

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background:transparent;")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(12, 12, 12, 12)

        self._scroll.setWidget(self._grid_widget)
        layout.addWidget(self._scroll)

    def set_items(self, items: list[MediaItem], cover_size: int = 180):
        self._items = items
        # Clear grid
        while self._grid.count():
            w = self._grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        groups = load_covers_for_albums(items, cover_size)
        cols = max(1, self.width() // (cover_size + 32))

        for i, group in enumerate(groups):
            btn = QPushButton()
            btn.setIcon(QIcon(group.pixmap))
            btn.setIconSize(QSize(cover_size, cover_size))
            btn.setFixedSize(cover_size + 8, cover_size + 52)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border-radius: 8px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.06);
                }
            """)

            label = QLabel(
                f"{group.title}\n{group.subtitle}", btn)
            label.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            label.setStyleSheet(
                "color: rgba(245,245,247,0.7); font-size: 11px;"
                "background: transparent; padding: 0 4px 8px 4px;")
            label.setGeometry(0, cover_size, cover_size + 8, 48)
            label.setWordWrap(True)

            tracks = group.data.get("tracks", [])
            if tracks:
                fps = [t.filepath for t in tracks]
                btn.clicked.connect(
                    lambda checked=False, f=fps: self.album_double_clicked.emit(f))

            row = i // cols
            col = i % cols
            self._grid.addWidget(btn, row, col, Qt.AlignCenter)
