"""GenreCard — premium card widget for genre display with health badges."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QGridLayout, QLabel, QFrame, QMenu,
)

from ui.central.central_styles import glass_card_qss, badge_qss, card_meta_qss
from ui.effects.michi_glass import apply_card_shadow

_BG = "#090B11"
_TEXT = "rgba(255,255,255,0.95)"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class GenreCard(QFrame):
    clicked = Signal(str)
    play_requested = Signal(str)
    mix_requested = Signal(str)
    radio_requested = Signal(str)
    playlist_requested = Signal(str)
    cleanup_requested = Signal(str)

    def __init__(self, genre_data: dict, parent=None):
        super().__init__(parent)
        self._data = genre_data
        self._genre_key = genre_data.get("genre", "")

        self.setObjectName("genreCard")
        self.setFixedSize(240, 240)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(glass_card_qss("genreCard"))
        apply_card_shadow(self)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)

        cover = QFrame()
        cover.setFixedSize(216, 80)
        cover.setStyleSheet("background: transparent; border-radius: 10px;")
        cl = QGridLayout(cover)
        cl.setContentsMargins(2, 0, 2, 0)
        cl.setSpacing(2)
        for ci in range(4):
            lbl = QLabel()
            lbl.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 6px;")
            lbl.setAlignment(Qt.AlignCenter)
            cl.addWidget(lbl, ci // 2, ci % 2)
        v.addWidget(cover)

        name = genre_data.get("genre", "—")
        if len(name) > 22:
            name = name[:21] + "…"
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 14px; font-weight: 700;")
        v.addWidget(name_lbl)

        stats = (f"{genre_data.get('track_count', 0)} canc · "
                 f"{genre_data.get('artist_count', 0)} art · "
                 f"{genre_data.get('album_count', 0)} alb")
        s_lbl = QLabel(stats)
        s_lbl.setStyleSheet(card_meta_qss())
        v.addWidget(s_lbl)

        health = genre_data.get("health", "ok")
        missing = genre_data.get("missing_metadata_count", 0)
        badge_text = ""
        badge_style = ""
        if health == "ok" and missing == 0:
            badge_text = "Limpio"
            badge_style = badge_qss("success")
        elif missing > 0:
            badge_text = f"{missing} sin meta"
            badge_style = badge_qss("warning")
        else:
            badge_text = health.capitalize()
            badge_style = badge_qss("info")

        if badge_text:
            b = QLabel(badge_text)
            b.setStyleSheet(badge_style)
            v.addWidget(b)

        v.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._genre_key)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: rgba(20,22,28,0.97); border: 1px solid rgba(255,255,255,0.06);"
            "border-radius: 10px; padding: 4px; color: rgba(255,255,255,0.88); }"
            "QMenu::item { padding: 6px 24px 6px 12px; border-radius: 6px; }"
            "QMenu::item:selected { background: rgba(143,183,255,0.16); }")
        menu.addAction("Abrir género", lambda: self.clicked.emit(self._genre_key))
        menu.addSeparator()
        menu.addAction("Reproducir todo", lambda: self.play_requested.emit(self._genre_key))
        menu.addAction("Crear mix", lambda: self.mix_requested.emit(self._genre_key))
        menu.addAction("Radio local", lambda: self.radio_requested.emit(self._genre_key))
        menu.addAction("Crear playlist", lambda: self.playlist_requested.emit(self._genre_key))
        menu.addSeparator()
        menu.addAction("Limpiar género", lambda: self.cleanup_requested.emit(self._genre_key))
        menu.exec(event.globalPos())



