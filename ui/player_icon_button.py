"""PlayerIconButton — QPushButton that paints icons with QPainter, no SVG/QIcon."""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QBrush
from PySide6.QtWidgets import QPushButton


def draw_player_icon(painter: QPainter, name: str, rect: QRectF, color: QColor):
    """Draw a player control icon directly into a rect."""
    painter.save()
    painter.translate(rect.x(), rect.y())
    sx = rect.width() / 24.0
    sy = rect.height() / 24.0
    painter.scale(sx, sy)

    pen = QPen(color, 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    brush = QBrush(color)

    key = name.replace("warm_", "")

    if key in ("play",):
        # Solid right-pointing triangle
        path = QPainterPath()
        path.moveTo(7, 4)
        path.lineTo(20, 12)
        path.lineTo(7, 20)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)

    elif key in ("pause",):
        painter.setBrush(brush)
        painter.drawRoundedRect(QRectF(6, 5, 4, 14), 1, 1)
        painter.drawRoundedRect(QRectF(14, 5, 4, 14), 1, 1)

    elif key in ("prev",):
        path = QPainterPath()
        path.moveTo(17, 4)
        path.lineTo(6, 12)
        path.lineTo(17, 20)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        painter.setBrush(brush)
        painter.drawRoundedRect(QRectF(17, 5, 2.5, 14), 1, 1)

    elif key in ("next",):
        path = QPainterPath()
        path.moveTo(7, 4)
        path.lineTo(18, 12)
        path.lineTo(7, 20)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        painter.setBrush(brush)
        painter.drawRoundedRect(QRectF(4.5, 5, 2.5, 14), 1, 1)

    elif key in ("shuffle",):
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(4, 7), QPointF(17, 7))
        painter.drawLine(QPointF(4, 17), QPointF(17, 17))
        # Top arrow
        path1 = QPainterPath()
        path1.moveTo(14, 5)
        path1.lineTo(20, 7)
        path1.lineTo(20, 3)
        path1.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path1)
        # Bottom arrow pointing right
        path2 = QPainterPath()
        path2.moveTo(20, 15)
        path2.lineTo(20, 19)
        path2.lineTo(14, 17)
        path2.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path2)

    elif key in ("repeat",):
        painter.setBrush(Qt.NoBrush)
        # Arc loop
        painter.drawArc(QRectF(6, 5, 12, 8), 0, 180 * 16)
        painter.drawArc(QRectF(6, 11, 12, 8), 0, -180 * 16)
        # Arrow tips
        path1 = QPainterPath()
        path1.moveTo(17.5, 5.5)
        path1.lineTo(19, 8.5)
        path1.lineTo(18, 5.5)
        path1.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path1)
        path2 = QPainterPath()
        path2.moveTo(7.5, 18.5)
        path2.lineTo(6, 15.5)
        path2.lineTo(5, 18.5)
        path2.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path2)

    elif key in ("eq",):
        painter.setBrush(Qt.NoBrush)
        for i, (h, x) in enumerate([(12, 5), (16, 10), (10, 15)]):
            painter.drawLine(QPointF(x, 20 - h), QPointF(x, 20))
            painter.setBrush(brush)
            painter.drawEllipse(QRectF(x - 1.8, 19 - h - 1.8, 3.6, 3.6))
            painter.setBrush(Qt.NoBrush)

    elif key in ("transmit",):
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(6, 3, 12, 8), 2, 2)
        painter.drawLine(QPointF(9, 13), QPointF(15, 13))
        painter.drawLine(QPointF(12, 11), QPointF(12, 13))
        # Wi-Fi arcs
        painter.drawArc(QRectF(5, 15, 14, 8), 220 * 16, 100 * 16)
        painter.drawArc(QRectF(8, 17, 8, 6), 220 * 16, 100 * 16)

    elif key in ("vol_high",):
        painter.setBrush(Qt.NoBrush)
        # Speaker
        path = QPainterPath()
        path.moveTo(6, 9)
        path.lineTo(8, 9)
        path.lineTo(11, 7)
        path.lineTo(11, 17)
        path.lineTo(8, 15)
        path.lineTo(6, 15)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(QRectF(13, 6, 8, 12), 300 * 16, 120 * 16)
        painter.drawArc(QRectF(16, 4, 8, 16), 300 * 16, 120 * 16)

    elif key in ("vol_medium",):
        # Speaker + 1 wave
        path = QPainterPath()
        path.moveTo(6, 9)
        path.lineTo(8, 9)
        path.lineTo(11, 7)
        path.lineTo(11, 17)
        path.lineTo(8, 15)
        path.lineTo(6, 15)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(QRectF(13, 6, 8, 12), 300 * 16, 120 * 16)

    elif key in ("vol_low",):
        # Speaker only
        path = QPainterPath()
        path.moveTo(6, 9)
        path.lineTo(8, 9)
        path.lineTo(11, 7)
        path.lineTo(11, 17)
        path.lineTo(8, 15)
        path.lineTo(6, 15)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)

    elif key in ("vol_mute", "mute"):
        # Speaker + X
        path = QPainterPath()
        path.moveTo(6, 9)
        path.lineTo(8, 9)
        path.lineTo(11, 7)
        path.lineTo(11, 17)
        path.lineTo(8, 15)
        path.lineTo(6, 15)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(14, 8), QPointF(21, 16))
        painter.drawLine(QPointF(14, 16), QPointF(21, 8))

    else:
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(5, 5, 14, 14))

    painter.restore()


class PlayerIconButton(QPushButton):
    """QPushButton with QPainter-drawn icon — no SVG, no QIcon."""

    def __init__(
        self,
        icon_name: str = "",
        button_size: int = 42,
        icon_size: int = 22,
        primary: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._icon_name = icon_name
        self._button_size = button_size
        self._icon_size = icon_size
        self._primary = primary
        self._hovered = False
        self._pressed = False
        self._active_state = False
        self.setFixedSize(button_size, button_size)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)

    def set_icon_name(self, name: str):
        self._icon_name = name
        self.update()

    def set_active(self, active: bool):
        self._active_state = active
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        if not self._icon_name:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()

        # Background
        if self._pressed:
            painter.setBrush(QColor(255, 77, 46, 56))
        elif self._hovered:
            painter.setBrush(QColor(255, 255, 255, 20))
        elif self._active_state:
            painter.setBrush(QColor(255, 77, 46, 46))
        else:
            painter.setBrush(Qt.NoBrush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, w, h), 11, 11)

        # Icon color
        if self._primary and not self._hovered and not self._pressed:
            color = QColor("#FF4D2E")
        elif self._active_state:
            color = QColor("#FF7A00")
        else:
            color = QColor("#FFFFFF")

        # Icon rect — centered
        offset = (self._button_size - self._icon_size) / 2
        rect = QRectF(offset, offset, self._icon_size, self._icon_size)

        draw_player_icon(painter, self._icon_name, rect, color)

        painter.end()
