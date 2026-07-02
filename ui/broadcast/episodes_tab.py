"""EpisodesTab — compact list of podcast episodes."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QComboBox,
)

from ui.central.central_styles import glass_combo_qss
from streaming.podcast_manager import PodcastManager


class EpisodesTab(QWidget):
    episode_play_requested = Signal(object)  # PodcastEpisode

    def __init__(self, podcast_manager: PodcastManager | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("episodesTab")
        self._pm = podcast_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        filter_row = QHBoxLayout()
        self._filter_combo = QComboBox()
        self._filter_combo.addItems([
            "Todos", "Nuevos", "En progreso", "No escuchados",
            "Favoritos", "Descargados", "Escuchados",
        ])
        self._filter_combo.setStyleSheet(glass_combo_qss())
        self._filter_combo.currentTextChanged.connect(self._reload)
        filter_row.addWidget(self._filter_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        self._cl = QVBoxLayout(content)
        self._cl.setContentsMargins(0, 0, 0, 0)
        self._cl.setSpacing(2)

        self._empty = QLabel("No hay episodios.")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 13px; "
            "background: transparent; border: none; padding: 48px;"
        )
        self._empty.setWordWrap(True)
        self._cl.addWidget(self._empty)

        self._cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._reload()

    def _reload(self):
        if self._pm is None:
            self._empty.setVisible(True)
            return

        filter_text = self._filter_combo.currentText()
        if filter_text == "Nuevos":
            episodes = self._pm.get_unplayed_episodes(200)
        elif filter_text == "En progreso":
            episodes = self._pm.get_in_progress_episodes(200)
        elif filter_text == "No escuchados":
            episodes = self._pm.get_episodes_by_status(played=0, limit=200)
        elif filter_text == "Favoritos":
            episodes = self._pm.get_favorite_episodes(200)
        elif filter_text == "Descargados":
            episodes = self._pm.get_downloaded_episodes()
        elif filter_text == "Escuchados":
            episodes = self._pm.get_listened_episodes(200)
        else:
            episodes = self._pm.get_recent_episodes(200)

        self._clear_list()
        if not episodes:
            self._empty.setVisible(True)
            return

        self._empty.setVisible(False)
        shows = {s.id: s.title for s in self._pm.get_shows()}
        for ep in episodes:
            show_title = shows.get(ep.podcast_id, "")
            row = _episode_row(ep, show_title, self._on_play)
            self._cl.insertWidget(self._cl.count() - 1, row)

    def _on_play(self, ep):
        self.episode_play_requested.emit(ep)

    def set_filter(self, text: str):
        if not text:
            self._reload()
            return
        if self._pm is None:
            return
        episodes = self._pm.get_recent_episodes(200)
        self._clear_list()
        filtered = [e for e in episodes if text.lower() in e.title.lower()]
        if not filtered:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        shows = {s.id: s.title for s in self._pm.get_shows()}
        for ep in filtered:
            show_title = shows.get(ep.podcast_id, "")
            row = _episode_row(ep, show_title, self._on_play)
            self._cl.insertWidget(self._cl.count() - 1, row)

    def _clear_list(self):
        for i in range(self._cl.count() - 1, -1, -1):
            item = self._cl.itemAt(i)
            if item and item.widget() and item.widget() != self._empty:
                item.widget().deleteLater()


def _episode_row(ep, show_title: str, play_cb=None) -> QFrame:
    row = QFrame()
    row.setStyleSheet(
        "QFrame { background: rgba(255,255,255,0.02); border: none; "
        "border-bottom: 1px solid rgba(255,255,255,0.03); }"
    )
    row.setFixedHeight(48)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 0, 12, 0)

    play_btn = QPushButton("\u25b6")
    play_btn.setCursor(Qt.PointingHandCursor)
    play_btn.setFixedSize(28, 28)
    play_btn.setStyleSheet(
        "QPushButton { background: rgba(143,183,255,0.08); border: 1px solid rgba(143,183,255,0.10); "
        "border-radius: 14px; color: rgba(255,255,255,0.72); font-size: 11px; }"
        "QPushButton:hover { background: rgba(143,183,255,0.16); color: rgba(255,255,255,0.90); }"
    )
    if play_cb:
        play_btn.clicked.connect(lambda: play_cb(ep))
    layout.addWidget(play_btn)

    info = QVBoxLayout()
    info.setSpacing(1)
    t = QLabel(ep.title)
    t.setStyleSheet(
        "color: rgba(255,255,255,0.82); font-size: 12px; font-weight: 500; "
        "background: transparent; border: none;"
    )
    info.addWidget(t)

    sub = show_title if show_title else ""
    if ep.published_at:
        sub += f"  |  {ep.published_at}" if sub else ep.published_at
    if ep.duration_seconds:
        m, s = divmod(ep.duration_seconds, 60)
        sub += f"  |  {m}m {s}s"
    if ep.position_seconds > 0 and ep.duration_seconds > 0:
        pct = int(ep.position_seconds / max(ep.duration_seconds, 1) * 100)
        sub += f"  |  {pct}%"
    if sub:
        s = QLabel(sub)
        s.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "background: transparent; border: none;"
        )
        info.addWidget(s)
    layout.addLayout(info, 1)

    if not ep.played:
        badge = QLabel("NUEVO")
        badge.setStyleSheet(
            "color: rgba(100,220,100,0.90); font-size: 9px; font-weight: 700; "
            "background: rgba(100,220,100,0.10); border: 1px solid rgba(100,220,100,0.15); "
            "border-radius: 4px; padding: 1px 6px;"
        )
        layout.addWidget(badge)
    elif ep.completed:
        badge = QLabel("COMPLETADO")
        badge.setStyleSheet(
            "color: rgba(143,183,255,0.70); font-size: 9px; font-weight: 700; "
            "background: rgba(143,183,255,0.08); border: 1px solid rgba(143,183,255,0.12); "
            "border-radius: 4px; padding: 1px 6px;"
        )
        layout.addWidget(badge)
    elif ep.position_seconds > 0:
        badge = QLabel("EN PROGRESO")
        badge.setStyleSheet(
            "color: #FFB347; font-size: 9px; font-weight: 700; "
            "background: rgba(255,180,71,0.10); border: 1px solid rgba(255,180,71,0.15); "
            "border-radius: 4px; padding: 1px 6px;"
        )
        layout.addWidget(badge)

    return row
