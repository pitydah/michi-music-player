"""NowPlayingBar — bottom bar with cover, info, seek, controls, volume."""
from PySide6.QtCore import Qt, Signal, QSize, QRectF

from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QSlider, QLabel, QSizePolicy, QGraphicsDropShadowEffect,
)

from ui.icons import get_icon

# ── Technical tokens for left-side filtering ──
_TECHNICAL_TOKENS = (
    "LOCAL", "FLAC", "MP3", "AAC", "OGG", "OPUS",
    "RADIO", "STREAMING", "NAVIDROME", "JELLYFIN",
    "TRANSMITIENDO", "KBPS", "KHZ", "BIT", "DSD",
)



LEFT_CARD_WIDTH = 320
LEFT_CARD_HEIGHT = 86
COVER_SIZE = 64
COVER_RADIUS = 13
LEFT_MARGIN_L = 12
LEFT_MARGIN_R = 14
LEFT_SPACING = 14



def _make_btn(icon_name: str, icon_size: int, button_size: int | None = None,
              role: str = "utility") -> QPushButton:
    from ui.icons import get_qicon

    # Visual size calibration per icon — balances perceptual weight
    _ICON_CALIBRATION = {
        "warm_play": 34, "warm_pause": 32,
        "warm_prev": 26, "warm_next": 26,
        "warm_shuffle": 20, "warm_repeat": 20,
        "warm_vol_high": 22, "warm_vol_medium": 22,
        "warm_vol_low": 22, "warm_mute": 22,
        "warm_eq": 24, "warm_transmit": 24,
        "warm_audio_source": 22, "warm_mini_player": 22,
    }
    visual_size = _ICON_CALIBRATION.get(icon_name, icon_size)

    btn = QPushButton("")
    btn.setFlat(True)

    icon = get_qicon(icon_name, size=visual_size)
    if not icon.isNull():
        btn.setIcon(icon)
    btn.setIconSize(QSize(visual_size, visual_size))

    final_size = button_size or visual_size + 6
    btn.setFixedSize(final_size, final_size)
    btn.setMinimumSize(final_size, final_size)
    btn.setMaximumSize(final_size, final_size)

    btn.setCursor(Qt.PointingHandCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    btn.setAutoDefault(False)
    btn.setDefault(False)
    btn.setProperty("role", role)

    # Border-radius proportional to button size
    radius_map = {"primary_transport": 18, "secondary_transport": 14,
                  "tertiary_transport": 13, "utility": 12, "volume": 12}
    radius = radius_map.get(role, 11)

    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: 1px solid transparent;
            outline: none;
            padding: 0px;
            margin: 0px;
            border-radius: {radius}px;
        }}
        QPushButton:focus {{
            outline: none;
            border: none;
        }}
        QPushButton:hover {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.055);
        }}
        QPushButton:pressed {{
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.04);
        }}
        QPushButton[role="secondary_transport"]:hover {{
            background: rgba(255,255,255,0.075);
            border: 1px solid rgba(255,255,255,0.065);
        }}
        QPushButton[role="secondary_transport"]:pressed {{
            background: rgba(255,255,255,0.040);
            border: 1px solid rgba(255,255,255,0.040);
        }}
        QPushButton[role="tertiary_transport"]:hover {{
            background: rgba(255,255,255,0.055);
        }}
        QPushButton[role="utility"]:hover {{
            background: rgba(255,255,255,0.050);
            border: 1px solid rgba(255,255,255,0.045);
        }}
        QPushButton[active="true"] {{
            background: rgba(249,33,65,0.135);
            border: 1px solid rgba(249,33,65,0.260);
        }}
        QPushButton[active="true"]:hover {{
            background: rgba(249,33,65,0.180);
            border: 1px solid rgba(249,33,65,0.320);
        }}
        QPushButton#transmitButton[active="true"] {{
            background: rgba(52,199,89,0.130);
            border: 1px solid rgba(52,199,89,0.280);
        }}
        QPushButton#transmitButton[active="true"]:hover {{
            background: rgba(52,199,89,0.180);
            border: 1px solid rgba(52,199,89,0.340);
        }}
        QPushButton:disabled {{
            color: rgba(255,255,255,0.25);
            background: transparent;
            border: 1px solid transparent;
        }}
    """)
    return btn


def _set_button_active(btn: QPushButton, active: bool):
    btn.setProperty("active", "true" if active else "false")
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


from functools import lru_cache  # noqa: E402


@lru_cache(maxsize=4)
def _placeholder_cover_pixmap(size: int = 76, radius: int = 16,
                               active: bool = False) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)

    if active:
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor(72, 76, 90))
        grad.setColorAt(1.0, QColor(52, 56, 68))
        glow = QRadialGradient(size * 0.65, size * 0.3, size * 0.7)
        glow.setColorAt(0.0, QColor(255, 122, 0, 60))
        glow.setColorAt(1.0, QColor(255, 77, 46, 0))
        note_alpha = 80
    else:
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor(62, 66, 80))
        grad.setColorAt(1.0, QColor(42, 46, 58))
        glow = QRadialGradient(size * 0.65, size * 0.3, size * 0.7)
        glow.setColorAt(0.0, QColor(255, 122, 0, 38))
        glow.setColorAt(1.0, QColor(255, 77, 46, 0))
        note_alpha = 55

    painter.setBrush(grad)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)

    painter.setBrush(glow)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)

    pen = QPen(QColor(255, 255, 255, note_alpha), 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    cx, cy = size / 2, size / 2
    painter.drawLine(int(cx + 4), int(cy - 8), int(cx + 4), int(cy + 8))
    painter.drawLine(int(cx + 4), int(cy - 8), int(cx + 12), int(cy - 5))
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
    cover_preview_requested = Signal()
    track_details_requested = Signal()
    expanded_requested = Signal()
    transmit_clicked = Signal()
    quality_details_requested = Signal()
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
        self._source_type = "local_file"
        self._source_label = ""
        self._source_quality = ""
        self._codec = ""
        self._bitrate = ""
        self._sample_rate = ""
        self._bit_depth = ""
        self._filepath = ""
        self._audio_output_label = ""
        self._identifier_state = ""
        self._transmitting = False
        self._transmit_device_name = ""
        self._replaygain = ""
        self._has_track = False
        self.setObjectName("nowplayingBar")
        self.setFixedHeight(116)

        self.setAutoFillBackground(True)

        # Force dark aesthetic — this bar is always black
        self._dark_mode = True
        self._bg_rgba = "#050608"
        self._text_color = "#F4F4F5"
        self._text_sec = "#A1A1AA"
        self._accent = "#ffffff"
        self._border = "rgba(255,255,255,0.07)"
        self._shadow_alpha = 110

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
        self._info_card = left_widget
        left_widget.setObjectName("nowPlayingInfoCard")
        left_widget.setFixedWidth(LEFT_CARD_WIDTH)
        left_widget.setFixedHeight(LEFT_CARD_HEIGHT)
        left_widget.setStyleSheet("""
            QWidget#nowPlayingInfoCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,0.055),
                    stop:1 rgba(255,255,255,0.028)
                );
                border: 1px solid rgba(255,255,255,0.055);
                border-radius: 16px;
            }
            QWidget#nowPlayingInfoCard:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,0.072),
                    stop:1 rgba(255,255,255,0.040)
                );
                border: 1px solid rgba(255,255,255,0.080);
            }
            QWidget#nowPlayingInfoCard[playing="true"] {
                border: 1px solid rgba(249,33,65,0.180);
            }
            QWidget#nowPlayingInfoCard[playing="true"]:hover {
                border: 1px solid rgba(249,33,65,0.260);
            }
        """)
        left_widget.setCursor(Qt.ArrowCursor)
        left_widget.setToolTip("Sin pista cargada")
        left_widget.mousePressEvent = self._on_info_card_clicked
        left_widget.mouseDoubleClickEvent = self._on_info_card_double_clicked

        card_shadow = QGraphicsDropShadowEffect(left_widget)
        card_shadow.setBlurRadius(20)
        card_shadow.setXOffset(0)
        card_shadow.setYOffset(4)
        card_shadow.setColor(QColor(0, 0, 0, 55))
        left_widget.setGraphicsEffect(card_shadow)

        card_layout = QHBoxLayout(left_widget)
        card_layout.setContentsMargins(12, 8, 14, 8)
        card_layout.setSpacing(14)

        # Cover button — high-quality paint
        self._cover = CoverButton()
        self._cover.setObjectName("coverButton")
        self._cover.set_placeholder(_placeholder_cover_pixmap(64, 13, active=False), False)
        self._cover.clicked_preview.connect(self._on_cover_clicked)
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
            "  color: #F4F4F5;"
            "  background: transparent; border: none;"
            "}")
        text_layout.addWidget(self._title_lbl)

        self._artist_lbl = QLabel("Añade música")
        self._artist_lbl.setObjectName("nowPlayingArtist")
        self._artist_lbl.setStyleSheet(
            "QLabel#nowPlayingArtist {"
            "  font-size: 12px; font-weight: 500;"
            "  color: #A1A1AA;"
            "  background: transparent; border: none;"
            "}")
        text_layout.addWidget(self._artist_lbl)

        self._meta_lbl = QLabel("Michi Music Player")
        self._meta_lbl.setObjectName("nowPlayingMeta")
        self._meta_lbl.setStyleSheet(
            "QLabel#nowPlayingMeta {"
            "  font-size: 10.5px; font-weight: 500;"
            "  color: #71717A;"
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
        seek_row.setSpacing(8)
        seek_row.setContentsMargins(0, 0, 0, 0)

        self._time_lbl = QLabel("0:00")
        self._time_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.86); font-size: 10px; font-weight: 600;")
        self._time_lbl.setFixedWidth(36)
        self._time_lbl.setAlignment(Qt.AlignCenter)

        self._seek = PremiumSlider(Qt.Horizontal, variant="seek")
        self._seek.setObjectName("seekSlider")
        self._seek.setRange(0, 1000)
        self._seek.setEnabled(False)
        self._seek.set_show_thumb_when_disabled(False)
        self._seek.setMinimumWidth(150)
        self._seek.setFixedHeight(32)
        self._seek.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._seek.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self._seek.sliderReleased.connect(self._on_seek_end)
        self._seek.sliderMoved.connect(self._on_seek_drag)
        self._seek.seek_clicked.connect(self._on_seek_click)

        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.86); font-size: 10px; font-weight: 600;")
        self._dur_lbl.setFixedWidth(36)
        self._dur_lbl.setAlignment(Qt.AlignCenter)

        seek_row.addWidget(self._time_lbl)
        seek_row.addWidget(self._seek)
        seek_row.addWidget(self._dur_lbl)

        # Controls row — playback | utility in one horizontal band
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)
        ctrl_row.setAlignment(Qt.AlignCenter)

        self._shuffle_btn = _make_btn("warm_shuffle", 20, 40, role="tertiary_transport")
        self._prev_btn = _make_btn("warm_prev", 26, 44, role="secondary_transport")
        self._play_btn = _make_btn("warm_play", 34, 54, role="primary_transport")
        self._next_btn = _make_btn("warm_next", 26, 44, role="secondary_transport")
        self._repeat_btn = _make_btn("warm_repeat", 20, 40, role="tertiary_transport")

        self._shuffle_btn.clicked.connect(self._on_shuffle)
        self._shuffle_btn.setToolTip("Aleatorio desactivado")
        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._prev_btn.setToolTip("Canción anterior")
        self._play_btn.clicked.connect(self.play_clicked.emit)
        self._play_btn.setToolTip("Reproducir")
        self._next_btn.clicked.connect(self.next_clicked.emit)
        self._next_btn.setToolTip("Canción siguiente")
        self._repeat_btn.clicked.connect(self._on_repeat)
        self._repeat_btn.setToolTip("Repetición desactivada")

        # Play button — visual center of the bar
        self._play_btn.setObjectName("playButton")
        self._play_btn.setStyleSheet(self._play_btn.styleSheet() + """
            QPushButton#playButton {
                background: rgba(255,255,255,0.075);
                border: 1px solid rgba(255,255,255,0.090);
                border-radius: 18px;
            }
            QPushButton#playButton:hover {
                background: rgba(255,255,255,0.120);
                border: 1px solid rgba(255,255,255,0.145);
            }
            QPushButton#playButton:pressed {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.090);
            }
        """)

        self._audio_output_btn = _make_btn("warm_audio_source", 22, 44, role="utility")
        self._audio_output_btn.setToolTip("Seleccionar salida de audio")
        self._audio_output_btn.clicked.connect(self.audio_output_clicked.emit)

        self._mini_player_btn = _make_btn("warm_mini_player", 22, 44, role="utility")
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

        # Mirror seek_row: 32px | stretch(controls) | 32px | utility
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(0)
        controls_row.addSpacing(32)
        controls_row.addLayout(ctrl_row, 1)
        controls_row.addSpacing(32)
        controls_row.addLayout(utility_controls, 0)

        center_layout.addLayout(seek_row)
        center_layout.addLayout(controls_row)
        layout.addWidget(center_widget, 1)

        # ═══ RIGHT: VOLUME + TOOLS + BADGE (stretch=0) ═══

        # Widgets
        self._vol_btn = _make_btn("warm_vol_high", 22, 38, role="volume")
        self._vol_btn.setToolTip("Click para silenciar")
        self._vol_btn.clicked.connect(self._on_mute_toggle)
        self._vol_level_before_mute = 70
        self._vol_muted = False

        self._vol = PremiumSlider(Qt.Horizontal, variant="volume")
        self._vol.setObjectName("volumeSlider")
        self._vol.setRange(0, 100)
        self._vol.setValue(70)
        self._vol.setFixedWidth(96)
        self._vol.setFixedHeight(32)
        self._vol.valueChanged.connect(lambda v: self.volume_changed.emit(v))

        self._eq_btn = _make_btn("warm_eq", 24, 40, role="utility")
        self._eq_btn.setToolTip("Ecualizador")
        self._eq_btn.clicked.connect(self.eq_clicked.emit)

        self._transmit_btn = _make_btn("warm_transmit", 24, 40, role="utility")
        self._transmit_btn.setObjectName("transmitButton")
        self._transmit_btn.setToolTip("Transmitir a dispositivo")
        self._transmit_btn.clicked.connect(lambda: self.transmit_clicked.emit())

        from ui.source_status_badge import SourceStatusBadge
        self._quality_badge = SourceStatusBadge()
        self._quality_badge.clicked_details.connect(self.quality_details_requested.emit)
        self._quality_badge.setMinimumWidth(88)
        self._quality_badge.setMaximumWidth(176)

        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)

        # Row 0 — controls row
        right_controls = QHBoxLayout()
        right_controls.setContentsMargins(0, 0, 0, 0)
        right_controls.setSpacing(10)
        right_controls.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        right_controls.addStretch()
        right_controls.addWidget(self._vol_btn)
        right_controls.addWidget(self._vol)
        right_controls.addSpacing(4)
        right_controls.addWidget(self._eq_btn)
        right_controls.addWidget(self._transmit_btn)

        right_layout.addLayout(right_controls)

        # Row 1 — badge under volume slider
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        badge_row.addStretch()
        badge_row.addWidget(self._quality_badge)
        right_layout.addLayout(badge_row)

        layout.addWidget(right_widget, 0)

        # ═══ GLASSMORPHISM + SOMBRA ═══
        self.setStyleSheet(f"""
            QWidget#nowplayingBar {{
                background: {self._bg_rgba};
                border-radius: 18px;
                border: 1px solid {self._border};
                border-top: 1px solid rgba(255,255,255,0.07);
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
        self._shuffle_btn.setToolTip(
            "Aleatorio activado" if self._shuffle else "Aleatorio desactivado")
        self.shuffle_clicked.emit()

    def _on_repeat(self):
        modes = {"none": "all", "all": "one", "one": "none"}
        self._repeat = modes.get(self._repeat, "none")
        _set_button_active(self._repeat_btn, self._repeat != "none")
        tips = {"none": "Repetición desactivada", "all": "Repetir lista",
                "one": "Repetir canción"}
        self._repeat_btn.setToolTip(tips.get(self._repeat, "Repetición desactivada"))
        self.repeat_clicked.emit()

    def _on_seek_end(self):
        self._seeking = False
        # seek now handled exclusively by _on_seek_click (mouseReleaseEvent)

    def _on_seek_drag(self, v):
        if self._duration > 0:
            self._time_lbl.setText(_fmt(v / 1000.0 * self._duration))

    def _on_seek_click(self, value: int):
        if self._duration > 0:
            seconds = value / 1000.0 * self._duration
            self._time_lbl.setText(_fmt(seconds))
            self.seek_requested.emit(seconds)

    # ── Public API ──

    def set_state(self, state: str):
        self._state = state
        if state == "playing":
            self._play_btn.setIcon(QIcon(get_icon("warm_pause")))
            self._play_btn.setIconSize(QSize(32, 32))
            self._play_btn.setToolTip("Pausar")
        else:
            self._play_btn.setIcon(QIcon(get_icon("warm_play")))
            self._play_btn.setIconSize(QSize(34, 34))
            self._play_btn.setToolTip("Reproducir")
        # Playing state on info card
        if hasattr(self, '_info_card'):
            playing = "true" if state == "playing" else "false"
            self._info_card.setProperty("playing", playing)
            self._info_card.style().unpolish(self._info_card)
            self._info_card.style().polish(self._info_card)

    def set_track(self, title: str, artist: str, cover_path: str = ""):
        self._raw_title = title or "Sin reproducción"
        self._raw_artist = artist or "Añade música"
        self._has_track = bool(title and title != "Sin reproducción")
        self._raw_meta = self._build_left_meta()

        # Strip technical metadata from artist line if present
        if " · " in self._raw_artist:
            parts = self._raw_artist.split(" · ")
            self._raw_artist = parts[0]
            extra = parts[1].strip() if len(parts) > 1 else ""
            if extra and not any(tok in extra.upper() for tok in _TECHNICAL_TOKENS):
                self._raw_meta = extra

        self._title_lbl.setText(self._raw_title)
        self._artist_lbl.setText(self._raw_artist)
        self._meta_lbl.setText(self._raw_meta)
        self._update_info_card_state()

        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                rounded = _rounded_cover_pixmap(pix, 64, 13)
                self._cover_pixmap = rounded
                self._cover.set_cover_pixmap(rounded)
                self.cover_loaded.emit(pix)
                self._apply_elide()
                return
        self._cover.set_placeholder(_placeholder_cover_pixmap(64, 13, active=True), True)
        self.cover_loaded.emit(None)

        self._apply_elide()

    def set_position(self, seconds: float):
        if self._seeking or self._duration <= 0:
            return
        safe_seconds = max(0.0, min(float(seconds), self._duration))
        self._time_lbl.setText(_fmt(safe_seconds))
        value = int((safe_seconds / self._duration) * 1000)
        self._seek.setValue(max(0, min(1000, value)))

    def set_duration(self, seconds: float):
        self._duration = max(0.0, float(seconds or 0))
        self._dur_lbl.setText(_fmt(self._duration))
        if self._duration <= 0:
            self._time_lbl.setText("0:00")
            self._seek.setValue(0)
            self._seek.setEnabled(False)
        else:
            self._seek.setEnabled(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self):
        """Apply text elision to prevent overflow in the info card."""
        if not hasattr(self, '_info_card'):
            return
        card_w = self._info_card.width()
        margins = LEFT_MARGIN_L + LEFT_MARGIN_R
        spacing = LEFT_SPACING
        avail = max(120, card_w - margins - COVER_SIZE - spacing)
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
        self._vol_muted = (vol <= 0)
        if vol <= 0:
            name = "warm_mute"
            self._vol_btn.setToolTip("Silenciado — click para restaurar")
        elif vol <= 33:
            name = "warm_vol_low"
            self._vol_btn.setToolTip(f"Volumen: {vol}%")
        elif vol <= 66:
            name = "warm_vol_medium"
            self._vol_btn.setToolTip(f"Volumen: {vol}%")
        else:
            name = "warm_vol_high"
            self._vol_btn.setToolTip(f"Volumen: {vol}%")
        self._vol_btn.setIcon(QIcon(get_icon(name)))
        self._vol_btn.setIconSize(QSize(22, 22))

    def _on_mute_toggle(self):
        if self._vol_muted:
            vol = self._vol_level_before_mute
            self._vol_muted = False
            self.set_volume(vol)
            self.volume_changed.emit(vol)
        else:
            self._vol_level_before_mute = self._vol.value()
            self._vol_muted = True
            self.set_volume(0)
            self.volume_changed.emit(0)

    def _update_info_card_state(self):
        if self._has_track:
            self._info_card.setCursor(Qt.PointingHandCursor)
            self._info_card.setToolTip(
                "Click: detalles del tema · Doble click: vista expandida")
            self._cover.setToolTip("Ver carátula")
        else:
            self._info_card.setCursor(Qt.ArrowCursor)
            self._info_card.setToolTip("Sin pista cargada")
            self._cover.setToolTip("")

    def reset_visual_state(self):
        self._has_track = False
        self._raw_title = ""
        self._raw_artist = ""
        self._raw_meta = ""
        self._duration = 0.0
        self._source_quality = ""
        self._source_type = "local_file"
        self._transmitting = False
        self._transmit_device_name = ""

        self._title_lbl.setText("Sin reproducción")
        self._artist_lbl.setText("Añade música")
        self._meta_lbl.setText("Michi Music Player")
        self._time_lbl.setText("0:00")
        self._dur_lbl.setText("0:00")
        self._seek.setValue(0)
        self._seek.setEnabled(False)
        self._seeking = False
        self._shuffle = False
        self._repeat = "none"
        self._update_info_card_state()

        self._cover.set_placeholder(_placeholder_cover_pixmap(64, 13, active=False), False)
        self._cover_pixmap = QPixmap()
        self._play_btn.setIcon(QIcon(get_icon("warm_play")))
        _set_button_active(self._shuffle_btn, False)
        _set_button_active(self._repeat_btn, False)
        _set_button_active(self._transmit_btn, False)

        self._quality_badge.set_text("")
        self._quality_badge.setToolTip("")
        self._refresh_source_badge()
        self._apply_elide()
    def _build_left_meta(self) -> str:
        """Build human-readable third line for the left card — no technical data."""
        if not self._has_track:
            return "Michi Music Player"
        if getattr(self, '_album_label', ""):
            return self._album_label
        if getattr(self, '_playlist_label', ""):
            return self._playlist_label
        return "Reproduciendo ahora"

    def set_quality(self, text: str):
        self._source_quality = text
        if text:
            self._quality_badge.set_text(f" {text} ")
        else:
            self._quality_badge.set_text("")
        self._refresh_source_badge()
        if self._has_track:
            self._raw_meta = self._build_left_meta()
            self._meta_lbl.setText(self._raw_meta)
            self._apply_elide()

    def set_quality_info(self, label: str, category: str = "unknown",
                          tooltip: str = ""):
        """Set quality badge with category-colored styling."""
        self._source_quality = label
        self._quality_badge.set_text(f" {label} ")
        self._quality_badge.set_quality_category(category)
        if tooltip:
            self._quality_badge.setToolTip(tooltip)
        self._refresh_source_badge()
        if self._has_track:
            self._raw_meta = self._build_left_meta()
            self._meta_lbl.setText(self._raw_meta)
            self._apply_elide()

    def set_source_status(self, source_type: str = "local_file", quality: str = "",
                          service: str = "", codec: str = "", bitrate: str = "",
                          sample_rate: str = "", bit_depth: str = "", filepath: str = "",
                          audio_output: str = "", identifier_state: str = "",
                          replaygain: str = "", transmitting: bool = False,
                          transmit_device: str = ""):
        self._source_type = source_type
        self._source_label = service
        self._source_quality = quality
        self._codec = codec
        self._bitrate = bitrate
        self._sample_rate = sample_rate
        self._bit_depth = bit_depth
        self._filepath = filepath
        self._audio_output_label = audio_output
        self._identifier_state = identifier_state
        self._replaygain = replaygain
        self._transmitting = transmitting
        self._transmit_device_name = transmit_device
        self._refresh_source_badge()
        if self._has_track:
            self._raw_meta = self._build_left_meta()
            self._meta_lbl.setText(self._raw_meta)
            self._apply_elide()

    def _refresh_source_badge(self):
        self._quality_badge.set_context(
            source_type=self._source_type,
            quality=self._source_quality,
            service=self._source_label,
            codec=self._codec,
            bitrate=self._bitrate,
            sample_rate=self._sample_rate,
            bit_depth=self._bit_depth,
            filepath=self._filepath,
            audio_output=self._audio_output_label,
            transmitting=self._transmitting,
            transmit_device=self._transmit_device_name,
            identifier_state=self._identifier_state,
            replaygain=self._replaygain,
        )
        # Build unified tooltip: quality + source + filepath + audio output
        lines = [self._source_quality] if self._source_quality else []
        if self._codec:
            detail = self._codec.upper() if self._codec else ""
            if self._bit_depth:
                detail += f" · {self._bit_depth}-bit"
            if self._sample_rate:
                detail += f" · {self._sample_rate}"
            if self._bitrate:
                detail += f" · {self._bitrate}kbps"
            if detail:
                lines.append(detail)
        src = ""
        if self._source_type == "radio":
            src = "Radio" if not self._source_label else f"Radio · {self._source_label}"
        elif self._source_type in ("navidrome", "jellyfin"):
            src = f"{self._source_type.upper()} · {self._source_label}" if self._source_label else self._source_type.upper()
        elif self._filepath:
            import os
            fn = os.path.basename(self._filepath)
            src = f"Archivo local · {fn[:80]}"
        if src:
            lines.append(src)
        if self._audio_output_label:
            lines.append(f"Salida · {self._audio_output_label}")
        if self._transmitting and self._transmit_device_name:
            lines.append(f"Transmitiendo a · {self._transmit_device_name}")
        if self._replaygain:
            lines.append("ReplayGain activo")
        if lines:
            self._quality_badge.setToolTip("\n".join(lines))

    def set_transmit_active(self, active: bool, device_name: str = ""):
        """Update transmit button style and tooltip from external controllers."""
        if not hasattr(self, '_transmit_btn'):
            return
        self._transmitting = active
        self._transmit_device_name = device_name or ""
        self._set_button_active(self._transmit_btn, active)
        if active:
            self._transmit_btn.setToolTip(f"Transmitiendo a: {device_name}")
        else:
            self._transmit_btn.setToolTip("Transmitir a dispositivo")
        self._refresh_source_badge()

    def _set_button_active(self, btn, active: bool):
        """Toggle active visual state on a button via property (consistent string)."""
        btn.setProperty("active", "true" if active else "false")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def transmit_button(self):
        """Returns the transmit QPushButton for menu positioning."""
        return self._transmit_btn

    def audio_output_button(self):
        """Returns the audio output QPushButton for menu positioning."""
        return self._audio_output_btn

    def set_route_tooltip(self, diagnostics):
        """Set audio route diagnostic info on the quality badge tooltip."""
        self._quality_badge.set_route_tooltip(diagnostics)

    def transmit_button_position(self):
        if hasattr(self, '_transmit_btn'):
            return self._transmit_btn.mapToGlobal(
                self._transmit_btn.rect().bottomLeft())
        from PySide6.QtCore import QPoint
        return QPoint(0, 0)

    def get_volume(self) -> int:
        """Returns current volume level (0-100)."""
        return self._vol.value()


    def _on_info_card_clicked(self, event):

        if not self._has_track:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.track_details_requested.emit()
            event.accept()
            return
        event.ignore()

    def _on_info_card_double_clicked(self, event):
        if not self._has_track:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.expanded_requested.emit()
            event.accept()
            return
        event.ignore()

    def _on_cover_clicked(self):
        if self._has_track:
            self.cover_preview_requested.emit()


class CoverButton(QPushButton):
    """High-quality cover art button with hover overlay."""
    clicked_preview = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._placeholder = QPixmap()
        self._hovered = False
        self._has_track = False
        self._has_cover = False
        self._radius = 13.0
        self.setFixedSize(64, 64)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.clicked.connect(self._on_click)

    def set_cover_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._has_cover = not pixmap.isNull()
        self.update()

    def set_placeholder(self, pixmap: QPixmap, has_track: bool):
        self._placeholder = pixmap
        self._has_track = has_track
        self._has_cover = False
        self.setCursor(Qt.PointingHandCursor if has_track else Qt.ArrowCursor)
        self.update()

    def _on_click(self):
        if self._has_track:
            self.clicked_preview.emit()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(0, 0, 64, 64)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        painter.setClipPath(path)

        # Background
        painter.setBrush(QColor(255, 255, 255, 15))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # Pixmap or placeholder
        src = self._pixmap if self._has_cover else self._placeholder
        if not src.isNull():
            scaled = src.scaled(64, 64, Qt.KeepAspectRatioByExpanding,
                                Qt.SmoothTransformation)
            x = (scaled.width() - 64) // 2
            y = (scaled.height() - 64) // 2
            painter.drawPixmap(-x, -y, scaled)

        # Hover overlay — darken
        if self._hovered and (self._has_track or self._has_cover):
            painter.setBrush(QColor(0, 0, 0, 46))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, self._radius, self._radius)

        # Border
        border_alpha = 58 if self._hovered and self._has_track else 28
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, border_alpha), 1.0))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                                self._radius, self._radius)
        painter.end()


class PremiumSlider(QSlider):
    """Premium horizontal slider painted via QPainter — clean capsule + circular thumb."""

    _METRICS = {
        "seek":   {"track_h": 8.0, "thumb_d": 16.0, "height": 32},
        "volume": {"track_h": 8.0, "thumb_d": 15.0, "height": 32},
    }

    seek_clicked = Signal(int)

    def __init__(self, orientation=Qt.Horizontal, parent=None, variant: str = "seek"):
        super().__init__(orientation, parent)
        self._variant = variant
        self._hovered = False
        self._pressed = False
        self._show_thumb_disabled = True
        self.setMouseTracking(True)

    def set_show_thumb_when_disabled(self, show: bool):
        self._show_thumb_disabled = show
        self.update()

    def _slider_geometry(self):
        w = float(self.width())
        h = float(self.height())
        m = self._METRICS.get(self._variant, self._METRICS["seek"])
        track_h = m["track_h"]
        thumb_d = m["thumb_d"]
        track_r = track_h / 2.0
        thumb_r = thumb_d / 2.0
        margin = max(thumb_r + 1.0, track_r + 1.0)
        track_x = margin
        track_w = max(1.0, w - margin * 2)
        track_y = (h - track_h) / 2.0
        track_rect = QRectF(track_x, track_y, track_w, track_h)
        return track_rect, track_x, track_w, track_y, track_h, track_r, thumb_d, thumb_r, margin

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        geo = self._slider_geometry()
        track_rect, track_x, track_w, track_y, track_h, track_r, thumb_d, thumb_r, margin = geo

        mn = self.minimum()
        mx = self.maximum()
        val = self.value()
        ratio = (val - mn) / max(1, (mx - mn))
        ratio = max(0.0, min(1.0, ratio))
        progress_w = track_w * ratio

        # 1. Inactive track — depth gradient for pill look
        base = QLinearGradient(track_rect.left(), track_rect.top(),
                               track_rect.left(), track_rect.bottom())
        if self.isEnabled():
            base.setColorAt(0.0, QColor("#303642"))
            base.setColorAt(1.0, QColor("#222730"))
        else:
            base.setColorAt(0.0, QColor("#282B33"))
            base.setColorAt(1.0, QColor("#1E2128"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(base)
        painter.drawRoundedRect(track_rect, track_r, track_r)

        # 2. Clip path — pill shape
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, track_r, track_r)

        # 3. Progress fill clipped inside the pill
        if progress_w > 1.0 and self.isEnabled():
            painter.save()
            painter.setClipPath(track_path)

            gradient = QLinearGradient(
                track_rect.left(), track_rect.center().y(),
                track_rect.right(), track_rect.center().y(),
            )
            gradient.setColorAt(0.0, QColor("#FF7A00"))
            gradient.setColorAt(0.35, QColor("#FF4A2D"))
            gradient.setColorAt(0.68, QColor("#F21B5B"))
            gradient.setColorAt(1.0, QColor("#9F0C80"))

            progress_rect = QRectF(track_rect.left(), track_rect.top(),
                                   progress_w, track_rect.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRect(progress_rect)
            painter.restore()
        elif progress_w > 1.0:
            painter.save()
            painter.setClipPath(track_path)
            progress_rect = QRectF(track_rect.left(), track_rect.top(),
                                   progress_w, track_rect.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#525866"))
            painter.drawRect(progress_rect)
            painter.restore()

        # 4. Pill border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
        painter.drawRoundedRect(track_rect, track_r, track_r)

        # 5. Thumb
        show_thumb = self.isEnabled() or self._show_thumb_disabled
        if show_thumb:
            thumb_x = track_x + progress_w
            thumb_y = float(self.height()) / 2.0
            thumb_rect = QRectF(thumb_x - thumb_r, thumb_y - thumb_r, thumb_d, thumb_d)

            if not self.isEnabled():
                fill = QColor("#525866")
                bd = QColor("#747986")
            elif self._pressed:
                fill = QColor("#F21B5B")
                bd = QColor("#F5F5F7")
            elif self._hovered:
                fill = QColor("#FF4A2D")
                bd = QColor("#F5F5F7")
            else:
                fill = QColor("#F92141")
                bd = QColor("#F5F5F7")

            painter.setPen(QPen(bd, 1.6))
            painter.setBrush(fill)
            painter.drawEllipse(thumb_rect)

        painter.end()

    def _value_from_x(self, x: float) -> int:
        _, track_x, track_w, *_ = self._slider_geometry()
        ratio = (x - track_x) / max(1.0, track_w)
        ratio = max(0.0, min(1.0, ratio))
        return self.minimum() + int(ratio * (self.maximum() - self.minimum()))

    # ── Interaction ──

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.orientation() == Qt.Horizontal:
            self._pressed = True
            self.setSliderDown(True)
            value = self._value_from_x(
                event.position().x() if hasattr(event, "position") else event.x()
            )
            self.setValue(value)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pressed and self.orientation() == Qt.Horizontal:
            value = self._value_from_x(
                event.position().x() if hasattr(event, "position") else event.x()
            )
            self.setValue(value)
            self.sliderMoved.emit(value)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pressed:
            self._pressed = False
            self.setSliderDown(False)
            self.update()
            self.seek_clicked.emit(self.value())
            event.accept()
            return
        super().mouseReleaseEvent(event)


def _fmt(t: float) -> str:
    t = int(t)
    if t < 3600:
        return f"{t // 60}:{t % 60:02d}"
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"
