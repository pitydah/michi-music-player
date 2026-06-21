"""Mini Player — compact floating window with cover + controls."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
)


class MiniPlayer(QWidget):
    play_clicked = Signal()
    prev_clicked = Signal()
    next_clicked = Signal()
    seek_requested = Signal(float)  # seconds

    def __init__(self, playback, parent=None):
        super().__init__(parent)
        self._playback = playback
        self.setWindowTitle("Astra — Mini reproductor")
        self.setFixedSize(320, 200)
        self.setWindowFlags(
            Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(20,24,34,0.88),
                    stop:1 rgba(12,14,22,0.88)
                );
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(8)

        # Title bar (drag handle)
        title_bar = QHBoxLayout()
        title_lbl = QLabel("Astra")
        title_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 650; color: rgba(255,255,255,0.5);")
        close_btn = QPushButton("\u00d7")
        close_btn.setFixedSize(26, 26)
        close_btn.setFlat(True)
        close_btn.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.35); font-size: 16px;"
            " background: transparent; border: 1px solid transparent;"
            " border-radius: 8px; }"
            "QPushButton:hover { color: #FF3C48;"
            " background: rgba(255,60,72,0.12); }")
        close_btn.clicked.connect(self.hide)
        title_bar.addWidget(title_lbl)
        title_bar.addStretch()
        title_bar.addWidget(close_btn)
        main.addLayout(title_bar)

        # Cover + info row
        info_row = QHBoxLayout()
        info_row.setSpacing(10)

        self._cover = QLabel()
        self._cover.setFixedSize(56, 56)
        self._cover.setStyleSheet(
            "background: rgba(255,255,255,0.06); border-radius: 10px;"
            "border: 1px solid rgba(255,255,255,0.08);")
        self._cover.setAlignment(Qt.AlignCenter)
        info_row.addWidget(self._cover)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title_lbl = QLabel("Sin reproducción")
        self._title_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 650; color: rgba(255,255,255,0.95);")
        self._artist_lbl = QLabel("")
        self._artist_lbl.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.55);")
        text_col.addWidget(self._title_lbl)
        text_col.addWidget(self._artist_lbl)
        text_col.addStretch()
        info_row.addLayout(text_col, 1)
        main.addLayout(info_row)

        # Progress bar
        self._seek = QSlider(Qt.Horizontal)
        self._seek.setRange(0, 1000)
        self._seek.setFixedHeight(20)
        self._seek.sliderPressed.connect(lambda: setattr(self, '_tracking', True))
        self._seek.sliderReleased.connect(self._on_seek_release)
        self._seek.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 3px; background: rgba(255,255,255,0.07); border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF7A00, stop:0.5 #FF243D,
                    stop:0.8 #D00073, stop:1 #6B1B8F
                );
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 9px; height: 9px; margin: -3px -4px; border-radius: 5px;
                background: #FFFFFF;
            }
        """)
        main.addWidget(self._seek)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.setAlignment(Qt.AlignCenter)
        ctrl.setSpacing(16)

        def _make_small_btn(icon_name, sz):
            from ui.icons import get_icon
            ipath = get_icon(icon_name)
            btn = QPushButton(QIcon(ipath) if ipath else QIcon(), "")
            btn.setFlat(True)
            btn.setIconSize(QSize(sz, sz))
            btn.setFixedSize(sz + 12, sz + 12)
            btn.setStyleSheet(
                "QPushButton { background: transparent;"
                " border: 1px solid transparent; border-radius: 9px; }"
                "QPushButton:hover { background: rgba(255,255,255,0.07);"
                " border: 1px solid rgba(255,255,255,0.09); }")
            return btn

        prev = _make_small_btn("warm_prev", 18)
        prev.clicked.connect(self.prev_clicked.emit)
        self._play_btn = _make_small_btn("warm_play", 22)
        self._play_btn.clicked.connect(self.play_clicked.emit)
        next_btn = _make_small_btn("warm_next", 18)
        next_btn.clicked.connect(self.next_clicked.emit)

        ctrl.addStretch()
        ctrl.addWidget(prev)
        ctrl.addWidget(self._play_btn)
        ctrl.addWidget(next_btn)
        ctrl.addStretch()
        main.addLayout(ctrl)

        # Position tracking
        self._tracking = False
        self._duration = 0.0

    def _on_seek_release(self):
        self._tracking = False
        if self._duration > 0:
            seconds = self._seek.value() / 1000.0 * self._duration
            self.seek_requested.emit(seconds)

    def set_track(self, title: str, artist: str = "", cover_path: str = ""):
        self._title_lbl.setText(title or "Sin reproducción")
        self._artist_lbl.setText(artist or "")
        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                self._cover.setPixmap(
                    pix.scaled(52, 52, Qt.KeepAspectRatio,
                              Qt.SmoothTransformation))

    def set_state(self, state: str):
        name = "warm_pause" if state == "playing" else "warm_play"
        from ui.icons import get_icon
        self._play_btn.setIcon(QIcon(get_icon(name)))

    def set_position(self, seconds: float, duration: float):
        self._duration = duration
        if not self._tracking and duration > 0:
            self._seek.setValue(int(seconds / duration * 1000))

    def mousePressEvent(self, event):
        self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos'):
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
