"""Icon Renderer — SVG to QPixmap with proper scaling, centering, and padding."""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_svg_icon(path: str, size: int = 20) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    if not path:
        return pixmap

    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return pixmap

    view = renderer.viewBoxF()

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    padding = max(1, int(size * 0.10))
    target = size - padding * 2

    if view.isEmpty() or view.width() <= 0 or view.height() <= 0:
        renderer.render(painter, QRectF(padding, padding, target, target))
        painter.end()
        return pixmap

    scale = min(target / view.width(), target / view.height())
    w = view.width() * scale
    h = view.height() * scale
    x = (size - w) / 2
    y = (size - h) / 2

    renderer.render(painter, QRectF(x, y, w, h))
    painter.end()

    return pixmap
