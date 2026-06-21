"""Album Info Banner — premium glass card between CoverFlow and NowPlayingBar."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
)

from metadata.album_summary import AlbumSummary


class AlbumInfoBanner(QWidget):
    play_requested = Signal(str)
    queue_requested = Signal(str)
    playlist_requested = Signal(str)
    metadata_requested = Signal(str)
    details_requested = Signal(str)
    refresh_metadata_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._summary: AlbumSummary | None = None
        self._compact = False
        self.setMinimumHeight(130)
        self.setMaximumHeight(175)

        self._card = QFrame()
        self._card.setStyleSheet(
            "QFrame#albumBanner {"
            "  background: rgba(255,255,255,0.050);"
            "  border: 1px solid rgba(255,255,255,0.085);"
            "  border-radius: 22px; }"
            "QFrame#albumBanner:hover {"
            "  background: rgba(255,255,255,0.060);"
            "  border: 1px solid rgba(255,255,255,0.110); }"
            "QLabel { background: transparent; }")
        self._card.setObjectName("albumBanner")

        self._layout = QHBoxLayout(self._card)
        self._layout.setContentsMargins(20, 14, 20, 14)
        self._layout.setSpacing(16)

        # Mini cover
        self._cover_lbl = QLabel()
        self._cover_lbl.setFixedSize(88, 88)
        self._cover_lbl.setStyleSheet(
            "background: rgba(255,255,255,0.06); border-radius: 14px;"
            "border: 1px solid rgba(255,255,255,0.10);")
        self._cover_lbl.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._cover_lbl)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(4)

        self._title_lbl = QLabel("")
        self._title_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: rgba(255,255,255,0.95);")
        info.addWidget(self._title_lbl)

        self._artist_lbl = QLabel("")
        self._artist_lbl.setStyleSheet(
            "font-size: 14px; color: rgba(255,255,255,0.74);")
        info.addWidget(self._artist_lbl)

        self._meta_lbl = QLabel("")
        self._meta_lbl.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.46);")
        info.addWidget(self._meta_lbl)

        self._desc_lbl = QLabel("")
        self._desc_lbl.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.40);"
            "line-height: 1.4;")
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setMaximumHeight(44)
        info.addWidget(self._desc_lbl)

        # Badges row
        badges = QHBoxLayout()
        badges.setSpacing(8)
        self._source_badge = QLabel("")
        self._source_badge.setStyleSheet(
            "font-size: 10px; font-weight: 600; color: rgba(140,190,255,0.88);"
            "background: rgba(70,145,255,0.14); border-radius: 6px;"
            "padding: 3px 8px;")
        self._source_badge.hide()
        badges.addWidget(self._source_badge)

        self._genre_badge = QLabel("")
        self._genre_badge.setStyleSheet(
            "font-size: 10px; color: rgba(255,255,255,0.52);"
            "background: rgba(255,255,255,0.05); border-radius: 6px;"
            "padding: 3px 8px;")
        self._genre_badge.hide()
        badges.addWidget(self._genre_badge)
        badges.addStretch()
        info.addLayout(badges)

        self._layout.addLayout(info, 1)

        # Action buttons
        actions = QVBoxLayout()
        actions.setSpacing(6)

        play_btn = self._make_action_btn("Reproducir")
        play_btn.clicked.connect(lambda: self.play_requested.emit(
            self._summary.album_key if self._summary else ""))
        queue_btn = self._make_action_btn("+ Cola")
        queue_btn.clicked.connect(lambda: self.queue_requested.emit(
            self._summary.album_key if self._summary else ""))
        details_btn = self._make_action_btn("Detalles")
        details_btn.clicked.connect(lambda: self.details_requested.emit(
            self._summary.album_key if self._summary else ""))

        actions.addWidget(play_btn)
        actions.addWidget(queue_btn)
        actions.addWidget(details_btn)
        actions.addStretch()
        self._layout.addLayout(actions)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._card)

    def _make_action_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            "QPushButton { font-size: 12px; font-weight: 600;"
            "  color: rgba(255,255,255,0.76);"
            "  background: rgba(255,255,255,0.06);"
            "  border: 1px solid rgba(255,255,255,0.09);"
            "  border-radius: 11px; padding: 7px 16px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.10);"
            "  border: 1px solid rgba(255,255,255,0.16);"
            "  color: rgba(255,255,255,0.94); }")
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def set_album_summary(self, summary: AlbumSummary | None):
        self._summary = summary
        if not summary:
            self.clear()
            return

        self._title_lbl.setText(summary.title[:36])
        self._artist_lbl.setText(summary.artist[:40])

        meta_parts = []
        if summary.year:
            meta_parts.append(summary.year)
        if summary.track_count:
            meta_parts.append(f"{summary.track_count} canciones")
        if summary.duration > 0:
            s = int(summary.duration)
            if s >= 3600:
                meta_parts.append(f"{s // 3600} h {(s % 3600)//60} min")
            else:
                meta_parts.append(f"{s // 60} min")
        self._meta_lbl.setText(" \u00b7 ".join(meta_parts))

        if summary.description:
            desc = summary.description[:160]
            self._desc_lbl.setText(desc)
        else:
            self._desc_lbl.setText("")

        # Source badge
        src_labels = {"theaudiodb": "Info externa", "cache": "Cache",
                       "musicbrainz": "MusicBrainz",
                      "local": "Local", "enriching": "Cargando..."}
        self._source_badge.setText(src_labels.get(summary.source, summary.source))
        self._source_badge.setVisible(bool(summary.source and summary.source != "local"))

        # Genre badge
        genre = summary.genre or summary.style or ""
        self._genre_badge.setText(genre[:18])
        self._genre_badge.setVisible(bool(genre))

        # Cover
        if summary.cover_path and summary.cover_path not in ("", "none"):
            pix = QPixmap(summary.cover_path)
            if not pix.isNull():
                self._cover_lbl.setPixmap(
                    pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_loading_state(self, state: str):
        """Show a temporary loading state."""
        self._title_lbl.setText(
            {"loading": "Cargando...", "enriching": "Enriqueciendo...",
             "error": "Error al cargar"}.get(state, state))

    def clear(self):
        self._title_lbl.setText("Sin album seleccionado")
        self._artist_lbl.setText("")
        self._meta_lbl.setText("")
        self._desc_lbl.setText("")
        self._source_badge.hide()
        self._genre_badge.hide()
        self._cover_lbl.clear()
        self._summary = None

    def set_compact_mode(self, enabled: bool):
        self._compact = enabled
        self._desc_lbl.setVisible(not enabled)
        self._genre_badge.setVisible(not enabled and bool(
            self._summary and (self._summary.genre or self._summary.style)))
