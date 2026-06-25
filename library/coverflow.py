"""CoverFlow — QGraphicsView-based carousel with OpenGL, physics, reflections, slider."""
import os

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation,
    Property, Signal, QPointF,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QPixmap,
    QTransform, QFont, QPainterPath,
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene,
    QGraphicsTextItem, QGraphicsOpacityEffect, QGraphicsProxyWidget,
    QGraphicsPixmapItem, QSlider, QGraphicsRectItem, QGraphicsEllipseItem,
)

from library.album_art import CoverFlowItem

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    HAVE_OPENGL = True
except ImportError:
    HAVE_OPENGL = False

# ── Calibration (override via env vars) ──
_CF_GAP = float(os.environ.get("MICHI_CF_GAP", "0.65"))
_CF_ROT_FACTOR = float(os.environ.get("MICHI_CF_ROT", "22.0"))
_CF_SCALE_DECAY = float(os.environ.get("MICHI_CF_SCALE", "0.88"))
_MODE = os.environ.get("MICHI_COVERFLOW_MODE", "classic_3d")
_DEBUG = os.environ.get("MICHI_COVERFLOW_DEBUG", "0") == "1"


def _clamp(x, a, b):
    return max(a, min(b, float(x)))


def _format_dur(seconds: float) -> str:
    if seconds is None or seconds <= 0:
        return ""
    m, s = divmod(int(seconds), 60)
    if seconds >= 3600:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def coverflow_layout(offset: float, view_w: float, view_h: float,
                     cover_w: float, cover_h: float) -> dict:
    """Pure math: position, rotation, scale, depth for one item.

    Returns dict with keys: x, y, scale, rot, z, visible.
    Calibrated via MICHI_CF_GAP, MICHI_CF_ROT, MICHI_CF_SCALE env vars.
    """
    abs_off = abs(offset)
    sign = -1.0 if offset < 0 else 1.0

    base_gap = cover_w * _CF_GAP
    x = view_w / 2.0 + sign * base_gap * (abs_off + 0.2 * abs_off ** 1.4)

    rot = 0.0 if abs_off < 0.15 else sign * min(55.0, abs_off * _CF_ROT_FACTOR)

    scale = max(0.45, 1.0 * (_CF_SCALE_DECAY ** abs_off))

    y = view_h / 2.0 - 20 + abs_off * 6.0 - offset ** 2 * 1.5

    z = int(2000 - abs_off * 20)
    visible = abs_off <= 10.0

    return {"x": x, "y": y, "scale": scale, "rot": rot,
            "z": z, "visible": visible}


def apply_layout_state(item, state: dict, cover_w: int, cover_h: int):
    """Apply position, rotation (edge-pivot), scale and z-value."""
    x, y, s, rot, z = state["x"], state["y"], state["scale"], state["rot"], state["z"]
    item.setPos(x, y)
    item.setZValue(z)

    transform = QTransform()
    if rot != 0.0:
        pivot_x = cover_w if rot > 0 else 0
        transform.translate(pivot_x, cover_h / 2)
        transform.rotate(rot, Qt.YAxis)
        transform.translate(-pivot_x, -cover_h / 2)
    transform.scale(s, s)
    item.setTransform(transform)
    item.setVisible(state.get("visible", True))


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


class CoverPixmapItem(QGraphicsPixmapItem):
    """Lightweight item — delegates painting to OpenGL. No reflections, just the cover."""
    def __init__(self, pixmap: QPixmap | None, index: int,
                 width: int = 260, height: int = 260):
        super().__init__()
        self._index = index
        self._w = width
        self._h = height
        self._cover_requested = False
        self._cover_failed = False
        self._fade_alpha = 1.0
        self._real_pixmap = None

        if pixmap is None or pixmap.isNull():
            placeholder = _make_placeholder(width, height)
            self.setPixmap(placeholder)
            self._placeholder = placeholder
            self._cover_loaded = False
        else:
            self._real_pixmap = pixmap.scaled(
                width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(self._real_pixmap)
            self._placeholder = None
            self._cover_loaded = True

        self._apply_rounded_clip()

    def _apply_rounded_clip(self):
        path = QPainterPath()
        path.addRoundedRect(0, 0, self._w, self._h, 14, 14)
        self.setClipPath(path)

    @property
    def needs_cover(self) -> bool:
        return not self._cover_loaded and not self._cover_requested and not self._cover_failed

    def mark_cover_requested(self):
        self._cover_requested = True

    def set_real_cover(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            self._cover_failed = True
            return
        self._real_pixmap = pixmap.scaled(
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
        self.setOpacity(value)

    def _on_fade_done(self):
        self.setPixmap(self._real_pixmap)
        self.setOpacity(1.0)
        self._placeholder = None
        self._apply_rounded_clip()


class DropShadow(QGraphicsEllipseItem):
    """Elliptical shadow under each cover — anchors it to the floor."""
    def __init__(self, cover_width: int):
        super().__init__()
        self._cover_w = cover_width
        self.setBrush(QColor(0, 0, 0, 60))
        self.setPen(Qt.NoPen)
        self.setZValue(150)
        self.hide()

    def update_for_state(self, cover_x: float, cover_y: float,
                         cover_scale: float, cover_height: int):
        if cover_scale < 0.5:
            self.hide()
            return
        w = self._cover_w * cover_scale * 0.85
        h = 16 * cover_scale
        x = cover_x - w / 2
        y = cover_y + cover_height * cover_scale / 2
        self.setRect(0, 0, w, h)
        self.setPos(x, y)
        self.show()


class CenterGlow(QGraphicsEllipseItem):
    """Soft halo behind the center cover — guides visual focus."""
    def __init__(self):
        super().__init__()
        g = QRadialGradient(300, 100, 300)
        g.setColorAt(0.0, QColor(255, 255, 255, 18))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        self.setBrush(g)
        self.setPen(Qt.NoPen)
        self.setZValue(500)
        self.setVisible(False)

    def update_for_center(self, center_x: float, center_y: float,
                          cover_w: int, cover_h: int, scale: float):
        if scale < 0.9:
            self.setVisible(False)
            return
        w = cover_w * scale * 1.8
        h = cover_h * scale * 0.6
        self.setRect(0, 0, w, h)
        self.setPos(center_x - w / 2, center_y - h / 2 - cover_h * scale * 0.1)
        self.setVisible(True)


class ReflectiveFloor(QGraphicsRectItem):
    """Dark reflective floor covering the bottom half of the viewport."""
    def __init__(self, viewport_width: int, viewport_height: int):
        super().__init__()
        self._vw = viewport_width
        self._vh = viewport_height
        self.setRect(0, 0, self._vw, self._vh * 0.42)
        self.setPos(0, self._vh * 0.58)
        self.setZValue(100)
        self.setPen(Qt.NoPen)

    def resize(self, viewport_width: int, viewport_height: int):
        self._vw = viewport_width
        self._vh = viewport_height
        self.setRect(0, 0, self._vw, self._vh * 0.42)
        self.setPos(0, self._vh * 0.58)

    def paint(self, painter: QPainter, option, widget):
        grad = QLinearGradient(0, 0, 0, self.rect().height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.15, QColor(0, 0, 0, 40))
        grad.setColorAt(1.0, QColor(0, 0, 0, 200))
        painter.fillRect(self.rect(), grad)


class CoverFlowWidget(QGraphicsView):
    """CoverFlow 3D de alto rendimiento para PySide6.

    Características:
    - Vista de carátulas con perspectiva 3D y rotación en eje Y.
    - Aceleración OpenGL (QOpenGLWidget) con pintado mínimo de CPU.
    - Física de inercia, arrastre con ratón, rueda y teclado.
    - Slider inferior, menú contextual y señales para acciones de álbum.
    - Suelo reflectante, sombras proyectadas e iluminación central.
    - Layout configurable por variables de entorno:
      MICHI_CF_GAP, MICHI_CF_ROT, MICHI_CF_SCALE.
    - Diagnóstico de rendimiento con MICHI_COVERFLOW_DEBUG=1.

    Uso:
        coverflow = CoverFlowWidget()
        coverflow.set_items(lista_de_CoverFlowItem)
        coverflow.show()
    """
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
                self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
                self.setCacheMode(QGraphicsView.CacheBackground)
                self._scene = QGraphicsScene(self)
                self._scene.setItemIndexMethod(QGraphicsScene.NoIndex)
            except Exception:
                self._use_opengl = False

        if not self._use_opengl:
            self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
            self.setCacheMode(QGraphicsView.CacheBackground)
            self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor(9, 11, 17))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)

        self._geometry = {
            "max_rot": 60.0, "center_scale": 1.04, "side_scale": 0.82,
            "far_scale": 0.66, "near_gap_factor": 0.72, "side_gap_factor": 0.32,
            "far_gap_factor": 0.18, "center_y_offset": -38,
        }

        self._items: list[CoverFlowItem] = []
        self._cover_items: list[CoverPixmapItem] = []
        self._shadows: list[DropShadow] = []
        self._floor: ReflectiveFloor | None = None
        self._glow: CenterGlow | None = None
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
        self._friction = 0.92
        self._min_velocity = 0.0015
        self._max_velocity = 0.32
        self._spring_strength = 0.08

        self._phys_timer = QTimer(self)
        self._phys_timer.timeout.connect(self._update_physics)

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

        vw = self.viewport().width() or 800
        vh = self.viewport().height() or 600
        self._floor = ReflectiveFloor(vw, vh)
        self._scene.addItem(self._floor)
        self._glow = CenterGlow()
        self._scene.addItem(self._glow)

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
        for sd in list(self._shadows):
            self._scene.removeItem(sd)
        self._shadows.clear()
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
            ci = CoverPixmapItem(item.pixmap, i, self._cover_w, self._cover_h)
            self._scene.addItem(ci)
            self._cover_items.append(ci)
            shadow = DropShadow(self._cover_w)
            self._scene.addItem(shadow)
            self._shadows.append(shadow)

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
            offset = ci._index - self._current
            state = coverflow_layout(offset, vw, vh, self._cover_w, self._cover_h)
            if not state["visible"]:
                ci.setVisible(False)
                continue
            ci.setVisible(True)
            if self._render_mode == "safe_2d":
                state["rot"] = 0.0
            apply_layout_state(ci, state, self._cover_w, self._cover_h)

            if ci.needs_cover:
                ci.mark_cover_requested()
                item = self._items[ci._index]
                self.request_cover.emit(ci._index, item)

        # Update shadows and center glow
        for i, ci in enumerate(self._cover_items):
            if i < len(self._shadows) and ci.isVisible():
                offset = ci._index - self._current
                state = coverflow_layout(offset, vw, vh, self._cover_w, self._cover_h)
                self._shadows[i].update_for_state(
                    state["x"], state["y"], state["scale"], self._cover_h)
            elif i < len(self._shadows):
                self._shadows[i].hide()

        idx = self.current_index()
        if 0 <= idx < len(self._cover_items):
            ci = self._cover_items[idx]
            state = coverflow_layout(idx - self._current, vw, vh, self._cover_w, self._cover_h)
            self._glow.update_for_center(
                state["x"], state["y"], self._cover_w, self._cover_h, state["scale"])

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
        spring = self._spring_strength
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
            px = center.pixmap()
            if px and not px.isNull():
                w = px.width()
                h = px.height()
                scale = max(rect.width() / w, rect.height() / h) * 1.6
                x = (rect.width() - w * scale) / 2
                y = (rect.height() - h * scale) / 2 - rect.height() * 0.05
                painter.setOpacity(0.18)
                painter.drawPixmap(x, y, w * scale, h * scale, px)

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
        self._floor.resize(self.viewport().width(), self.viewport().height())
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
            ci = CoverPixmapItem(item.pixmap, i, self._cover_w, self._cover_h)
            self._scene.addItem(ci)
            self._cover_items.append(ci)
            shadow = DropShadow(self._cover_w)
            self._scene.addItem(shadow)
            self._shadows.append(shadow)
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
            if isinstance(item, CoverPixmapItem) and hasattr(item, '_index'):
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
                # Zoom disabled — use MICHI_CF_GAP env var instead
                pass

        self._clamp_current_soft()
        self._update_layout()
        self._velocity = 0.0
        self._wheel_snap_timer.start(180)
