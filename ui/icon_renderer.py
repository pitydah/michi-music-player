"""Icon Renderer — SVG to QPixmap with proper scaling, centering, and padding."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_svg_icon(path: str, size: int = 24, padding: int = 2) -> QPixmap:
    """Render an SVG to pixmap at 2x then scale down — kills alpha premult halos."""
    double = size * 2
    pixmap = QPixmap(double, double)
    pixmap.fill(Qt.transparent)

    if not path:
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    pad2 = padding * 2
    target = max(1, double - pad2 * 2)
    view = renderer.viewBoxF()

    if view.isEmpty() or view.width() <= 0 or view.height() <= 0:
        renderer.render(painter, QRectF(pad2, pad2, target, target))
    else:
        scale = min(target / view.width(), target / view.height())
        w = view.width() * scale
        h = view.height() * scale
        x = (double - w) / 2
        y = (double - h) / 2
        renderer.render(painter, QRectF(x, y, w, h))

    painter.end()
    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
