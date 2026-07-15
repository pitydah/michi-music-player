"""Background theme service — adaptive background color extraction and animation.
QML-compatible: uses PySide6 signals instead of QStackedWidget."""
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QColor


class BackgroundThemeService(QObject):
    backgroundChanged = Signal(str, str)  # primary_color, darker_color

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_bg_color = QColor("#090B11")
        self._bg_fade_anim = None

    def extract_colors(self, pixmap):
        if pixmap is None or pixmap.isNull():
            return "#090B11", "#06080D"
        img = pixmap.toImage().scaled(1, 1, Qt.IgnoreAspectRatio,
                                      Qt.SmoothTransformation)
        avg = img.pixelColor(0, 0)
        return avg.name(), avg.darker(150).name()

    def apply(self, pixmap):
        if pixmap is None or pixmap.isNull():
            self.reset()
            return
        c1, c2 = self.extract_colors(pixmap)
        self.backgroundChanged.emit(c1, c2)
        self._last_bg_color = QColor(c1)

    def reset(self):
        self.backgroundChanged.emit("#090B11", "#06080D")
