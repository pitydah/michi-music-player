"""CoverFlow — QGraphicsView-based carousel with OpenGL, physics, reflections, slider."""
import os
from dataclasses import dataclass

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation,
    Property, Signal, QRectF, QPointF,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QPixmap,
    QTransform, QFont, QPainterPath,
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsObject,
    QGraphicsTextItem, QGraphicsOpacityEffect, QGraphicsProxyWidget,
    QSlider,
)

from library.album_art import CoverFlowItem

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    HAVE_OPENGL = True
except ImportError:
    HAVE_OPENGL = False

# ── Render mode ──
_MODE = os.environ.get("MICHI_COVERFLOW_MODE", "classic_3d")
_DEBUG = os.environ.get("MICHI_COVERFLOW_DEBUG", "0") == "1"


def _clamp(x, a, b):
    return max(a, min(b, float(x)))


def _smoothstep(edge0, edge1, x):
    t = _clamp((x - edge0) / (edge1 - edge0) if edge1 != edge0 else 0.0, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ease_out_cubic(x):
    t = _clamp(x, 0.0, 1.0)
    return 1.0 - pow(1.0 - t, 3.0)


@dataclass
class CoverFlowItemState:
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation_y: float = 0.0
    opacity: float = 1.0
    darken_alpha: int = 0
    z: int = 0
    is_center: bool = False
    visible: bool = True


class CoverFlowLayoutEngine:
    """Pure math: calculates position, rotation, scale for each item."""

    def __init__(self):
        self.max_rot = 60.0
        self.center_scale = 1.05
        self.side_scale = 0.82
        self.far_scale = 0.52
        self.near_gap_factor = 0.72
        self.side_gap_factor = 0.32
        self.far_gap_factor = 0.18
        self.center_y_offset = -38

    def visible_indices(self, count: int, offset: float,
                        viewport_width: int) -> range:
        if viewport_width < 900:
            r = 7
        elif viewport_width > 1600:
            r = 14
        else:
            r = 10
        mid = round(offset)
        return range(max(0, mid - r), min(count, mid + r + 1))

    def item_state(self, index: int, offset: float,
                   cover_w: int, cover_h: int,
                   view_w: int, view_h: int,
                   velocity: float = 0.0) -> CoverFlowItemState:
        dist = index - offset
        ad = abs(dist)
        side = -1.0 if dist < 0 else 1.0

        center_t = 1.0 - _smoothstep(0.0, 1.0, ad)
        far_t = _smoothstep(1.8, 6.0, ad)

        # rotation — classic Apple linear + cap
        if ad <= 1.0:
            rot_raw = ad * 50.0
        elif ad <= 2.2:
            rot_raw = 50.0 + (ad - 1.0) * 8.0
        else:
            rot_raw = 60.0
        if ad < 0.10:
            rot_raw = 0.0
        rot = side * rot_raw

        # position
        near_gap = cover_w * self.near_gap_factor
        side_gap = cover_w * self.side_gap_factor
        far_gap = cover_w * self.far_gap_factor
        cx = view_w / 2.0
        if ad < 1.0:
            x = cx + side * near_gap * _smoothstep(0.0, 1.0, ad)
        else:
            x = cx + side * (near_gap + side_gap * (ad - 1.0)
                             + far_gap * max(0.0, ad - 3.0))
        cy = view_h / 2.0 + self.center_y_offset
        y = cy + (1.0 - center_t) * 16.0 + far_t * 12.0

        # scale — classic Apple: center 1.05, ±1 = 0.87, ±2 = 0.65, min 0.45
        scale = _clamp(self.center_scale - max(0.0, ad - 0.2) * 0.22, 0.45, 1.05)

        # visual state
        is_center = ad < 0.50
        darken = 0 if is_center else int(_clamp(ad * 33, 0, 120))
        z_val = 2000 - int(ad * 22)

        # opacity
        opacity = 1.0 - min(0.55, ad * 0.07)
        if ad > 9:
            opacity = 0.0
        visible = ad <= 10

        return CoverFlowItemState(
            x=x, y=y, scale=scale, rotation_y=rot,
            opacity=max(0.0, opacity), darken_alpha=darken,
            z=z_val, is_center=is_center, visible=visible)


def _format_dur(seconds: float) -> str:
    if seconds <= 0:
        return ""
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


def _make_placeholder(w: int, h: int) -> QPixmap:
    pix = QPixmap(w, h)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    # glass rounded rect
    p.setPen(QPen(QColor(255, 255, 255, 18), 1.2))
    path = QPainterPath()
    path.addRoundedRect(3, 3, w - 6, h - 6, 14, 14)
    p.fillPath(path, QColor(255, 255, 255, 8))
    p.drawPath(path)
    # inner disc icon
    cx, cy = w / 2, h / 2
    r = min(w, h) // 6
    p.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.drawEllipse(QPointF(cx, cy), r * 0.3, r * 0.3)
    p.end()
    return pix


class CoverItem(QGraphicsObject):
    def __init__(self, pixmap: QPixmap | None, index: int,
                 width: int = 260, height: int = 260):
        super().__init__()
        self._index = index
        self._w = width
        self._h = height
        self._ref_h = int(height * 0.40)
        self._darken_alpha = 0
        self._is_center = False
        self._cover_requested = False
        self._cover_failed = False
        self._fade_alpha = 1.0

        if pixmap is None or pixmap.isNull():
            self._pixmap = _make_placeholder(width, height)
            self._placeholder = self._pixmap
            self._cover_loaded = False
        else:
            self._placeholder = QPixmap()
            self._pixmap = pixmap.scaled(
                width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._cover_loaded = True

        self._cached = None

    def _ensure_cached(self):
        if self._cached is None:
            self._cached = self._generate_reflection()

    def _generate_reflection(self) -> QPixmap:
        total_h = self._h + self._ref_h
        cached = QPixmap(self._w, total_h)
        cached.fill(Qt.transparent)
        p = QPainter(cached)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        radius = 14.0
        path = QPainterPath()
        path.addRoundedRect(0, 0, self._w, self._h, radius, radius)

        p.save()
        p.setClipPath(path)
        p.drawPixmap(0, 0, self._pixmap)
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        p.drawPath(path)

        # reflection
        p.save()
        p.translate(0, self._h + self._ref_h)
        p.scale(1, -1)
        p.setOpacity(0.12)
        p.setClipPath(path)
        p.drawPixmap(0, 0, self._pixmap)
        p.restore()

        grad = QLinearGradient(0, self._h, 0, total_h)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.08, QColor(13, 13, 20, 80))
        grad.setColorAt(0.25, QColor(13, 13, 20, 185))
        grad.setColorAt(0.55, QColor(13, 13, 20, 255))
        grad.setColorAt(1.0, QColor(13, 13, 20, 255))
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.fillRect(0, self._h, self._w, self._ref_h, grad)
        p.end()
        return cached

    def set_real_cover(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            self._cover_failed = True
            return
        self._real_cover = pixmap.scaled(
            self._w, self._h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._cover_loaded = True
        self._cover_requested = False
        self._fade_alpha = 0.0
        anim = QVariantAnimation()
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(self._on_fade_step)
        anim.finished.connect(self._on_fade_done)
        anim.start()
        self._fade_anim = anim

    def _on_fade_step(self, value: float):
        self._fade_alpha = value
        self.update()

    def _on_fade_done(self):
        self._pixmap = self._real_cover
        self._fade_alpha = 1.0
        self._placeholder = QPixmap()
        self._cached = self._generate_reflection()
        self.update()

    @property
    def needs_cover(self) -> bool:
        return not self._cover_loaded and not self._cover_requested and not self._cover_failed

    def mark_cover_requested(self):
        self._cover_requested = True

    def _apply_state(self, state, w, h):
        self._is_center = state.is_center
        self._darken_alpha = state.darken_alpha
        self.setOpacity(state.opacity)
        self.setZValue(state.z)

        transform = QTransform()
        if abs(state.rotation_y) > 0.0:
            # Pivot from inner edge (coverflowjs pattern)
            if state.rotation_y < 0:
                # Left tile: pivot at right edge
                pivot_x, pivot_y = w, h / 2
            else:
                # Right tile: pivot at left edge
                pivot_x, pivot_y = 0, h / 2
            transform.translate(pivot_x, pivot_y)
            transform.rotate(state.rotation_y, Qt.YAxis)
            transform.translate(-pivot_x, -pivot_y)
        transform.translate(state.x - w / 2, state.y - h / 2)
        transform.scale(state.scale, state.scale)
        self.setTransform(transform)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._w, self._h + self._ref_h)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self._ensure_cached()
        painter.drawPixmap(0, 0, self._cached)

        if self._is_center:
            painter.save()
            shadow = QRadialGradient(self._w / 2, self._h, self._w * 0.55)
            shadow.setColorAt(0.0, QColor(0, 0, 0, 55))
            shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(shadow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(self._w / 2, self._h), self._w * 0.45, 10)
            painter.restore()

            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255, 80), 1.3))
            path = QPainterPath()
            path.addRoundedRect(0.6, 0.6, self._w - 1.2, self._h - 1.2, 14, 14)
            painter.drawPath(path)
            painter.restore()

        if hasattr(self, '_real_cover') and self._fade_alpha < 1.0:
            painter.save()
            painter.setOpacity(self._fade_alpha)
            painter.drawPixmap(0, 0, self._real_cover)
            painter.restore()

        if self._darken_alpha > 0:
            painter.save()
            gray = max(40, 255 - int(self._darken_alpha * 1.6))
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            painter.fillRect(0, 0, self._w, self._h + self._ref_h,
                             QColor(gray, gray, gray))
            painter.restore()

    def update_transform(self, current_offset: float, view_width: float,
                         view_height: float, velocity: float = 0.0,
                         geometry: dict | None = None):
        dist = self._index - current_offset
        ad = abs(dist)
        side = -1.0 if dist < 0 else 1.0
        geo = geometry or {}

        max_rot = geo.get("max_rot", 60.0)
        near_gap = self._w * geo.get("near_gap_factor", 0.72)
        side_gap = self._w * geo.get("side_gap_factor", 0.32)
        far_gap = self._w * geo.get("far_gap_factor", 0.18)
        center_scale = geo.get("center_scale", 1.04)
        side_scale = geo.get("side_scale", 0.82)
        far_scale = geo.get("far_scale", 0.66)
        center_y_off = geo.get("center_y_offset", -38)

        # smooth factors
        center_t = 1.0 - _smoothstep(0.0, 1.0, ad)
        far_t = _smoothstep(1.8, 6.0, ad)

        # rotation
        rot_raw = max_rot * _ease_out_cubic(min(ad, 1.6) / 1.6)
        if ad < 0.10:
            rot_raw = 0.0
        rot = side * rot_raw

        # position
        center_x = view_width / 2.0
        if ad < 1.0:
            x = center_x + side * near_gap * _smoothstep(0.0, 1.0, ad)
        else:
            x = center_x + side * (near_gap + side_gap * (ad - 1.0) + far_gap * max(0.0, ad - 3.0))

        center_y = view_height / 2.0 + center_y_off
        y = center_y + (1.0 - center_t) * 16.0 + far_t * 12.0

        # scale
        scale = center_scale * center_t + side_scale * (1.0 - center_t) * (1.0 - far_t) + far_scale * far_t
        v_zoom = min(0.07, abs(velocity) * 0.5)
        scale = max(0.58, scale - v_zoom)

        # z-value and visual state
        self._is_center = ad < 0.42
        self._darken_alpha = int(_clamp(ad * 33, 0, 120))
        if self._is_center:
            self._darken_alpha = 0
        self.setZValue(2000 - int(ad * 22))

        # opacity fade for far items
        opacity = 1.0 - min(0.55, ad * 0.07)
        if ad > 9:
            opacity = 0.0
        self.setOpacity(max(0.0, opacity))

        # build transform
        transform = QTransform()
        if abs(rot) > 0.0:
            transform.translate(self._w / 2, self._h / 2)
            transform.rotate(rot, Qt.YAxis)
            transform.translate(-self._w / 2, -self._h / 2)
        transform.translate(x - self._w / 2, y - self._h / 2)
        transform.scale(scale, scale)
        self.setTransform(transform)


class CoverFlowWidget(QGraphicsView):
    selection_changed = Signal(int)
    double_clicked = Signal(int)
    clicked = Signal(int)
    cover_snapped = Signal(int)
    request_cover = Signal(int, object)

    play_album_requested = Signal(int)
    queue_album_requested = Signal(int)
    playlist_album_requested = Signal(int)
    metadata_album_requested = Signal(int)
    details_album_requested = Signal(int)
    cover_search_requested = Signal(int)
    open_folder_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._render_mode = _MODE
        self._use_opengl = _MODE not in ("no_opengl", "safe_2d") and HAVE_OPENGL
        if self._use_opengl:
            try:
                self.setViewport(QOpenGLWidget())
            except Exception:
                self._use_opengl = False
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor(9, 11, 17))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._geometry = {
            "max_rot": 60.0, "center_scale": 1.04, "side_scale": 0.82,
            "far_scale": 0.66, "near_gap_factor": 0.72, "side_gap_factor": 0.32,
            "far_gap_factor": 0.18, "center_y_offset": -38,
        }

        self._items: list[CoverFlowItem] = []
        self._cover_items: list[CoverItem] = []
        self._current = 0.0
        self._velocity = 0.0
        self._dragging = False
        self._drag_moved = False
        self._last_x = 0.0
        self._press_x = 0.0
        self._cover_w = 260
        self._cover_h = 260
        self._last_text_idx = -1
        self._last_emitted_idx = -1
        self._last_title = ""
        self._last_artist = ""
        self._slider_dragging = False
        self._syncing_slider = False

        # physics params
        self._drag_sensitivity = 1.0 / 190.0
        self._wheel_sensitivity = 0.009
        self._friction = 0.88
        self._min_velocity = 0.0025
        self._max_velocity = 0.32

        self._phys_timer = QTimer(self)
        self._phys_timer.timeout.connect(self._update_physics)

        self._layout_engine = CoverFlowLayoutEngine()

        self._wheel_snap_timer = QTimer(self)
        self._wheel_snap_timer.setSingleShot(True)
        self._wheel_snap_timer.timeout.connect(self._trigger_snap)

        self._snap_anim = QPropertyAnimation(self, b"current_pos")
        self._snap_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._snap_anim.setDuration(340)
        self._snap_anim.finished.connect(self._on_snap_finished)
        self._snapping = False

        self._create_overlay_items()
        self._create_slider()

    # ── Current pos property ──

    def get_current(self) -> float:
        return self._current

    def set_current(self, value: float):
        self._current = value
        self._update_layout()

    current_pos = Property(float, get_current, set_current)

    # ── Slider ──

    def _create_slider(self):
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setObjectName("coverflowSlider")
        self._slider.setRange(0, 0)
        self._slider.setValue(0)
        self._slider.setFixedHeight(20)
        self._slider.setCursor(Qt.PointingHandCursor)
        self._slider.setStyleSheet("""
            QSlider#coverflowSlider { background: transparent; border: none; }
            QSlider#coverflowSlider::groove:horizontal {
                height: 2px; border-radius: 1px; margin: 0 4px;
                background: rgba(255,255,255,0.055);
            }
            QSlider#coverflowSlider::sub-page:horizontal {
                height: 2px; border-radius: 1px;
                background: rgba(255,255,255,0.35);
            }
            QSlider#coverflowSlider::handle:horizontal {
                width: 8px; height: 8px; margin: -3px -4px;
                border-radius: 4px; background: rgba(255,255,255,0.92);
                border: none;
            }
            QSlider#coverflowSlider::handle:horizontal:hover {
                width: 14px; height: 14px; margin: -6px -7px;
                border-radius: 7px; background: #FFFFFF;
            }
        """)
        self._slider.valueChanged.connect(self._on_slider_changed)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider_proxy = QGraphicsProxyWidget()
        self._slider_proxy.setWidget(self._slider)
        self._slider_proxy.setZValue(4000)
        self._scene.addItem(self._slider_proxy)
        self._slider.setVisible(False)

    def _on_slider_pressed(self):
        self._slider_dragging = True
        self._snap_anim.stop()
        self._velocity = 0.0

    def _on_slider_released(self):
        self._slider_dragging = False
        self.scroll_to(self._slider.value(), animated=True)

    def _on_slider_changed(self, value: int):
        if self._syncing_slider:
            return
        if self._slider_dragging:
            self._current = float(value)
            self._velocity = 0.0
            self._update_layout()

    def _position_slider(self):
        if not hasattr(self, "_slider_proxy"):
            return
        vw = self.viewport().width()
        vh = self.viewport().height()
        w = max(240, min(620, int(vw * 0.46)))
        self._slider.setFixedWidth(w)
        self._slider_proxy.setPos(vw / 2 - w / 2, vh - 30)

    # ── Overlay items ──

    def _create_overlay_items(self):
        self._title_text = QGraphicsTextItem()
        self._title_text.setDefaultTextColor(QColor("#ffffff"))
        self._title_text.setFont(QFont("sans-serif", 16, 750))
        self._title_text.setZValue(2000)
        self._title_effect = QGraphicsOpacityEffect()
        self._title_effect.setOpacity(1.0)
        self._title_text.setGraphicsEffect(self._title_effect)
        self._scene.addItem(self._title_text)

        self._artist_text = QGraphicsTextItem()
        self._artist_text.setDefaultTextColor(QColor(255, 255, 255, 190))
        self._artist_text.setFont(QFont("sans-serif", 12.5))
        self._artist_text.setZValue(2000)
        self._artist_effect = QGraphicsOpacityEffect()
        self._artist_effect.setOpacity(1.0)
        self._artist_text.setGraphicsEffect(self._artist_effect)
        self._scene.addItem(self._artist_text)

        self._meta_text = QGraphicsTextItem()
        self._meta_text.setDefaultTextColor(QColor(255, 255, 255, 120))
        self._meta_text.setFont(QFont("sans-serif", 10))
        self._meta_text.setZValue(2000)
        self._scene.addItem(self._meta_text)

        self._position_text = QGraphicsTextItem()
        self._position_text.setDefaultTextColor(QColor(255, 255, 255, 90))
        self._position_text.setFont(QFont("sans-serif", 9.5))
        self._position_text.setZValue(2000)
        self._scene.addItem(self._position_text)

        self._empty_msg = QGraphicsTextItem()
        self._empty_msg.setHtml(
            '<div style="text-align:center">'
            '<p style="font-size:16pt;color:rgba(245,245,247,210)">'
            'No hay álbumes en tu biblioteca</p>'
            '<p style="font-size:12pt;color:rgba(245,245,247,148)">'
            'Añade una carpeta musical para activar CoverFlow</p>'
            '</div>')
        self._empty_msg.setZValue(3000)
        self._scene.addItem(self._empty_msg)

    # ── Public API ──

    def _clear_scene_preserve_slider(self):
        for ci in list(self._cover_items):
            self._scene.removeItem(ci)
        self._cover_items.clear()
        for attr in ('_title_text', '_artist_text', '_meta_text',
                     '_position_text', '_empty_msg'):
            item = getattr(self, attr, None)
            if item and item.scene() is self._scene:
                self._scene.removeItem(item)

    def set_items(self, items: list[CoverFlowItem]):
        self._items = items
        self._clear_scene_preserve_slider()
        self._cover_items.clear()
        self._current = 0.0
        self._velocity = 0.0
        self._last_text_idx = -1
        self._last_emitted_idx = -1

        self._create_overlay_items()

        for i, item in enumerate(items):
            ci = CoverItem(item.pixmap, i, self._cover_w, self._cover_h)
            self._scene.addItem(ci)
            self._cover_items.append(ci)

        self._slider.setRange(0, max(0, len(items) - 1))
        self._slider.setVisible(len(items) > 1)
        self._slider.setValue(0)

        self._update_layout()
        self._position_slider()

    def item_at(self, idx: int) -> CoverFlowItem | None:
        if 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    def current_item(self) -> CoverFlowItem | None:
        return self.item_at(self.current_index())

    def current_index(self) -> int:
        if not self._items:
            return -1
        return max(0, min(len(self._items) - 1, int(round(self._current))))

    def count(self) -> int:
        return len(self._items)

    def scroll_to(self, index: int, animated: bool = True):
        if not self._items:
            return
        index = max(0, min(index, len(self._items) - 1))
        if animated:
            self._snap_anim.stop()
            self._snap_anim.setDuration(self._snap_duration_for(abs(self._current - index)))
            self._snap_anim.setStartValue(self._current)
            self._snap_anim.setEndValue(float(index))
            self._snap_anim.start()
        else:
            self._current = float(index)
            self._update_layout()

    def _snap_duration_for(self, dist: float) -> int:
        return int(max(150, min(380, 140 + dist * 110)))

    # ── Layout ──

    def _update_layout(self):
        if not self._cover_items:
            vw = self.viewport().width()
            vh = self.viewport().height()
            br = self._empty_msg.boundingRect()
            self._empty_msg.setPos(vw / 2 - br.width() / 2, vh / 2 - 60)
            self._empty_msg.setVisible(True)
            self._title_text.setPlainText("")
            self._artist_text.setPlainText("")
            self._meta_text.setPlainText("")
            self._position_text.setPlainText("")
            return

        vw = self.viewport().width()
        vh = self.viewport().height()
        self._empty_msg.setVisible(False)

        for ci in self._cover_items:
            state = self._layout_engine.item_state(
                ci._index, self._current, self._cover_w, self._cover_h,
                vw, vh, self._velocity)
            if not state.visible:
                ci.setVisible(False)
                continue
            ci.setVisible(True)
            if self._render_mode == "safe_2d":
                state.rotation_y = 0.0
            if self._render_mode == "no_reflection":
                ci._ref_h = 0
            ci._apply_state(state, self._cover_w, self._cover_h)

            if ci.needs_cover:
                ci.mark_cover_requested()
                item = self._items[ci._index]
                self.request_cover.emit(ci._index, item)

        idx = self.current_index()

        if self._last_emitted_idx != idx:
            self.selection_changed.emit(idx)
            self._last_emitted_idx = idx

        # Sync slider
        if not self._slider_dragging:
            self._syncing_slider = True
            self._slider.setValue(idx)
            self._syncing_slider = False

        # Position
        self._position_text.setPlainText(f"{idx + 1} / {len(self._items)}")
        pr = self._position_text.boundingRect()
        self._position_text.setPos(vw - pr.width() - 20, vh - 58)

        # Debug overlay
        if _DEBUG:
            self._show_debug_overlay(vw, vh, idx)

        # Center text
        if idx != self._last_text_idx:
            self._last_text_idx = idx
            self._update_center_text(idx)
        else:
            self._position_texts_only()

    def _visible_range(self) -> int:
        vw = self.viewport().width()
        if vw < 900:
            return 7
        if vw > 1600:
            return 14
        return 10

    def _show_debug_overlay(self, vw: int, vh: int, idx: int):
        lines = [
            f"CoverFlow {self._render_mode} | {len(self._items)} items",
            f"idx {idx} offset={self._current:.2f} v={self._velocity:.4f}",
            f"GL={'on' if self._use_opengl else 'off'} {vw}x{vh}",
            f"cover {self._cover_w}x{self._cover_h}",
        ]
        text = " | ".join(lines)
        self._meta_text.setPlainText(self._meta_text.toPlainText())
        self._position_text.setPlainText(
            f"{self._position_text.toPlainText()}\n{text}")

    def _update_center_text(self, idx: int):
        if not self._items or idx < 0 or idx >= len(self._items):
            return
        item = self._items[idx]
        artist = (
            item.subtitle.split(" · ")[0]
            if item.subtitle and " · " in item.subtitle
            else item.subtitle or "Desconocido")
        tracks = item.data.get("tracks", [])
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = _format_dur(dur)
        meta_parts = []
        if count:
            meta_parts.append(f"{count} canciones")
        if dur_str:
            meta_parts.append(dur_str)
        meta = " · ".join(meta_parts)

        title_changed = item.title != self._last_title
        artist_changed = artist != self._last_artist
        self._last_title = item.title
        self._last_artist = artist

        if title_changed or artist_changed:
            self._animate_text_change(item.title, artist)
        else:
            self._title_text.setPlainText(item.title)
            self._artist_text.setPlainText(artist)
            self._position_texts_only()

        self._meta_text.setPlainText(meta)
        self._position_texts_only()

    def _animate_text_change(self, new_title: str, new_artist: str):
        anim = QVariantAnimation()
        anim.setDuration(120)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)

        def _on_fade_out():
            self._title_text.setPlainText(new_title)
            self._artist_text.setPlainText(new_artist)
            self._title_effect.setOpacity(1.0)
            self._artist_effect.setOpacity(1.0)
            self._position_texts_only()

        anim.finished.connect(_on_fade_out)
        anim.valueChanged.connect(
            lambda v: (self._title_effect.setOpacity(v),
                       self._artist_effect.setOpacity(v)))
        anim.start()
        self._text_anim = anim

    def _position_texts_only(self):
        vw = self.viewport().width()
        vh = self.viewport().height()
        tr = self._title_text.boundingRect()
        ar = self._artist_text.boundingRect()
        mr = self._meta_text.boundingRect()
        self._title_text.setPos(vw / 2 - tr.width() / 2, vh - 118)
        self._artist_text.setPos(vw / 2 - ar.width() / 2, vh - 96)
        self._meta_text.setPos(vw / 2 - mr.width() / 2, vh - 74)

    # ── Cover loading ──

    def _on_cover_loaded(self, idx: int, pixmap: QPixmap):
        if 0 <= idx < len(self._cover_items) and not pixmap.isNull():
            self._cover_items[idx].set_real_cover(pixmap)
            # Cache for future rebuilds
            if not hasattr(self, '_cover_cache'):
                self._cover_cache = {}
            self._cover_cache[idx] = pixmap

    # ── Physics ──

    def _update_physics(self):
        if self._dragging:
            return
        if abs(self._velocity) < self._min_velocity:
            if abs(self._current - round(self._current)) > 0.01:
                self._trigger_snap()
            self._phys_timer.stop()
            return

        self._velocity *= self._friction
        self._current += self._velocity
        self._clamp_current_soft()
        self._update_layout()

        if abs(self._velocity) < self._min_velocity:
            self._trigger_snap()
            self._phys_timer.stop()

    def _clamp_current_soft(self):
        if not self._items:
            self._current = 0.0
            return
        max_i = max(0.0, float(len(self._items) - 1))
        overscroll = 0.65
        if self._current < -overscroll:
            self._current = -overscroll
            self._velocity *= 0.35
        elif self._current > max_i + overscroll:
            self._current = max_i + overscroll
            self._velocity *= 0.35
        spring = 0.065
        if self._current < 0:
            self._velocity += (0 - self._current) * spring
        elif self._current > max_i:
            self._velocity += (max_i - self._current) * spring
        self._velocity = _clamp(self._velocity, -self._max_velocity, self._max_velocity)

    def _trigger_snap(self):
        if not self._items or self._snapping:
            return
        target = self.current_index()
        if abs(self._current - target) < 0.008:
            self._current = float(target)
            self._velocity = 0.0
            self._update_layout()
            self.cover_snapped.emit(target)
            return
        self._snap_anim.stop()
        self._snapping = True
        self._snap_anim.setDuration(self._snap_duration_for(abs(self._current - target)))
        self._snap_anim.setStartValue(self._current)
        self._snap_anim.setEndValue(float(target))
        self._snap_anim.start()

    def _on_snap_finished(self):
        self._snapping = False
        if not self._items:
            return
        target = self.current_index()
        self._current = float(target)
        self._velocity = 0.0
        self._update_layout()
        self.cover_snapped.emit(target)

    # ── Background ──

    def drawBackground(self, painter, rect):
        painter.save()
        # Cover backdrop — blurred center cover image
        ci = self.current_index()
        if 0 <= ci < len(self._cover_items):
            center = self._cover_items[ci]
            if center._cached and not center._cached.isNull():
                w = center._cached.width()
                h = center._cached.height()
                scale = max(rect.width() / w, rect.height() / h) * 1.6
                x = (rect.width() - w * scale) / 2
                y = (rect.height() - h * scale) / 2 - rect.height() * 0.05
                painter.setOpacity(0.18)
                painter.drawPixmap(x, y, w * scale, h * scale, center._cached)

        # Darken layer
        painter.setOpacity(1.0)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        grad = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.65)
        grad.setColorAt(0.0, QColor(32, 36, 48, 210))
        grad.setColorAt(0.45, QColor(16, 18, 28, 240))
        grad.setColorAt(1.0, QColor(7, 9, 14, 255))
        painter.fillRect(rect, grad)
        # Subtle violet glow in center
        glow = QRadialGradient(rect.center(), rect.width() * 0.4)
        glow.setColorAt(0.0, QColor(110, 90, 200, 14))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow)
        painter.restore()

    # ── Resize ──

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_cover_size()
        self._update_layout()
        self._position_slider()

    def _update_cover_size(self):
        vw = self.viewport().width()
        vh = self.viewport().height()
        by_w = int(vw * 0.23)
        by_h = int(vh * 0.40)
        size = max(190, min(310, by_w, by_h))
        if abs(size - self._cover_w) >= 14:
            self._cover_w = size
            self._cover_h = size
            self._rebuild_items()

    def _rebuild_items(self):
        if not self._items:
            return
        saved = self._current
        self._clear_scene_preserve_slider()
        self._create_overlay_items()
        for i, item in enumerate(self._items):
            ci = CoverItem(item.pixmap, i, self._cover_w, self._cover_h)
            self._scene.addItem(ci)
            self._cover_items.append(ci)
        self._current = max(0, min(len(self._items) - 1, saved))
        self._update_layout()
        self._position_slider()

    # ── Context menu ──

    def contextMenuEvent(self, event):
        idx = self.current_index()
        if not self._items or idx < 0 or idx >= len(self._items):
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: rgba(18,20,28,0.98); color: rgba(255,255,255,0.88);
              border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 6px 4px; }
            QMenu::item { padding: 8px 28px 8px 14px; border-radius: 7px; font-size: 12.5px; }
            QMenu::item:selected { background: rgba(255,255,255,0.095); color: #FFFFFF; }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.08); margin: 4px 8px; }
        """)
        menu.addAction("Reproducir álbum", lambda: self.play_album_requested.emit(idx))
        menu.addAction("Añadir álbum a cola", lambda: self.queue_album_requested.emit(idx))
        menu.addSeparator()
        menu.addAction("Crear playlist desde álbum", lambda: self.playlist_album_requested.emit(idx))
        menu.addAction("Editar metadatos", lambda: self.metadata_album_requested.emit(idx))
        menu.addAction("Buscar carátula", lambda: self.cover_search_requested.emit(idx))
        menu.addAction("Abrir carpeta", lambda: self.open_folder_requested.emit(idx))
        menu.addSeparator()
        menu.addAction("Ver detalles", lambda: self.details_album_requested.emit(idx))
        menu.exec(event.globalPos())

    # ── Keyboard ──

    def keyPressEvent(self, event):
        if not self._items:
            return super().keyPressEvent(event)
        idx = self.current_index()
        k = event.key()

        if k == Qt.Key_Left:
            self.scroll_to(idx - 1)
        elif k == Qt.Key_Right:
            self.scroll_to(idx + 1)
        elif k == Qt.Key_PageUp:
            self.scroll_to(idx - 5)
        elif k == Qt.Key_PageDown:
            self.scroll_to(idx + 5)
        elif k == Qt.Key_Home:
            self.scroll_to(0)
        elif k == Qt.Key_End:
            self.scroll_to(len(self._items) - 1)
        elif k in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space):
            self.play_album_requested.emit(idx)
        elif k == Qt.Key_A:
            self.queue_album_requested.emit(idx)
        elif k == Qt.Key_I:
            self.details_album_requested.emit(idx)
        elif k == Qt.Key_M:
            self.metadata_album_requested.emit(idx)
        elif k == Qt.Key_F:
            self.cover_search_requested.emit(idx)
        else:
            return super().keyPressEvent(event)
        event.accept()

    # ── Mouse ──

    def mousePressEvent(self, event):
        self._dragging = True
        self._drag_moved = False
        self._phys_timer.stop()
        self._snap_anim.stop()
        self._snapping = False
        self._press_x = event.position().x()
        self._last_x = self._press_x
        self._velocity = 0.0
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        dx = event.position().x() - self._last_x
        total_dx = event.position().x() - self._press_x
        if abs(total_dx) > 5:
            self._drag_moved = True
        delta = -dx * self._drag_sensitivity
        self._current += delta
        self._velocity = delta * 0.85
        self._last_x = event.position().x()
        self._clamp_current_soft()
        self._update_layout()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)
        self._velocity = _clamp(self._velocity, -self._max_velocity, self._max_velocity)

        if not self._drag_moved:
            # Click on a side cover — navigate to it
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, CoverItem) and hasattr(item, '_index'):
                if item._index != self.current_index():
                    self.scroll_to(item._index)
                else:
                    self.clicked.emit(item._index)
        else:
            if abs(self._velocity) > self._min_velocity:
                self._phys_timer.start(16)
            else:
                self._trigger_snap()

    def mouseDoubleClickEvent(self, event):
        idx = self.current_index()
        if 0 <= idx < len(self._items):
            self.play_album_requested.emit(idx)
            self.double_clicked.emit(idx)

    def wheelEvent(self, event):
        pixel = event.pixelDelta()
        if pixel.x() or pixel.y():
            d = pixel.x() if abs(pixel.x()) > abs(pixel.y()) else pixel.y()
            self._current -= d * self._wheel_sensitivity
        else:
            angle = event.angleDelta()
            if abs(angle.x()) > abs(angle.y() * 0.6):
                # Horizontal navigation
                self._current -= angle.x() / 120.0 * 0.42
            elif abs(angle.y()) > 0:
                # Pure vertical: zoom
                self._layout_engine.center_scale = _clamp(
                    self._layout_engine.center_scale + angle.y() / 120.0 * 0.02,
                    0.90, 1.25)

        self._clamp_current_soft()
        self._update_layout()
        self._velocity = 0.0
        self._wheel_snap_timer.start(180)
