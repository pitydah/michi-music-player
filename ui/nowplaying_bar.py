"""NowPlayingBar — bottom bar with cover, info, seek, controls, volume."""

import os

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton,
    QSlider, QLabel, QMenu, QSizePolicy, QGraphicsDropShadowEffect,
)

from ui.icons import get_icon

SEEK_STYLESHEET = """
QSlider::groove:horizontal {
    height: 6px;
    border-radius: 3px;
    background: #3B3F47;
}
QSlider::sub-page:horizontal {
    height: 6px;
    border-radius: 3px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #FF7A00,
        stop:0.38 #FF243D,
        stop:0.72 #D00073,
        stop:1 #6B1B8F
    );
}
QSlider::add-page:horizontal {
    height: 6px;
    border-radius: 3px;
    background: #3B3F47;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 3px solid #FFFFFF;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #FF7A00,
        stop:0.5 #FF243D,
        stop:1 #B0007A
    );
}
"""

VOLUME_STYLESHEET = """
QSlider::groove:horizontal {
    height: 4px;
    border-radius: 2px;
    background: #3B3F47;
}
QSlider::sub-page:horizontal {
    height: 4px;
    border-radius: 2px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #FF7A00,
        stop:0.38 #FF243D,
        stop:0.72 #D00073,
        stop:1 #6B1B8F
    );
}
QSlider::add-page:horizontal {
    height: 4px;
    border-radius: 2px;
    background: #3B3F47;
}
QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 2px solid #FFFFFF;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #FF7A00,
        stop:0.5 #FF243D,
        stop:1 #B0007A
    );
}
"""


def _make_btn(icon_name: str, icon_size: int, button_size: int | None = None) -> QPushButton:
    btn = QPushButton("")
    btn.setFlat(True)

    icon_path = get_icon(icon_name)
    if icon_path:
        btn.setIcon(QIcon(icon_path))

    btn.setIconSize(QSize(icon_size, icon_size))

    final_size = button_size or icon_size + 10
    btn.setFixedSize(final_size, final_size)
    btn.setMinimumSize(final_size, final_size)
    btn.setMaximumSize(final_size, final_size)

    btn.setCursor(Qt.PointingHandCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    btn.setAutoDefault(False)
    btn.setDefault(False)

    btn.setStyleSheet("""
        QPushButton {
            background: transparent;
            border: none;
            outline: none;
            padding: 0px;
            margin: 0px;
            border-radius: 11px;
        }
        QPushButton:focus {
            outline: none;
            border: none;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.055);
        }
        QPushButton:pressed {
            background: rgba(255,255,255,0.095);
        }
        QPushButton[active="true"] {
            background: rgba(255,255,255,0.11);
            border: none;
        }
    """)
    return btn


def _set_button_active(btn: QPushButton, active: bool):
    btn.setProperty("active", active)
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    btn.update()


def _rounded_cover_pixmap(src: QPixmap, size: int = 76, radius: int = 16) -> QPixmap:
    """Scale and round-crop a cover pixmap."""
    result = QPixmap(size, size)
    result.fill(Qt.transparent)

    if src.isNull():
        return result

    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing, True)

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)

    scaled = src.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation)
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    painter.drawPixmap(-x, -y, scaled)
    painter.end()

    return result


def _placeholder_cover_pixmap(size: int = 76, radius: int = 16) -> QPixmap:
    """Premium placeholder cover art."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor(62, 66, 80))
    grad.setColorAt(1.0, QColor(42, 46, 58))
    painter.setBrush(grad)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)

    # Subtle accent glow
    glow = QRadialGradient(size * 0.65, size * 0.3, size * 0.7)
    glow.setColorAt(0.0, QColor(255, 122, 0, 38))
    glow.setColorAt(1.0, QColor(255, 77, 46, 0))
    painter.setBrush(glow)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)

    # Musical note
    pen = QPen(QColor(255, 255, 255, 55), 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    cx, cy = size / 2, size / 2
    painter.drawLine(int(cx + 4), int(cy - 8), int(cx + 4), int(cy + 8))
    painter.drawLine(int(cx + 4), int(cy - 8), int(cx + 12), int(cy - 5))
    painter.setBrush(QColor(255, 255, 255, 55))
    painter.drawEllipse(int(cx - 6), int(cy + 4), 9, 8)

    painter.end()

    # Border
    painter2 = QPainter(pix)
    painter2.setRenderHint(QPainter.Antialiasing, True)
    painter2.setPen(QPen(QColor(255, 255, 255, 25), 1))
    painter2.setBrush(Qt.NoBrush)
    painter2.drawRoundedRect(0.5, 0.5, size - 1, size - 1, radius, radius)
    painter2.end()

    return pix


class NowPlayingBar(QWidget):
    play_clicked = Signal()
    prev_clicked = Signal()
    next_clicked = Signal()
    shuffle_clicked = Signal()
    repeat_clicked = Signal()
    seek_requested = Signal(float)
    volume_changed = Signal(int)
    eq_clicked = Signal()
    cover_clicked = Signal()
    transmit_clicked = Signal()
    audio_output_clicked = Signal()
    mini_player_clicked = Signal()
    cover_loaded = Signal(object)  # emits QPixmap of album art

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "stopped"
        self._seeking = False
        self._duration = 0.0
        self._shuffle = False
        self._repeat = "none"
        self.setObjectName("nowplayingBar")
        self.setFixedHeight(116)

        self.setAutoFillBackground(True)

        from ui.theme import is_dark_mode
        self._dark_mode = is_dark_mode()
        if self._dark_mode:
            self._bg_rgba = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                " stop:0 rgba(10,12,18,0.98),"
                " stop:0.55 rgba(7,9,14,0.98),"
                " stop:1 rgba(14,10,16,0.98))")
            self._text_color = "rgba(255,255,255,0.98)"
            self._text_sec = "rgba(245,245,247,0.74)"
            self._accent = "#ffffff"
            self._border = "rgba(255,255,255,0.08)"
            self._shadow_alpha = 110
        else:
            self._bg_rgba = "rgba(245, 245, 247, 220)"
            self._text_color = "#1c1c1e"
            self._text_sec = "rgba(28,28,30,0.6)"
            self._accent = "#FF7A00"
            self._border = "rgba(0,0,0,0.06)"
            self._shadow_alpha = 30

        # ─── 3-COLUMN LAYOUT: left(0) | center(1) | right(0) ───
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 8, 16, 8)
        layout.setSpacing(24)

        # ═══ LEFT: NOW PLAYING INFO CARD ═══
        self._cover_pixmap = QPixmap()
        self._raw_title = ""
        self._raw_artist = ""
        self._raw_meta = ""

        left_widget = QWidget()
        left_widget.setObjectName("nowPlayingInfoCard")
        left_widget.setFixedWidth(270)
        left_widget.setFixedHeight(86)
        left_widget.setStyleSheet("""
            QWidget#nowPlayingInfoCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(64,68,80,0.92),
                    stop:0.55 rgba(45,49,60,0.92),
                    stop:1 rgba(20,22,30,0.95)
                );
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 16px;
            }
        """)
        left_widget.setCursor(Qt.PointingHandCursor)
        left_widget.mousePressEvent = lambda e: self.cover_clicked.emit()

        card_shadow = QGraphicsDropShadowEffect(left_widget)
        card_shadow.setBlurRadius(20)
        card_shadow.setXOffset(0)
        card_shadow.setYOffset(4)
        card_shadow.setColor(QColor(0, 0, 0, 55))
        left_widget.setGraphicsEffect(card_shadow)

        card_layout = QHBoxLayout(left_widget)
        card_layout.setContentsMargins(12, 8, 14, 8)
        card_layout.setSpacing(14)

        # Cover button
        self._cover = QPushButton()
        self._cover.setObjectName("coverButton")
        self._cover.setFixedSize(64, 64)
        self._cover.setIconSize(QSize(64, 64))
        self._cover.setCursor(Qt.PointingHandCursor)
        self._cover.setFlat(True)
        self._cover.setStyleSheet("""
            QPushButton#coverButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 13px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#coverButton:hover {
                border: 1px solid rgba(255,122,0,0.38);
            }
        """)
        self._cover.clicked.connect(self.cover_clicked.emit)
        self._cover.setIcon(QIcon(_placeholder_cover_pixmap(64, 13)))
        card_layout.addWidget(self._cover, 0, Qt.AlignVCenter)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        text_layout.addStretch(1)

        self._title_lbl = QLabel("Sin reproducción")
        self._title_lbl.setObjectName("nowPlayingTitle")
        self._title_lbl.setStyleSheet(
            "QLabel#nowPlayingTitle {"
            "  font-size: 14px; font-weight: 700;"
            "  color: #FFFFFF;"
            "  background: transparent; border: none;"
            "}")
        text_layout.addWidget(self._title_lbl)

        self._artist_lbl = QLabel("Añade música")
        self._artist_lbl.setObjectName("nowPlayingArtist")
        self._artist_lbl.setStyleSheet(
            "QLabel#nowPlayingArtist {"
            "  font-size: 12px; font-weight: 540;"
            "  color: rgba(255,255,255,0.92);"
            "  background: transparent; border: none;"
            "}")
        text_layout.addWidget(self._artist_lbl)

        self._meta_lbl = QLabel("Astra Music Player")
        self._meta_lbl.setObjectName("nowPlayingMeta")
        self._meta_lbl.setStyleSheet(
            "QLabel#nowPlayingMeta {"
            "  font-size: 10.5px; font-weight: 500;"
            "  color: rgba(255,255,255,0.76);"
            "  background: transparent; border: none;"
            "}")
        text_layout.addWidget(self._meta_lbl)

        text_layout.addStretch(1)
        card_layout.addLayout(text_layout, 1)

        layout.addWidget(left_widget, 0)

        # ═══ CENTER: SEEK + CONTROLS (stretch=1) ═══
        center_widget = QWidget()
        center_widget.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        # Seek row
        seek_row = QHBoxLayout()
        seek_row.setSpacing(6)
        seek_row.setContentsMargins(0, 0, 0, 0)

        self._time_lbl = QLabel("0:00")
        self._time_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.86); font-size: 10px; font-weight: 600;")
        self._time_lbl.setFixedWidth(32)

        self._seek = QSlider(Qt.Horizontal)
        self._seek.setRange(0, 1000)
        self._seek.setMinimumWidth(150)
        self._seek.setFixedHeight(28)
        self._seek.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._seek.setStyleSheet(SEEK_STYLESHEET)
        self._seek.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self._seek.sliderReleased.connect(self._on_seek_end)
        self._seek.sliderMoved.connect(self._on_seek_drag)

        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.86); font-size: 10px; font-weight: 600;")
        self._dur_lbl.setFixedWidth(32)

        seek_row.addWidget(self._time_lbl)
        seek_row.addWidget(self._seek)
        seek_row.addWidget(self._dur_lbl)

        # Controls row — playback | utility in one horizontal band
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)
        ctrl_row.setAlignment(Qt.AlignCenter)

        self._shuffle_btn = _make_btn("warm_shuffle", 20, 40)
        self._prev_btn = _make_btn("warm_prev", 26, 44)
        self._play_btn = _make_btn("warm_play", 34, 54)
        self._next_btn = _make_btn("warm_next", 26, 44)
        self._repeat_btn = _make_btn("warm_repeat", 20, 40)

        self._shuffle_btn.clicked.connect(self._on_shuffle)
        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._play_btn.clicked.connect(self.play_clicked.emit)
        self._next_btn.clicked.connect(self.next_clicked.emit)
        self._repeat_btn.clicked.connect(self._on_repeat)

        self._audio_output_btn = _make_btn("warm_audio_source", 22, 40)
        self._audio_output_btn.setToolTip("Seleccionar salida de audio")
        self._audio_output_btn.clicked.connect(self.audio_output_clicked.emit)

        self._mini_player_btn = _make_btn("warm_mini_player", 22, 40)
        self._mini_player_btn.setToolTip("Abrir mini reproductor")
        self._mini_player_btn.clicked.connect(self.mini_player_clicked.emit)

        ctrl_row.addWidget(self._shuffle_btn)
        ctrl_row.addWidget(self._prev_btn)
        ctrl_row.addWidget(self._play_btn)
        ctrl_row.addWidget(self._next_btn)
        ctrl_row.addWidget(self._repeat_btn)

        utility_controls = QHBoxLayout()
        utility_controls.setContentsMargins(0, -2, 0, 0)
        utility_controls.setSpacing(10)
        utility_controls.addStretch()
        utility_controls.addWidget(self._audio_output_btn)
        utility_controls.addWidget(self._mini_player_btn)
        utility_controls.addSpacing(32)

        # Mirror seek_row: 32px | stretch(controls) | utility | 32px
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(0)
        controls_row.addSpacing(32)
        controls_row.addLayout(ctrl_row, 1)
        controls_row.addLayout(utility_controls, 0)

        center_layout.addLayout(seek_row)
        center_layout.addLayout(controls_row)
        layout.addWidget(center_widget, 1)

        # ═══ RIGHT: VOLUME + TOOLS + BADGE (stretch=0) ═══

        # Widgets
        self._vol_btn = _make_btn("warm_vol_high", 22, 38)

        self._vol = QSlider(Qt.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(70)
        self._vol.setFixedWidth(80)
        self._vol.setFixedHeight(28)
        self._vol.setStyleSheet(VOLUME_STYLESHEET)
        self._vol.valueChanged.connect(lambda v: self.volume_changed.emit(v))

        self._eq_btn = _make_btn("warm_eq", 26, 44)
        self._eq_btn.setToolTip("Ecualizador")
        self._eq_btn.clicked.connect(self.eq_clicked.emit)

        self._transmit_btn = _make_btn("warm_transmit", 28, 44)
        self._transmit_btn.setToolTip("Transmitir a dispositivo")
        self._transmit_btn.clicked.connect(lambda: self.transmit_clicked.emit())

        self._quality_badge = QLabel("")
        self._quality_badge.setAlignment(Qt.AlignCenter)
        self._quality_badge.setWordWrap(False)
        self._quality_badge.setMinimumWidth(88)
        self._quality_badge.setFixedHeight(22)
        self._quality_badge.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self._quality_badge.setStyleSheet("""
            QLabel {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,0.085),
                    stop:0.55 rgba(255,255,255,0.045),
                    stop:1 rgba(255,122,0,0.075)
                );
                color: rgba(255,255,255,0.92);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 9px;
                padding: 3px 10px;
                font-size: 10.5px;
                font-weight: 650;
                letter-spacing: 0.2px;
            }
        """)

        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)

        # Row 0 — controls row
        right_controls = QHBoxLayout()
        right_controls.setContentsMargins(0, 0, 0, 0)
        right_controls.setSpacing(8)
        right_controls.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        right_controls.addStretch()
        right_controls.addWidget(self._vol_btn)
        right_controls.addWidget(self._vol)
        right_controls.addSpacing(6)
        right_controls.addWidget(self._eq_btn)
        right_controls.addWidget(self._transmit_btn)

        right_layout.addLayout(right_controls)

        # Row 1 — badge under volume slider
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.addStretch()
        badge_row.addWidget(self._quality_badge)
        badge_row.addSpacing(94)
        right_layout.addLayout(badge_row)

        layout.addWidget(right_widget, 0)

        # ═══ GLASSMORPHISM + SOMBRA ═══
        self.setStyleSheet(f"""
            QWidget#nowplayingBar {{
                background: {self._bg_rgba};
                border-radius: 18px;
                border: 1px solid {self._border};
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, self._shadow_alpha))
        self.setGraphicsEffect(shadow)

    def _on_shuffle(self):
        self._shuffle = not self._shuffle
        _set_button_active(self._shuffle_btn, self._shuffle)
        self.shuffle_clicked.emit()

    def _on_repeat(self):
        modes = {"none": "all", "all": "one", "one": "none"}
        self._repeat = modes.get(self._repeat, "none")
        _set_button_active(self._repeat_btn, self._repeat != "none")
        self.repeat_clicked.emit()

    def _on_seek_end(self):
        self._seeking = False
        if self._duration > 0:
            self.seek_requested.emit(
                self._seek.value() / 1000.0 * self._duration)

    def _on_seek_drag(self, v):
        if self._duration > 0:
            self._time_lbl.setText(_fmt(v / 1000.0 * self._duration))

    # ── Public API ──

    def set_state(self, state: str):
        self._state = state
        name = "warm_pause" if state == "playing" else "warm_play"
        self._play_btn.setIcon(QIcon(get_icon(name)))
        self._play_btn.setIconSize(QSize(34, 34))

    def set_track(self, title: str, artist: str, cover_path: str = ""):
        self._raw_title = title or "Sin reproducción"
        self._raw_artist = artist or "Añade música"
        self._raw_meta = "Astra Music Player"

        # Split artist/album if combined
        if " · " in self._raw_artist:
            parts = self._raw_artist.split(" · ")
            self._raw_artist = parts[0]
            if len(parts) > 1:
                self._raw_meta = parts[1]

        self._title_lbl.setText(self._raw_title)
        self._artist_lbl.setText(self._raw_artist)
        self._meta_lbl.setText(self._raw_meta)

        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                rounded = _rounded_cover_pixmap(pix, 64, 13)
                self._cover_pixmap = rounded
                self._cover.setIcon(QIcon(rounded))
                self.cover_loaded.emit(pix)
            else:
                self._cover.setIcon(QIcon(_placeholder_cover_pixmap(64, 13)))
                self.cover_loaded.emit(None)
        else:
            self._cover.setIcon(QIcon(_placeholder_cover_pixmap(64, 13)))
            self.cover_loaded.emit(None)

        self._apply_elide()

    def set_position(self, seconds: float):
        if self._seeking or self._duration <= 0:
            return
        self._time_lbl.setText(_fmt(seconds))
        self._seek.setValue(int(seconds / self._duration * 1000))

    def set_duration(self, seconds: float):
        self._duration = seconds
        self._dur_lbl.setText(_fmt(seconds))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self):
        """Apply text elision to prevent overflow."""
        w = self.width()
        # Estimate available width for text (left card is ~300-410px of bar)
        avail = max(80, w - 580)
        fm = self._title_lbl.fontMetrics()
        self._title_lbl.setText(
            fm.elidedText(self._raw_title, Qt.ElideRight, avail))
        fm2 = self._artist_lbl.fontMetrics()
        self._artist_lbl.setText(
            fm2.elidedText(self._raw_artist, Qt.ElideRight, avail))
        fm3 = self._meta_lbl.fontMetrics()
        self._meta_lbl.setText(
            fm3.elidedText(self._raw_meta, Qt.ElideRight, avail))

    def set_volume(self, vol: int):
        self._vol.blockSignals(True)
        self._vol.setValue(vol)
        self._vol.blockSignals(False)
        if vol <= 0:
            name = "warm_mute"
        elif vol <= 33:
            name = "warm_vol_low"
        elif vol <= 66:
            name = "warm_vol_medium"
        else:
            name = "warm_vol_high"
        self._vol_btn.setIcon(QIcon(get_icon(name)))
        self._vol_btn.setIconSize(QSize(22, 22))

    def set_quality(self, text: str):
        self._quality_badge.setText(f" {text} " if text else " LOCAL ")

def _fmt(t: float) -> str:
    t = int(t)
    if t < 3600:
        return f"{t // 60}:{t % 60:02d}"
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"
