"""Background theme service — adaptive background color extraction and animation."""
from PySide6.QtCore import Qt, QVariantAnimation
from PySide6.QtGui import QColor


class BackgroundThemeService:
    def __init__(self, content_stack):
        self._content = content_stack
        self._last_bg_color = QColor("#1a1a1e")
        self._bg_fade_anim = None

    def extract_colors(self, pixmap):
        img = pixmap.toImage().scaled(1, 1, Qt.IgnoreAspectRatio,
                                      Qt.SmoothTransformation)
        avg = img.pixelColor(0, 0)
        return avg.name(), avg.darker(150).name()

    def apply(self, pixmap):
        if pixmap is None or pixmap.isNull():
            self.reset()
            return
        c1, _ = self.extract_colors(pixmap)
        c1_color = QColor(c1)

        anim = QVariantAnimation()
        anim.setDuration(800)
        anim.setStartValue(self._last_bg_color)
        anim.setEndValue(c1_color)
        anim.valueChanged.connect(
            lambda v: self._content.setStyleSheet(
                f"QStackedWidget {{"
                f"  background: qlineargradient(y1:0, y2:1,"
                f" stop:0 {v.name()}, stop:1 {v.name()});"
                f"  border-radius: 12px;"
                f"}}"))
        anim.start()
        self._last_bg_color = c1_color
        self._bg_fade_anim = anim

    def reset(self):
        self._content.setStyleSheet(
            "QStackedWidget {"
            "  background: rgba(255,255,255,0.04);"
            "  border-radius: 12px;"
            "}")
