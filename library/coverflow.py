"""CoverFlow — QGraphicsView-based carousel with OpenGL, physics, reflections."""

import math
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation,
    Property, Signal, QRectF, QPointF,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QPixmap,
    QTransform, QFont,
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsObject,
    QGraphicsTextItem,
)

from library.album_art import CoverFlowItem

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    HAVE_OPENGL = True
except ImportError:
    HAVE_OPENGL = False


class CoverItem(QGraphicsObject):
    """Single album cover with reflection in the carousel."""

    def __init__(self, pixmap: QPixmap | None, index: int, width: int = 260,
                 height: int = 260):
        super().__init__()
        self._index = index
        self._w = width
        self._h = height
        self._fade_alpha = 1.0

        # Placeholder for async loading
        if pixmap is None or pixmap.isNull():
            self._placeholder = QPixmap(width, height)
            self._placeholder.fill(QColor(40, 40, 45))
            self._pixmap = self._placeholder
        else:
            self._placeholder = QPixmap()
            self._pixmap = pixmap.scaled(
                width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _generate_reflection(self) -> QPixmap:
        cached = QPixmap(self._w, self._h * 2)
        cached.fill(Qt.transparent)
        p = QPainter(cached)
        p.drawPixmap(0, 0, self._pixmap)
        p.save()
        p.translate(0, self._h * 2)
        p.scale(1, -1)
        p.setOpacity(0.3)
        p.drawPixmap(0, 0, self._pixmap)
        p.restore()
        grad = QLinearGradient(0, self._h, 0, self._h * 2)
        grad.setColorAt(0.0, QColor(0, 0, 0, 90))
        grad.setColorAt(0.3, QColor(0, 0, 0, 255))
        grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        p.fillRect(0, self._h, self._w, self._h, grad)
        p.end()
        return cached

    def set_real_cover(self, pixmap: QPixmap):
        """Animated fade from placeholder to real cover (anti-pop-in)."""
        if pixmap is None or pixmap.isNull():
            return
        self._real_cover = pixmap.scaled(
            self._w, self._h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._fade_alpha = 0.0
        anim = QVariantAnimation()
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(self._on_fade_step)
        anim.finished.connect(self._on_fade_done)
        anim.start()
        self._fade_anim = anim  # keep reference

    def _on_fade_step(self, value: float):
        self._fade_alpha = value
        self.update()

    def _on_fade_done(self):
        self._pixmap = self._real_cover
        self._fade_alpha = 1.0
        self._placeholder = QPixmap()
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(-self._w / 2, -self._h / 2, self._w, self._h * 2)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Draw cover + reflection
        painter.drawPixmap(0, 0, self._pixmap)

        # Reflection
        painter.save()
        painter.translate(0, self._h * 2)
        painter.scale(1, -1)
        painter.setOpacity(0.3)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.restore()

        # Fade gradient over reflection
        gradient = QLinearGradient(0, self._h, 0, self._h * 2)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 90))
        gradient.setColorAt(0.3, QColor(0, 0, 0, 255))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.fillRect(0, int(self._h), int(self._w), int(self._h), gradient)

        # Fade-in overlay: if real_cover is loading, crossfade
        if hasattr(self, '_real_cover') and self._fade_alpha < 1.0:
            painter.save()
            painter.setOpacity(self._fade_alpha)
            painter.drawPixmap(0, 0, self._real_cover)
            painter.translate(0, self._h * 2)
            painter.scale(1, -1)
            painter.setOpacity(0.3 * self._fade_alpha)
            painter.drawPixmap(0, 0, self._real_cover)
            painter.restore()

    def update_transform(self, current_offset: float, view_width: float,
                         view_height: float):
        dist = self._index - current_offset
        transform = QTransform()
        max_rot = 65.0
        spacing_center = 200.0
        spacing_side = 60.0

        if abs(dist) < 0.1:
            self.setZValue(1000)
            cx = view_width / 2
            cy = view_height / 2 - 20
            transform.translate(cx, cy)
            transform.scale(1.0, 1.0)
        else:
            is_left = dist < 0
            ad = abs(dist)
            self.setZValue(1000 - int(ad * 10))
            rot = max_rot if ad >= 1.0 else max_rot * ad
            if is_left:
                rot = -rot

            transform.translate(self._w / 2, self._h / 2)
            transform.rotate(rot, Qt.YAxis)
            transform.translate(-self._w / 2, -self._h / 2)

            cx = view_width / 2
            cy = view_height / 2 - 20
            if is_left:
                cx -= spacing_center + spacing_side * (ad - 1)
            else:
                cx += spacing_center + spacing_side * (ad - 1)
            transform.translate(cx - self._w / 2, cy - self._h / 2)
            scale = 0.85
            transform.scale(scale, scale)

        self.setTransform(transform)


class CoverFlowWidget(QGraphicsView):
    selection_changed = Signal(int)
    double_clicked = Signal(int)
    clicked = Signal(int)
    cover_snapped = Signal(int)  # emitted when snapping to a cover

    def __init__(self, parent=None):
        super().__init__(parent)

        if HAVE_OPENGL:
            self.setViewport(QOpenGLWidget())
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor(13, 13, 20))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Central album text (title + artist)
        self._title_text = QGraphicsTextItem()
        self._title_text.setDefaultTextColor(QColor("#ffffff"))
        self._title_text.setFont(QFont("sans-serif", 14, QFont.Bold))
        self._title_text.setZValue(2000)
        self._scene.addItem(self._title_text)

        self._artist_text = QGraphicsTextItem()
        self._artist_text.setDefaultTextColor(QColor(245, 245, 247, 140))
        self._artist_text.setFont(QFont("sans-serif", 12))
        self._artist_text.setZValue(2000)
        self._scene.addItem(self._artist_text)

        self._items: list[CoverFlowItem] = []
        self._cover_items: list[CoverItem] = []
        self._current = 0.0
        self._velocity = 0.0
        self._dragging = False
        self._last_x = 0.0
        self._cover_w = 260
        self._cover_h = 260

        self._phys_timer = QTimer(self)
        self._phys_timer.timeout.connect(self._update_physics)
        self._phys_timer.start(16)

        self._snap_anim = QPropertyAnimation(self, b"current_pos")
        self._snap_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._snap_anim.setDuration(350)

    def get_current(self) -> float:
        return self._current

    def set_current(self, value: float):
        self._current = value
        self._update_layout()

    current_pos = Property(float, get_current, set_current)

    # ── Public API (backward compatible) ──

    def set_items(self, items: list[CoverFlowItem]):
        self._items = items
        self._scene.clear()
        # Re-add text items after clear (they get removed by scene.clear)
        self._scene.addItem(self._title_text)
        self._scene.addItem(self._artist_text)
        self._cover_items.clear()
        self._current = 0.0
        self._velocity = 0.0

        for i, item in enumerate(items):
            ci = CoverItem(item.pixmap, i, self._cover_w, self._cover_h)
            self._scene.addItem(ci)
            self._cover_items.append(ci)

        self._update_layout()

    def scroll_to(self, index: int, animated: bool = True):
        if not self._items:
            return
        index = max(0, min(index, len(self._items) - 1))
        if animated:
            self._snap_anim.setStartValue(self._current)
            self._snap_anim.setEndValue(float(index))
            self._snap_anim.start()
        else:
            self._current = float(index)
            self._update_layout()

    def _update_layout(self):
        if not self._cover_items:
            return
        vw = self.viewport().width()
        vh = self.viewport().height()
        for ci in self._cover_items:
            ci.update_transform(self._current, vw, vh)
        idx = max(0, min(len(self._items) - 1, int(round(self._current))))

        # Update central text
        if self._items and 0 <= idx < len(self._items):
            item = self._items[idx]
            self._title_text.setPlainText(item.title)
            artist = item.subtitle.split(" · ")[0]
            self._artist_text.setPlainText(artist)
            tr = self._title_text.boundingRect()
            ar = self._artist_text.boundingRect()
            self._title_text.setPos(vw / 2 - tr.width() / 2, vh - 85)
            self._artist_text.setPos(vw / 2 - ar.width() / 2, vh - 65)
        else:
            self._title_text.setPlainText("")
            self._artist_text.setPlainText("")

        self.selection_changed.emit(idx)

    # ── Physics ──

    def _update_physics(self):
        if self._dragging:
            return
        if abs(self._velocity) < 0.003:
            if abs(self._current - round(self._current)) > 0.01:
                self._trigger_snap()
            return
        self._velocity *= 0.92
        self._current += self._velocity
        self._update_layout()
        if abs(self._velocity) < 0.003:
            self._trigger_snap()

    def _trigger_snap(self):
        target = max(0, min(len(self._items) - 1, int(round(self._current))))
        self._snap_anim.stop()
        self._snap_anim.setStartValue(self._current)
        self._snap_anim.setEndValue(float(target))
        self._snap_anim.start()
        self.cover_snapped.emit(target)

    # ── Mouse events ──

    def mousePressEvent(self, event):
        self._dragging = True
        self._snap_anim.stop()
        self._last_x = event.position().x()
        self._velocity = 0.0
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        dx = event.position().x() - self._last_x
        sensitivity = 0.004
        self._current -= dx * sensitivity
        self._velocity = -dx * sensitivity * 0.5
        self._last_x = event.position().x()
        self._update_layout()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)
        if abs(self._velocity) < 0.01:
            self._trigger_snap()

    def mouseDoubleClickEvent(self, event):
        idx = int(round(self._current))
        if 0 <= idx < len(self._items):
            self.double_clicked.emit(idx)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self._current -= delta * 0.5
        max_i = max(0, len(self._items) - 1)
        self._current = max(0.0, min(float(max_i), self._current))
        self._update_layout()
        self._trigger_snap()
