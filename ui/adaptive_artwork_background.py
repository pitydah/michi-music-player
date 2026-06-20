"""Adaptive Artwork Background — blurred album art with dark overlay."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient
from PySide6.QtWidgets import QWidget


class AdaptiveArtworkBackground(QWidget):
    """Paints a blurred, darkened version of the album art as background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._blur_radius = 40
        self._dim_strength = 0.65
        self._cache_key: str = ""

    def set_pixmap(self, pixmap: QPixmap):
        key = str(id(pixmap)) if pixmap else ""
        if key == self._cache_key:
            return
        self._cache_key = key
        if pixmap is None or pixmap.isNull():
            self._pixmap = None
        else:
            # Scale to a reasonable size for blur
            w = min(pixmap.width(), 400)
            h = min(pixmap.height(), 400)
            self._pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation)
        self.update()

    def clear(self):
        self._pixmap = None
        self._cache_key = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        if self._pixmap and not self._pixmap.isNull():
            # Draw scaled to fill
            scaled = self._pixmap.scaled(
                rect.size(), Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)

        # Dim overlay
        dim = QColor(0, 0, 0, int(255 * self._dim_strength))
        painter.fillRect(rect, dim)

        # Gradient overlay (bottom to top)
        grad = QLinearGradient(0, rect.height(), 0, 0)
        grad.setColorAt(0, QColor(0, 0, 0, 200))
        grad.setColorAt(0.5, QColor(0, 0, 0, 80))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(rect, grad)

        painter.end()
