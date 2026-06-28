"""Michi glass — acrylic brush with blur, noise, specular, and card shadow.

Provides the glassmorphism visual foundation for AcrylicGlassFrame cards.
"""

from __future__ import annotations

from PySide6.QtCore import QChildEvent, QEvent, QRectF, Qt
from PySide6.QtGui import (
    QColor, QImage, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap,
)
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QWidget


class AcrylicBrush:
    """Paints a translucent glass surface with tint, specular highlight, and border.

    Mimics acrylic/matte glass material used on macOS/Windows 11 acrylic cards.
    """

    def __init__(self, tint_opacity: float = 0.06,
                 specular_opacity: float = 24,
                 tint_color: QColor | None = None):
        self._tint_opacity = tint_opacity
        self._specular_opacity = specular_opacity
        self._tint_color = tint_color or QColor(255, 255, 255)

    def paint(self, widget: QWidget, painter: QPainter,
              clip_radius: int = 18):
        rect = QRectF(widget.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, clip_radius, clip_radius)
        painter.setClipPath(path)

        # Tinted translucent base
        tint = QColor(self._tint_color)
        tint.setAlphaF(self._tint_opacity)
        painter.fillRect(rect, tint)

        # Specular highlight (thin top edge)
        spec = QLinearGradient(0, 0, 0, rect.height() * 0.3)
        spec.setColorAt(0.0, QColor(255, 255, 255, max(0, min(255, int(self._specular_opacity)))))
        spec.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(rect, spec)

        # Outer border (brighter, defines the glass edge)
        border_outer = QPen(QColor(255, 255, 255, 20), 1.0)
        painter.setPen(border_outer)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                                clip_radius, clip_radius)

        # Inner border (subtle, gives glass depth)
        border_inner = QPen(QColor(255, 255, 255, 10), 0.5)
        painter.setPen(border_inner)
        painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5),
                                clip_radius - 1, clip_radius - 1)


class NoiseOverlay(QWidget):
    """Subtle noise/grain texture overlay for glass surfaces."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        if parent:
            self.setParent(parent)
        self.setObjectName("noiseOverlay")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._cached_noise: QPixmap | None = None
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent():
            if isinstance(event, QChildEvent):
                return super().eventFilter(obj, event)
            if event.type() == QEvent.Resize:
                self.setGeometry(obj.rect())
                self._generate_noise(obj.width(), obj.height())
        return super().eventFilter(obj, event)

    def _generate_noise(self, w: int, h: int):
        import random as _r
        _r.seed(42)
        img = QImage(w, h, QImage.Format_Grayscale8)
        for y in range(h):
            for x in range(w):
                v = _r.randint(0, 12)
                img.setPixel(x, y, v)
        self._cached_noise = QPixmap.fromImage(img)

    def paintEvent(self, event):
        if self._cached_noise is None:
            return
        painter = QPainter(self)
        painter.setOpacity(0.6)
        painter.drawPixmap(0, 0, self._cached_noise)
        painter.end()


def apply_card_shadow(widget: QWidget):
    """Apply a subtle drop shadow to a card widget."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(24)
    shadow.setXOffset(0)
    shadow.setYOffset(4)
    shadow.setColor(QColor(0, 0, 0, 60))
    widget.setGraphicsEffect(shadow)


class AcrylicGlassFrame(QFrame):
    """Glass surface with tint, noise, specular, shadow, and optional hover shine.

    Applies blur + tint + noise + specular automatically.
    Also adds NoiseOverlay, optional ShineOverlay, and card shadow.
    """

    def __init__(self, name: str, parent=None,
                 tint_opacity: float = 0.06,
                 specular_opacity: float = 24,
                 clip_radius: int = 18,
                 hover_shine: bool = False):
        super().__init__(parent)
        self.setObjectName(name)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._brush = AcrylicBrush(
            tint_opacity=tint_opacity,
            specular_opacity=specular_opacity,
        )
        self._clip_radius = clip_radius
        NoiseOverlay(self)
        if hover_shine:
            from ui.effects.michi_hover import ShineOverlay
            self._shine = ShineOverlay(self)
        from PySide6.QtGui import QColor as _QColor
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(24)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(4)
        self._shadow.setColor(_QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self._shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._brush.paint(self, painter, clip_radius=self._clip_radius)
        painter.end()
