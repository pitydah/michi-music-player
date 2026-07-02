"""DownloadsTab — downloaded podcast episodes."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea,
)

from streaming.podcast_manager import PodcastManager


class DownloadsTab(QWidget):
    def __init__(self, podcast_manager: PodcastManager | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("downloadsTab")
        self._pm = podcast_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        self._cl = QVBoxLayout(content)
        self._cl.setContentsMargins(0, 0, 0, 0)
        self._cl.setSpacing(2)

        self._empty = QLabel(
            "No hay episodios descargados.\n\n"
            "Descarga episodios de tus podcasts para escucharlos sin conexión."
        )
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
            return
        episodes = self._pm.get_downloaded_episodes()
        self._clear_list()
        if not episodes:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        shows = {s.id: s.title for s in self._pm.get_shows()}
        for ep in episodes:
            show_title = shows.get(ep.podcast_id, "")
            row = _download_row(ep, show_title, self._remove)
            self._cl.insertWidget(self._cl.count() - 1, row)

    def _remove(self, episode_id: int, local_path: str):
        from streaming.podcast_downloads import remove_download
        if remove_download(local_path):
            if self._pm:
                self._pm._repo._conn.execute(
                    "UPDATE podcast_episodes SET downloaded=0, local_path='' WHERE id=?",
                    (episode_id,),
                )
                self._pm._repo._conn.commit()
            self._reload()

    def _clear_list(self):
        for i in range(self._cl.count() - 1, -1, -1):
            item = self._cl.itemAt(i)
            if item and item.widget() and item.widget() != self._empty:
                item.widget().deleteLater()

    def set_filter(self, text: str):
        if not text:
            self._reload()
            return


def _download_row(ep, show_title: str, remove_cb) -> QFrame:
    row = QFrame()
    row.setStyleSheet(
        "QFrame { background: rgba(255,255,255,0.02); border: none; "
        "border-bottom: 1px solid rgba(255,255,255,0.03); }"
    )
    row.setFixedHeight(48)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 0, 12, 0)

    info = QVBoxLayout()
    info.setSpacing(1)
    t = QLabel(ep.title)
    t.setStyleSheet(
        "color: rgba(255,255,255,0.82); font-size: 12px; font-weight: 500; "
        "background: transparent; border: none;"
    )
    info.addWidget(t)

    sub = show_title if show_title else ""
    if ep.local_path and os.path.isfile(ep.local_path):
        size_mb = round(os.path.getsize(ep.local_path) / (1024 * 1024), 1)
        sub += f"  |  {size_mb} MB" if sub else f"{size_mb} MB"
    if sub:
        s = QLabel(sub)
        s.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "background: transparent; border: none;"
        )
        info.addWidget(s)
    layout.addLayout(info, 1)

    btn = QPushButton("Eliminar")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(
        "QPushButton { background: rgba(255,80,80,0.08); border: 1px solid rgba(255,80,80,0.12); "
        "border-radius: 6px; color: rgba(255,120,120,0.80); font-size: 10px; font-weight: 600; "
        "padding: 4px 12px; }"
        "QPushButton:hover { background: rgba(255,80,80,0.14); }"
    )
    btn.clicked.connect(lambda: remove_cb(ep.id, ep.local_path))
    layout.addWidget(btn)

    badge = QLabel("DESCARGADO")
    badge.setStyleSheet(
        "color: rgba(100,220,100,0.80); font-size: 9px; font-weight: 700; "
        "background: rgba(100,220,100,0.08); border: 1px solid rgba(100,220,100,0.12); "
        "border-radius: 4px; padding: 1px 6px;"
    )
    layout.addWidget(badge)

    return row
