"""NowPlayingBar — bottom bar with cover, info, seek, controls, volume."""

import os

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton,
    QSlider, QLabel, QMenu, QSizePolicy, QGraphicsDropShadowEffect,
)

from ui.icons import get_icon
from ui.player_icon_button import PlayerIconButton

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


def _make_btn(icon_name: str, icon_size: int, button_size: int | None = None) -> PlayerIconButton:
    final_size = button_size or icon_size + 10
    return PlayerIconButton(
        icon_name=icon_name,
        button_size=final_size,
        icon_size=icon_size,
        primary=(icon_name in ("warm_play", "warm_pause")),
    )


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
    cover_loaded = Signal(object)  # emits QPixmap of album art

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "stopped"
        self._seeking = False
        self._duration = 0.0
        self._shuffle = False
        self._repeat = "none"
        self.setObjectName("nowplayingBar")
        self.setFixedHeight(112)

        self.setAutoFillBackground(True)

        from ui.theme import is_dark_mode
        self._dark_mode = is_dark_mode()
        if self._dark_mode:
            self._bg_rgba = "rgba(48, 52, 64, 242)"
            self._text_color = "rgba(255,255,255,0.98)"
            self._text_sec = "rgba(245,245,247,0.74)"
            self._accent = "#ffffff"
            self._border = "rgba(255,255,255,0.14)"
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
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(24)

        # ═══ LEFT: COVER + TITLE/ARTIST (stretch=0) ═══
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self._cover = QPushButton()
        self._cover.setFlat(True)
        self._cover.setFixedSize(48, 48)
        self._cover.setStyleSheet("""
            QPushButton {
                background: #2a2a2e;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                border: 1px solid rgba(255,255,255,0.2);
            }
        """)
        self._cover.clicked.connect(self.cover_clicked.emit)
        self._cover.setIcon(QIcon(get_icon("play")))
        self._cover.setIconSize(QSize(44, 44))
        self._cover_pixmap = QPixmap()
        left_layout.addWidget(self._cover)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        self._title_lbl = QLabel("Sin reproducción")
        self._title_lbl.setObjectName("titleLabel")
        self._title_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {self._text_color};")
        self._artist_lbl = QLabel("Añade música")
        self._artist_lbl.setObjectName("artistLabel")
        self._artist_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 400; color: {self._text_sec};")
        text_layout.addWidget(self._title_lbl)
        text_layout.addWidget(self._artist_lbl)
        left_layout.addLayout(text_layout)

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
            f"color: {self._text_sec}; font-size: 10px; font-weight: 500;")
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
            f"color: {self._text_sec}; font-size: 10px; font-weight: 500;")
        self._dur_lbl.setFixedWidth(32)

        seek_row.addWidget(self._time_lbl)
        seek_row.addWidget(self._seek)
        seek_row.addWidget(self._dur_lbl)

        # Controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(16)
        ctrl_row.setAlignment(Qt.AlignCenter)

        self._shuffle_btn = _make_btn("warm_shuffle", 22, 42)
        self._prev_btn = _make_btn("warm_prev", 28, 48)
        self._play_btn = _make_btn("warm_play", 34, 58)
        self._next_btn = _make_btn("warm_next", 28, 48)
        self._repeat_btn = _make_btn("warm_repeat", 22, 42)

        self._shuffle_btn.clicked.connect(self._on_shuffle)
        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._play_btn.clicked.connect(self.play_clicked.emit)
        self._next_btn.clicked.connect(self.next_clicked.emit)
        self._repeat_btn.clicked.connect(self._on_repeat)

        ctrl_row.addWidget(self._shuffle_btn)
        ctrl_row.addWidget(self._prev_btn)
        ctrl_row.addWidget(self._play_btn)
        ctrl_row.addWidget(self._next_btn)
        ctrl_row.addWidget(self._repeat_btn)

        center_layout.addLayout(seek_row)
        center_layout.addLayout(ctrl_row)
        layout.addWidget(center_widget, 1)

        # ═══ RIGHT: VOLUME + BADGE + EQ + TRANSMIT (stretch=0) ═══
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(right_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        # Widgets
        self._vol_btn = _make_btn("warm_vol_high", 25, 40)

        self._vol = QSlider(Qt.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(70)
        self._vol.setFixedWidth(80)
        self._vol.setFixedHeight(26)
        self._vol.setStyleSheet(VOLUME_STYLESHEET)
        self._vol.valueChanged.connect(lambda v: self.volume_changed.emit(v))

        self._eq_btn = _make_btn("warm_eq", 26, 46)
        self._eq_btn.clicked.connect(self.eq_clicked.emit)

        self._transmit_btn = _make_btn("warm_transmit", 26, 46)
        self._transmit_btn.setToolTip("Transmitir a dispositivo")
        self._transmit_btn.clicked.connect(lambda: self.transmit_clicked.emit())

        self._quality_badge = QLabel("")
        self._quality_badge.setAlignment(Qt.AlignCenter)
        self._quality_badge.setWordWrap(False)
        self._quality_badge.setMinimumWidth(90)
        self._quality_badge.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self._quality_badge.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,0.07);
                color: #FF9A3D;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 550;
            }
        """)

        # Row 0
        grid.addWidget(self._vol_btn, 0, 1, Qt.AlignVCenter)
        grid.addWidget(self._vol, 0, 2, Qt.AlignVCenter)

        tight = QHBoxLayout()
        tight.setSpacing(2)
        tight.setContentsMargins(0, 0, 0, 0)
        tight.addWidget(self._eq_btn)
        tight.addWidget(self._transmit_btn)
        grid.addLayout(tight, 0, 3, Qt.AlignVCenter)

        # Row 1 — badge under slider
        grid.addWidget(self._quality_badge, 1, 2, Qt.AlignHCenter | Qt.AlignVCenter)

        # Column stretches for centering
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(4, 1)

        layout.addWidget(right_widget, 0)

        # ═══ GLASSMORPHISM + SOMBRA ═══
        self.setStyleSheet(f"""
            QWidget#nowplayingBar {{
                background: {self._bg_rgba};
                border-radius: 16px;
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
        self._shuffle_btn.set_active(self._shuffle)
        self.shuffle_clicked.emit()

    def _on_repeat(self):
        modes = {"none": "all", "all": "one", "one": "none"}
        self._repeat = modes.get(self._repeat, "none")
        self._repeat_btn.set_active(self._repeat != "none")
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
        self._play_btn.set_icon_name(
            "warm_pause" if state == "playing" else "warm_play")

    def set_track(self, title: str, artist: str, cover_path: str = ""):
        self._title_lbl.setText(title or "Sin reproducción")
        if artist:
            artist = artist.split(" · ")[0]
        self._artist_lbl.setText(artist or "Sin información")
        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                self._cover_pixmap = pix.scaled(
                    48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._cover.setIcon(QIcon(self._cover_pixmap))
                self.cover_loaded.emit(self._cover_pixmap)
            else:
                self.cover_loaded.emit(None)
        else:
            self.cover_loaded.emit(None)

    def set_position(self, seconds: float):
        if self._seeking or self._duration <= 0:
            return
        self._time_lbl.setText(_fmt(seconds))
        self._seek.setValue(int(seconds / self._duration * 1000))

    def set_duration(self, seconds: float):
        if seconds > 0:
            self._duration = seconds
            self._dur_lbl.setText(_fmt(seconds))

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
        self._vol_btn.set_icon_name(name)

    def set_quality(self, text: str):
        self._quality_badge.setText(f" {text} ") if text else self._quality_badge.clear()

def _fmt(t: float) -> str:
    t = int(t)
    if t < 3600:
        return f"{t // 60}:{t % 60:02d}"
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"
