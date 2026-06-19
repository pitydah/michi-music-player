"""Sidebar Icon Factory — QPainter-drawn icons, direct paint mode.

Two APIs:
- draw_sidebar_icon(painter, name, rect, color) → paints directly into rect.
- sidebar_pixmap(name, size, color) → returns QPixmap (for preview tools).
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath, QBrush


def draw_sidebar_icon(painter: QPainter, name: str, rect: QRectF, color: QColor):
    """Paint a sidebar icon directly into a rect using QPainter."""
    painter.save()

    painter.translate(rect.x(), rect.y())
    sx = rect.width() / 24.0
    sy = rect.height() / 24.0
    painter.scale(sx, sy)

    pen = QPen(color, 1.7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    brush = QBrush(color)
    key = (name or "").replace("sidebar_", "")

    if key in ("library", "songs"):
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(14, 6), QPointF(14, 15))
        painter.drawLine(QPointF(14, 6), QPointF(18, 7.3))
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(7.5, 14, 5.8, 4.6))

    elif key == "albums":
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(5.5, 5.5, 13, 13), 2.5, 2.5)
        painter.drawEllipse(QRectF(9.3, 9.3, 5.4, 5.4))
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(11.3, 11.3, 1.4, 1.4))

    elif key == "folders":
        painter.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(5.2, 8.4)
        path.lineTo(9.4, 8.4)
        path.lineTo(10.8, 10.1)
        path.lineTo(18.8, 10.1)
        path.lineTo(18.8, 17.8)
        path.lineTo(5.2, 17.8)
        path.closeSubpath()
        painter.drawPath(path)

    elif key in ("playlists", "playlist_item"):
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(8.5, 7.5), QPointF(18, 7.5))
        painter.drawLine(QPointF(8.5, 12), QPointF(18, 12))
        painter.drawLine(QPointF(8.5, 16.5), QPointF(15.8, 16.5))
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(5.2, 6.7, 1.8, 1.8))
        painter.drawEllipse(QRectF(5.2, 11.2, 1.8, 1.8))
        painter.drawEllipse(QRectF(5.2, 15.7, 1.8, 1.8))

    elif key == "radio":
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(10.2, 10.2, 3.6, 3.6))
        painter.drawArc(QRectF(7.2, 7.2, 9.6, 9.6), 35 * 16, 110 * 16)
        painter.drawArc(QRectF(5.2, 5.2, 13.6, 13.6), 35 * 16, 110 * 16)
        painter.drawArc(QRectF(7.2, 7.2, 9.6, 9.6), 215 * 16, 110 * 16)
        painter.drawArc(QRectF(5.2, 5.2, 13.6, 13.6), 215 * 16, 110 * 16)

    elif key == "servers":
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(5.6, 6.4, 12.8, 4.3), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(5.6, 13.3, 12.8, 4.3), 1.5, 1.5)
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(7.3, 7.7, 1.4, 1.4))
        painter.drawEllipse(QRectF(7.3, 14.6, 1.4, 1.4))

    elif key == "devices":
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(5.5, 6.2, 13, 9.6), 2.0, 2.0)
        painter.drawLine(QPointF(9, 18.3), QPointF(15, 18.3))
        painter.drawLine(QPointF(12, 15.8), QPointF(12, 18.3))

    elif key == "mix":
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(5.5, 5.5, 4.5, 4.5))
        painter.drawEllipse(QRectF(14, 5.5, 4.5, 4.5))
        painter.drawEllipse(QRectF(9.75, 14, 4.5, 4.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(9.2, 9), QPointF(11, 14))
        painter.drawLine(QPointF(15, 9), QPointF(13, 14))

    elif key == "unplayed":
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(5.8, 5.8, 12.4, 12.4))
        painter.drawLine(QPointF(12, 8.5), QPointF(12, 12))
        painter.drawLine(QPointF(12, 12), QPointF(15, 14))

    elif key == "popular":
        painter.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(12, 6.0)
        path.lineTo(13.6, 10.0)
        path.lineTo(17.8, 10.5)
        path.lineTo(14.7, 13.4)
        path.lineTo(15.6, 17.5)
        path.lineTo(12, 15.3)
        path.lineTo(8.4, 17.5)
        path.lineTo(9.3, 13.4)
        path.lineTo(6.2, 10.5)
        path.lineTo(10.4, 10.0)
        path.closeSubpath()
        painter.drawPath(path)

    elif key == "identifier":
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(6.2, 6.2, 7.8, 7.8))
        painter.drawLine(QPointF(13, 13), QPointF(18, 18))
        painter.drawLine(QPointF(8.3, 10.1), QPointF(11.9, 10.1))
        painter.drawLine(QPointF(10.1, 8.3), QPointF(10.1, 11.9))

    elif key == "add":
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(12, 6.8), QPointF(12, 17.2))
        painter.drawLine(QPointF(6.8, 12), QPointF(17.2, 12))

    elif key == "navidrome":
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(6, 6, 12, 12))
        painter.drawEllipse(QRectF(9, 9, 6, 6))
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(11.2, 11.2, 1.6, 1.6))

    elif key == "jellyfin":
        painter.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(12, 6.2)
        path.lineTo(17.8, 17.4)
        path.lineTo(6.2, 17.4)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setBrush(brush)
        painter.drawEllipse(QRectF(10.4, 12.4, 3.2, 3.2))

    else:
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(6.5, 6.5, 11, 11))

    painter.restore()


# ── Legacy pixmap API (for preview tools) ──

def sidebar_pixmap(name: str, size: int = 22, color: str = "#FFFFFF") -> QPixmap:
    """Return a QPixmap for preview tools. Uses draw_sidebar_icon internally."""
    render_size = 96
    pix = QPixmap(render_size, render_size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    draw_sidebar_icon(
        painter, name,
        QRectF(0, 0, render_size, render_size),
        QColor(color),
    )

    painter.end()
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
