"""Expanded NowPlaying view — full-screen cover art with controls and queue."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QListWidget, QListWidgetItem, QFrame, QMenu, QAbstractItemView,
)

from ui.icons import get_icon
from ui.adaptive_artwork_background import AdaptiveArtworkBackground
from ui.lyrics_widget import LyricsWidget


def _make_btn(icon_name: str, size: int) -> QPushButton:
    btn = QPushButton(QIcon(get_icon(icon_name)), "")
    btn.setFlat(True)
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size + 14, size + 14)
    return btn


class ExpandedNowPlaying(QWidget):
    go_back = Signal()
    play_clicked = Signal()
    prev_clicked = Signal()
    next_clicked = Signal()
    seek_requested = Signal(float)
    volume_changed = Signal(int)
    track_from_queue = Signal(str)  # filepath
    add_to_playlist = Signal(str)
    queue_reordered = Signal(list)   # list of filepaths

    eq_requested = Signal()
    file_info_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "stopped"
        self._seeking = False
        self._duration = 0.0
        self._setting_queue = False

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Background — sits behind everything
        self._artwork_bg = AdaptiveArtworkBackground(self)
        self._artwork_bg.lower()

        # ── Header ──
        header = QHBoxLayout()
        header.setContentsMargins(16, 12, 16, 12)
        self._back_btn = QPushButton("Cerrar vista expandida")
        self._back_btn.setFlat(True)
        self._back_btn.setStyleSheet(
            "QPushButton { color: rgba(245,245,247,0.7); font-size: 13px; }"
            "QPushButton:hover { color: #8FB7FF; }")
        self._back_btn.clicked.connect(self.go_back.emit)
        self._menu_btn = _make_btn("menu", 18)
        self._menu_btn.clicked.connect(self._show_menu)
        header.addWidget(self._back_btn)
        header.addStretch()
        header.addWidget(self._menu_btn)
        main.addLayout(header)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.07);")
        main.addWidget(sep)

        # ── Scrollable body ──
        body = QVBoxLayout()
        body.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        body.setSpacing(8)
        body.setContentsMargins(32, 24, 32, 24)

        # Cover art
        self._cover = QLabel()
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setFixedSize(310, 310)
        self._cover.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.04); border-radius: 12px; }")
        body.addWidget(self._cover, alignment=Qt.AlignCenter)

        body.addSpacing(16)

        # Title
        self._title = QLabel("")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("font-size: 22px; font-weight: bold; color: rgba(245,245,247,0.95);")
        self._title.setWordWrap(True)
        body.addWidget(self._title)

        # Artist / Album
        self._subtitle = QLabel("")
        self._subtitle.setAlignment(Qt.AlignCenter)
        self._subtitle.setStyleSheet("font-size: 14px; color: rgba(245,245,247,0.56);")
        body.addWidget(self._subtitle)

        # Quality badge
        self._quality = QLabel("")
        self._quality.setAlignment(Qt.AlignCenter)
        self._quality.setStyleSheet("font-size: 11px; color: #8FB7FF; font-weight: 500;")
        body.addWidget(self._quality)

        body.addSpacing(16)

        # Seek bar
        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)
        self._time_lbl = QLabel("0:00")
        self._time_lbl.setStyleSheet("font-size: 10px; color: rgba(245,245,247,0.56);")
        self._seek = QSlider(Qt.Horizontal)
        self._seek.setRange(0, 1000)
        self._seek.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self._seek.sliderReleased.connect(self._on_seek_end)
        self._seek.sliderMoved.connect(self._on_seek_drag)
        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setStyleSheet("font-size: 10px; color: rgba(245,245,247,0.56);")
        seek_row.addWidget(self._time_lbl)
        seek_row.addWidget(self._seek)
        seek_row.addWidget(self._dur_lbl)
        body.addLayout(seek_row)

        body.addSpacing(8)

        # Controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setAlignment(Qt.AlignCenter)
        ctrl_row.setSpacing(10)
        self._shuffle_btn = _make_btn("shuffle", 20)
        self._prev_btn = _make_btn("prev", 28)
        self._play_btn = _make_btn("play", 36)
        self._next_btn = _make_btn("next", 28)
        self._repeat_btn = _make_btn("repeat", 20)

        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._play_btn.clicked.connect(self._on_play)
        self._next_btn.clicked.connect(self.next_clicked.emit)

        ctrl_row.addWidget(self._shuffle_btn)
        ctrl_row.addSpacing(8)
        ctrl_row.addWidget(self._prev_btn)
        ctrl_row.addWidget(self._play_btn)
        ctrl_row.addWidget(self._next_btn)
        ctrl_row.addSpacing(8)
        ctrl_row.addWidget(self._repeat_btn)
        body.addLayout(ctrl_row)

        # Volume
        vol_row = QHBoxLayout()
        vol_row.setAlignment(Qt.AlignCenter)
        vol_row.setSpacing(6)
        vol_icon = QLabel()
        vol_icon.setPixmap(QIcon(get_icon("volume_high")).pixmap(16, 16))
        self._vol = QSlider(Qt.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(70)
        self._vol.setFixedWidth(140)
        self._vol.valueChanged.connect(lambda v: self.volume_changed.emit(v))
        vol_row.addStretch()
        vol_row.addWidget(vol_icon)
        vol_row.addWidget(self._vol)
        vol_row.addStretch()
        body.addLayout(vol_row)

        body.addSpacing(12)

        # Action buttons
        act_row = QHBoxLayout()
        act_row.setAlignment(Qt.AlignCenter)
        act_row.setSpacing(24)
        fav_btn = QPushButton("♡ Favorito")
        fav_btn.setFlat(True)
        fav_btn.setStyleSheet("QPushButton { color: rgba(245,245,247,0.56); } QPushButton:hover { color: #8FB7FF; }")
        dl_btn = QPushButton("⤓ Descargar")
        dl_btn.setFlat(True)
        dl_btn.setStyleSheet("QPushButton { color: rgba(245,245,247,0.56); } QPushButton:hover { color: #8FB7FF; }")
        act_row.addWidget(fav_btn)
        act_row.addWidget(dl_btn)
        body.addLayout(act_row)

        body.addSpacing(12)

        # ── Synced Lyrics ──
        self._lyrics = LyricsWidget(self)
        self._lyrics.setFixedHeight(240)
        body.addWidget(self._lyrics)

        main.addLayout(body)

        # ── Separator ──
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: rgba(255,255,255,0.07);")
        main.addWidget(sep2)

        # ── Queue ──
        qh = QHBoxLayout()
        qh.setContentsMargins(16, 8, 16, 4)
        self._queue_label = QLabel("Cola (0 canciones)")
        self._queue_label.setStyleSheet("font-size: 12px; color: rgba(245,245,247,0.56); font-weight: 600;")
        clear_btn = QPushButton("Limpiar")
        clear_btn.setFlat(True)
        clear_btn.setStyleSheet("QPushButton { color: rgba(245,245,247,0.56); font-size: 11px; }")
        qh.addWidget(self._queue_label)
        qh.addStretch()
        qh.addWidget(clear_btn)
        main.addLayout(qh)

        self._queue_list = QListWidget()
        self._queue_list.setFrameShape(QFrame.NoFrame)
        self._queue_list.setDragDropMode(QAbstractItemView.InternalMove)
        self._queue_list.setDefaultDropAction(Qt.MoveAction)
        self._queue_list.model().rowsMoved.connect(self._on_queue_reorder)
        self._queue_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,0.06); }
            QListWidget::item:hover { background: rgba(143,183,255,0.06); }
        """)
        self._queue_list.doubleClicked.connect(self._on_queue_dbl)
        main.addWidget(self._queue_list, 1)

    def _on_play(self):
        self.play_clicked.emit()

    def _on_seek_end(self):
        self._seeking = False
        if self._duration > 0:
            self.seek_requested.emit(self._seek.value() / 1000.0 * self._duration)

    def _on_seek_drag(self, v):
        if self._duration > 0:
            self._time_lbl.setText(_fmt(v / 1000.0 * self._duration))

    def _on_queue_dbl(self, item):
        fp = item.data(Qt.UserRole)
        if fp:
            self.track_from_queue.emit(fp)

    def _on_queue_reorder(self, *args):
        """Emit new filepath order after drag & drop."""
        if getattr(self, '_setting_queue', False):
            return
        filepaths = []
        for i in range(self._queue_list.count()):
            item = self._queue_list.item(i)
            fp = item.data(Qt.UserRole)
            if fp:
                filepaths.append(fp)
        if filepaths:
            self.queue_reordered.emit(filepaths)

    def _show_menu(self):
        menu = QMenu(self)
        menu.addAction("Ecualizador...", self.eq_requested.emit)
        menu.addSeparator()
        menu.addAction("Añadir a playlist...", lambda: self.add_to_playlist.emit(""))
        menu.addAction("Información del archivo", self.file_info_requested.emit)
        menu.exec(self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomRight()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._artwork_bg.setGeometry(self.rect())

    # ── Public API ──

    def set_track(self, title: str, artist: str = "", album: str = "",
                  quality: str = "", cover_path: str = ""):
        self._title.setText(title or "Sin reproducción")
        parts = []
        if artist:
            parts.append(artist)
        if album:
            parts.append(album)
        self._subtitle.setText(" · ".join(parts))
        if quality:
            self._quality.setText(f" {quality} ")
            self._quality.setStyleSheet(
                "font-size: 11px; padding: 2px 10px; border-radius: 8px;"
                "background: rgba(143,183,255,0.08); color: #8FB7FF; font-weight: 600;")
        else:
            self._quality.setText("")
            self._quality.setStyleSheet("")
        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                self._cover.setPixmap(pix.scaled(
                    310, 310, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._artwork_bg.set_pixmap(pix)
        else:
            self._artwork_bg.clear()

    def load_lyrics(self, title: str, artist: str = "",
                    album: str = "", duration: float = 0.0):
        self._lyrics.load_lyrics(title, artist, album, duration)

    def set_state(self, state: str):
        self._state = state
        self._play_btn.setIcon(QIcon(get_icon(
            "pause" if state == "playing" else "play")))

    def set_position(self, seconds: float):
        if self._seeking:
            return
        self._time_lbl.setText(_fmt(seconds))
        if self._duration > 0:
            self._seek.setValue(int(seconds / self._duration * 1000))
        self._lyrics.set_position(seconds)

    def set_duration(self, seconds: float):
        if seconds > 0:
            self._duration = seconds
            self._dur_lbl.setText(_fmt(seconds))
        self._lyrics.set_duration(seconds)

    def set_volume(self, vol: int):
        self._vol.blockSignals(True)
        self._vol.setValue(vol)
        self._vol.blockSignals(False)

    def set_queue(self, items: list[dict]):
        self._setting_queue = True
        self._queue_list.clear()
        self._queue_label.setText(f"Cola ({len(items)} canciones)")
        for item in items:
            prefix = "▶ " if item.get("is_current") else "♪ "
            text = f"{prefix}{item.get('title','')} — {item.get('artist','') or '...'}"
            if item.get("duration"):
                text += f"    {_fmt(item['duration'])}"
            qi = QListWidgetItem(text)
            qi.setData(Qt.UserRole, item.get("filepath", ""))
            qi.setSizeHint(QSize(0, 36))
            self._queue_list.addItem(qi)
        self._setting_queue = False

    def set_worker_manager(self, workers):
        """Set the worker manager for async lyrics fetching."""
        self._lyrics._workers = workers


def _fmt(t: float) -> str:
    t = int(t)
    if t < 3600:
        return f"{t // 60}:{t % 60:02d}"
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"
