"""Michi glass — acrylic brush with noise, specular, and card shadow.

Provides the glassmorphism visual foundation for AcrylicGlassFrame cards
and utility functions for shadows and glass surfaces.
"""

from __future__ import annotations

import contextlib
import random as _r
from typing import TYPE_CHECKING

from PySide6.QtCore import QChildEvent, QEvent, QRectF, Qt
from PySide6.QtGui import (
    QColor, QImage, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap,
)
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QWidget

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget as QWidgetType

_NOISE_TILE_SIZE = 96
_NOISE_TILE_CACHE: QPixmap | None = None
_NOISE_SEED = 42


def _noise_tile() -> QPixmap:
    global _NOISE_TILE_CACHE
    if _NOISE_TILE_CACHE is not None:
        return _NOISE_TILE_CACHE
    _r.seed(_NOISE_SEED)
    img = QImage(_NOISE_TILE_SIZE, _NOISE_TILE_SIZE, QImage.Format_Grayscale8)
    for y in range(_NOISE_TILE_SIZE):
        for x in range(_NOISE_TILE_SIZE):
            img.setPixel(x, y, _r.randint(0, 12))
    _NOISE_TILE_CACHE = QPixmap.fromImage(img)
    return _NOISE_TILE_CACHE


class AcrylicBrush:
    """Paints a translucent glass surface with tint, specular highlight, and border."""

    def __init__(self, tint_opacity: float = 0.06,
                 specular_opacity: float = 24,
                 tint_color: QColor | None = None):
        self._tint_opacity = tint_opacity
        self._specular_opacity = specular_opacity
        self._tint_color = tint_color or QColor(255, 255, 255)

    def paint(self, widget: QWidgetType, painter: QPainter,
              clip_radius: int = 18):
        rect = QRectF(widget.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, clip_radius, clip_radius)
        painter.setClipPath(path)

        tint = QColor(self._tint_color)
        tint.setAlphaF(self._tint_opacity)
        painter.fillRect(rect, tint)

        spec = QLinearGradient(0, 0, 0, rect.height() * 0.3)
        spec.setColorAt(0.0, QColor(255, 255, 255, max(0, min(255, int(self._specular_opacity)))))
        spec.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(rect, spec)

        border_outer = QPen(QColor(255, 255, 255, 20), 1.0)
        painter.setPen(border_outer)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                                clip_radius, clip_radius)

        border_inner = QPen(QColor(255, 255, 255, 10), 0.5)
        painter.setPen(border_inner)
        painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5),
                                clip_radius - 1, clip_radius - 1)


class NoiseOverlay(QWidget):
    """Subtle noise/grain texture overlay for glass surfaces."""

    def __init__(self, parent: QWidgetType | None = None):
        super().__init__(parent)
        self.setObjectName("noiseOverlay")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent():
            if isinstance(event, QChildEvent):
                return super().eventFilter(obj, event)
            if event.type() == QEvent.Resize:
                self.setGeometry(obj.rect())
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.6)
        painter.drawTiledPixmap(self.rect(), _noise_tile())
        painter.end()


def _shadow(blur: int = 18, offset: int = 4, opacity: int = 50) -> QGraphicsDropShadowEffect:
    e = QGraphicsDropShadowEffect()
    e.setBlurRadius(blur)
    e.setXOffset(0)
    e.setYOffset(offset)
    e.setColor(QColor(0, 0, 0, opacity))
    return e


def apply_soft_shadow(widget: QWidgetType):
    widget.setGraphicsEffect(_shadow(blur=14, offset=3, opacity=40))


def apply_card_shadow(widget: QWidgetType):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(24)
    shadow.setXOffset(0)
    shadow.setYOffset(4)
    shadow.setColor(QColor(0, 0, 0, 60))
    widget.setGraphicsEffect(shadow)


def apply_floating_shadow(widget: QWidgetType):
    widget.setGraphicsEffect(_shadow(blur=24, offset=5, opacity=60))


def apply_dialog_shadow(widget: QWidgetType):
    widget.setGraphicsEffect(_shadow(blur=40, offset=10, opacity=85))


def apply_sidebar_shadow(widget: QWidgetType):
    e = QGraphicsDropShadowEffect()
    e.setBlurRadius(18)
    e.setXOffset(3)
    e.setYOffset(0)
    e.setColor(QColor(0, 0, 0, 40))
    widget.setGraphicsEffect(e)


def clear_graphics_effect_safely(widget: QWidgetType):
    with contextlib.suppress(RuntimeError):
        widget.setGraphicsEffect(None)


class AcrylicGlassFrame(QFrame):
    """Glass surface with tint, noise, specular, shadow, and optional hover shine.

    Supports legacy callers: AcrylicGlassFrame(name, parent, tint_opacity=..., ...)
    and new callers: AcrylicGlassFrame(parent, brush, clip_radius=...)
    """

    def __init__(self, name_or_parent: str | QWidget | None = None,
                 parent_or_brush: QWidget | AcrylicBrush | None = None,
                 tint_opacity: float = 0.06,
                 specular_opacity: float = 24,
                 clip_radius: int = 18,
                 hover_shine: bool = False):
        name = ""
        parent: QWidget | None = None
        brush: AcrylicBrush | None = None

        if isinstance(name_or_parent, str):
            name = name_or_parent
            parent = parent_or_brush if isinstance(parent_or_brush, QWidget) else None
        else:
            parent = name_or_parent
            brush = parent_or_brush if isinstance(parent_or_brush, AcrylicBrush) else None

        super().__init__(parent)
        self.setObjectName(name)
        self._clip_radius = clip_radius
        self._brush = brush or AcrylicBrush(
            tint_opacity=tint_opacity,
            specular_opacity=specular_opacity,
        )
        self._noise = NoiseOverlay(self)
        self.setAttribute(Qt.WA_StyledBackground, True)
        apply_card_shadow(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self._brush.paint(self, painter, self._clip_radius)
        painter.end()
