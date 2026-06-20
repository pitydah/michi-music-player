"""Lyrics Widget — synced lyrics display with glassmorphism styling."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QFont, QColor, QLinearGradient, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

from lyrics.lrclib_client import LyricLine, LrcLibClient


class LyricsWidget(QWidget):
    lyrics_loaded = Signal(str)  # title

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client = LrcLibClient()
        self._lines: list[LyricLine] = []
        self._plain: str = ""
        self._position: float = 0.0
        self._active_idx: int = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("""
            font-size: 14px; font-weight: 600;
            color: rgba(245,245,247,0.6);
        """)
        layout.addWidget(self._title_label)

        layout.addSpacing(8)

        self._display = _LyricDisplay(self)
        layout.addWidget(self._display, stretch=1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar {
                height: 2px; border: none; border-radius: 1px;
                background: rgba(255,255,255,0.05);
            }
            QProgressBar::chunk {
                background: rgba(255,122,0,0.6); border-radius: 1px;
            }
        """)
        layout.addWidget(self._progress)

    def load_lyrics(self, title: str, artist: str = "",
                    album: str = "", duration: float = 0.0):
        self._lines.clear()
        self._plain = ""
        self._active_idx = -1
        self._title_label.setText(title or "Sin título")
        self._display.set_lines([])
        self._progress.setVisible(True)

        result = self._client.get_lyrics(title, artist, album, duration)
        if result:
            self._lines = result.lines
            self._plain = result.plain
            self._display.set_lines(self._lines)
            self.lyrics_loaded.emit(title)
        else:
            self._display.set_no_lyrics()

        self._progress.setVisible(False)

    def set_position(self, seconds: float):
        self._position = seconds

        if not self._lines:
            return

        new_idx = -1
        for i, line in enumerate(self._lines):
            if line.timestamp <= seconds:
                new_idx = i
            else:
                break

        if new_idx != self._active_idx:
            self._active_idx = new_idx
            self._display.set_active_idx(new_idx)

    def set_duration(self, seconds: float):
        pass  # reserved for future progress bar

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._display.update()


class _LyricDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lines: list[LyricLine] = []
        self._active_idx: int = -1
        self._no_lyrics: bool = False
        self.setMinimumHeight(120)

    def set_lines(self, lines: list[LyricLine]):
        self._lines = lines
        self._active_idx = -1
        self._no_lyrics = False
        self.update()

    def set_active_idx(self, idx: int):
        self._active_idx = idx
        self.update()

    def set_no_lyrics(self):
        self._lines.clear()
        self._active_idx = -1
        self._no_lyrics = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        if self._no_lyrics:
            painter.setPen(QColor(245, 245, 247, 60))
            font = QFont("Helvetica", 14)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter,
                             "Sin letras disponibles")
            painter.end()
            return

        if not self._lines:
            painter.end()
            return

        # Center the active line vertically
        line_height = 42
        center_y = h // 2
        start_y = center_y - self._active_idx * line_height

        font = QFont("Helvetica", 13)
        active_font = QFont("Helvetica", 16)

        for i, line in enumerate(self._lines):
            y = start_y + i * line_height

            # Skip lines outside viewport
            if y < -line_height or y > h + line_height:
                continue

            if i == self._active_idx:
                # Active line — brighter, larger, with gradient
                painter.setFont(active_font)
                rect = self.rect()
                rect.setTop(y - 4)
                rect.setBottom(y + line_height - 4)
                gradient = QLinearGradient(
                    rect.topLeft(), rect.bottomLeft())
                gradient.setColorAt(0.0, QColor(255, 255, 255, 230))
                gradient.setColorAt(1.0, QColor(255, 255, 255, 230))
                painter.setPen(QPen(gradient, 0))
            else:
                # Distance-based opacity
                dist = abs(i - self._active_idx)
                alpha = max(30, 180 - dist * 40)
                painter.setFont(font)
                painter.setPen(QColor(245, 245, 247, alpha))

            painter.drawText(
                0, int(y), w, line_height,
                Qt.AlignHCenter | Qt.AlignVCenter,
                line.text,
            )

        painter.end()
