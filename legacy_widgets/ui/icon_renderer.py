"""Icon Renderer — SVG to QPixmap with proper scaling, centering, and alpha cleanup."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor
from PySide6.QtSvg import QSvgRenderer


def _clear_near_transparent_pixels(image: QImage, threshold: int = 2) -> None:
    """Clear RGB garbage only from nearly transparent pixels.

    Gentle cleanup — does not touch edge position or opaque black.
    Safe for action/view icons with tight viewBox.
    """
    if image.isNull():
        return
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.alpha() <= threshold:
                image.setPixelColor(x, y, QColor(0, 0, 0, 0))


def _clear_edge_artifacts(image: QImage) -> None:
    """Remove black borders and nearly-transparent pixels from SVG rendering."""
    if image.isNull():
        return
    w, h = image.width(), image.height()
    edge = max(2, min(w, h) // 8)
    for y in range(h):
        for x in range(w):
            c = image.pixelColor(x, y)
            is_edge = (x < edge or x >= w - edge or y < edge or y >= h - edge)
            is_pure_black = (c.red() == 0 and c.green() == 0 and c.blue() == 0
                             and c.alpha() == 255)
            if is_edge or is_pure_black or c.alpha() <= 30:
                image.setPixelColor(x, y, QColor(0, 0, 0, 0))


def render_svg_icon(path: str, size: int = 24, padding: int = 2) -> QPixmap:
    """Render an SVG with transparent alpha-safe supersampling."""
    scale_factor = 4
    canvas = max(1, size * scale_factor)
    pad = max(0, padding * scale_factor)

    image = QImage(canvas, canvas, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)

    if not path:
        return QPixmap.fromImage(image).scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return QPixmap.fromImage(image).scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    view = renderer.viewBoxF()
    target_size = max(1, canvas - pad * 2)

    if view.isEmpty() or view.width() <= 0 or view.height() <= 0:
        target_rect = QRectF(pad, pad, target_size, target_size)
    else:
        scale = min(target_size / view.width(), target_size / view.height())
        w = view.width() * scale
        h = view.height() * scale
        x = (canvas - w) / 2
        y = (canvas - h) / 2
        target_rect = QRectF(x, y, w, h)

    renderer.render(painter, target_rect)
    painter.end()

    # Pre-scale: gentle cleanup only (threshold=2, no edge clearing)
    _clear_near_transparent_pixels(image, threshold=2)

    final = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    final = final.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    # Post-scale: aggressive cleanup (edges, pure black, alpha<=30)
    _clear_edge_artifacts(final)

    return QPixmap.fromImage(final)
