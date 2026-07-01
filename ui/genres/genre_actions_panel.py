"""GenreActionsPanel — quick action buttons for genre operations."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel

from ui.central.central_styles import glass_button_qss, card_title_qss

_TEXT3 = "rgba(255,255,255,0.62)"


class GenreActionsPanel(QFrame):
    play_requested = Signal(str)
    mix_requested = Signal(str)
    radio_requested = Signal(str)
    playlist_requested = Signal(str)
    queue_requested = Signal(str)
    cleanup_requested = Signal(str)

    def __init__(self, genre_key: str = "", parent=None):
        super().__init__(parent)
        self._genre_key = genre_key
        self.setObjectName("genreActionsPanel")
        self.setStyleSheet(
            "QFrame#genreActionsPanel { background: rgba(255,255,255,0.03);"
            "border: 1px solid rgba(255,255,255,0.045); border-radius: 14px; }"
            "QLabel { background: transparent; border: none; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)

        hdr = QLabel("Acciones")
        hdr.setStyleSheet(card_title_qss())
        v.addWidget(hdr)

        grid = QVBoxLayout()
        grid.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        for label, icon, slot in [
            ("▶ Reproducir", "primary", lambda: self.play_requested.emit(self._genre_key)),
            ("🎵 Mix", "accent", lambda: self.mix_requested.emit(self._genre_key)),
            ("📻 Radio", "accent", lambda: self.radio_requested.emit(self._genre_key)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss(icon))
            btn.clicked.connect(slot)
            row1.addWidget(btn)
        grid.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        for label, icon, slot in [
            ("+ Cola", "ghost", lambda: self.queue_requested.emit(self._genre_key)),
            ("♫ Playlist", "ghost", lambda: self.playlist_requested.emit(self._genre_key)),
            ("🧹 Limpiar", "ghost", lambda: self.cleanup_requested.emit(self._genre_key)),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss(icon))
            btn.clicked.connect(slot)
            row2.addWidget(btn)
        grid.addLayout(row2)

        v.addLayout(grid)

    def set_genre_key(self, key: str):
        self._genre_key = key
