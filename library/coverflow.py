"""CoverFlow — QGraphicsView-based carousel with OpenGL, physics, reflections, slider."""
import math
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation,
    Property, Signal, QRectF, QPointF,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QPixmap,
    QTransform, QFont, QPainterPath, QBrush,
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


def _clamp(x, a, b):
    return max(a, min(b, float(x)))


def _smoothstep(edge0, edge1, x):
    t = _clamp((x - edge0) / (edge1 - edge0) if edge1 != edge0 else 0.0, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ease_out_cubic(x):
    t = _clamp(x, 0.0, 1.0)
    return 1.0 - pow(1.0 - t, 3.0)


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
        self._ref_h = int(height * 0.55)
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
        p.setOpacity(0.18)
        p.setClipPath(path)
        p.drawPixmap(0, 0, self._pixmap)
        p.restore()

        grad = QLinearGradient(0, self._h, 0, total_h)
        grad.setColorAt(0.0, QColor(13, 13, 20, 80))
        grad.setColorAt(0.12, QColor(13, 13, 20, 170))
        grad.setColorAt(0.35, QColor(13, 13, 20, 255))
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

    def boundingRect(self) -> QRectF:
        return QRectF(-self._w / 2, -self._h / 2, self._w, self._h + self._ref_h)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self._ensure_cached()
        painter.drawPixmap(0, 0, self._cached)

        if self._is_center:
            painter.save()
            shadow = QRadialGradient(self._w / 2, self._h, self._w * 0.55)
            shadow.setColorAt(0.0, QColor(0, 0, 0, 40))
            shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(shadow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(self._w / 2, self._h), self._w * 0.38, 8)
            painter.restore()

            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255, 48), 1.3))
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
            painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            painter.fillRect(0, 0, int(self._w), int(self._h + self._ref_h),
                             QColor(0, 0, 0, self._darken_alpha))
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
        side_t = _smoothstep(0.0, 2.6, ad)
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

        if HAVE_OPENGL:
            self.setViewport(QOpenGLWidget())
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

        self._wheel_snap_timer = QTimer(self)
        self._wheel_snap_timer.setSingleShot(True)
        self._wheel_snap_timer.timeout.connect(self._trigger_snap)

        self._snap_anim = QPropertyAnimation(self, b"current_pos")
        self._snap_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._snap_anim.setDuration(340)
        self._snap_anim.finished.connect(self._on_snap_finished)

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
        self._slider.setFixedHeight(26)
        self._slider.setCursor(Qt.PointingHandCursor)
        self._slider.setStyleSheet("""
            QSlider#coverflowSlider { background: transparent; }
            QSlider#coverflowSlider::groove:horizontal {
                height: 5px; border-radius: 3px;
                background: rgba(255,255,255,0.085);
            }
            QSlider#coverflowSlider::sub-page:horizontal {
                height: 5px; border-radius: 3px;
                background: rgba(255,255,255,0.32);
            }
            QSlider#coverflowSlider::handle:horizontal {
                width: 15px; height: 15px; margin: -5px 0; border-radius: 8px;
                background: rgba(255,255,255,0.84);
                border: 1px solid rgba(255,255,255,0.50);
            }
            QSlider#coverflowSlider::handle:horizontal:hover {
                background: #FFFFFF; border: 1px solid rgba(255,255,255,0.78);
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

    def set_items(self, items: list[CoverFlowItem]):
        self._items = items
        self._scene.clear()
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

        vis_range = self._visible_range()
        for ci in self._cover_items:
            dist = ci._index - self._current
            if abs(dist) > vis_range:
                ci.setVisible(False)
                continue
            ci.setVisible(True)
            ci.update_transform(self._current, vw, vh, self._velocity, self._geometry)

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
        if not self._items:
            return
        target = self.current_index()
        if abs(self._current - target) < 0.008:
            self._current = float(target)
            self._velocity = 0.0
            self._update_layout()
            self.cover_snapped.emit(target)
            return
        self._snap_anim.stop()
        self._snap_anim.setDuration(self._snap_duration_for(abs(self._current - target)))
        self._snap_anim.setStartValue(self._current)
        self._snap_anim.setEndValue(float(target))
        self._snap_anim.start()

    def _on_snap_finished(self):
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
        grad = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.65)
        grad.setColorAt(0.0, QColor(28, 31, 42, 230))
        grad.setColorAt(0.55, QColor(12, 14, 21, 245))
        grad.setColorAt(1.0, QColor(7, 9, 14, 255))
        painter.fillRect(rect, grad)
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
        self._scene.clear()
        self._cover_items.clear()
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
        self._snap_anim.stop()
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
            self._current -= event.angleDelta().y() / 120.0 * 0.42

        self._clamp_current_soft()
        self._update_layout()
        self._velocity = 0.0
        self._wheel_snap_timer.start(180)
