"""HistoryTab — timeline of radio and podcast listening."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea,
)

from streaming.podcast_manager import PodcastManager


class HistoryTab(QWidget):
    history_play_requested = Signal(object)  # BroadcastHistoryItem

    def __init__(self, podcast_manager: PodcastManager | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("historyTab")
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
            "No hay historial todavia.\n\n"
            "El historial registrara las transmisiones que escuches."
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
        items = self._pm.get_history(100)
        self._clear_list()
        if not items:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        for item in items:
            row = _history_row(item, self._on_play)
            self._cl.insertWidget(self._cl.count() - 1, row)

    def _on_play(self, item):
        self.history_play_requested.emit(item)

    def _clear_list(self):
        for i in range(self._cl.count() - 1, -1, -1):
            item = self._cl.itemAt(i)
            if item and item.widget() and item.widget() != self._empty:
                item.widget().deleteLater()

    def set_filter(self, text: str):
        if not text:
            self._reload()
            return


def _history_row(item, play_cb=None) -> QFrame:
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
        play_btn.clicked.connect(lambda: play_cb(item))
    layout.addWidget(play_btn)

    info = QVBoxLayout()
    info.setSpacing(1)
    t = QLabel(item.title)
    t.setStyleSheet(
        "color: rgba(255,255,255,0.82); font-size: 12px; font-weight: 500; "
        "background: transparent; border: none;"
    )
    info.addWidget(t)

    sub = item.subtitle if item.subtitle else ""
    if item.duration_seconds:
        m, s = divmod(item.duration_seconds, 60)
        h, m = divmod(m, 60)
        dur = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
        sub += f"  |  {dur}" if sub else dur
    if sub:
        s = QLabel(sub)
        s.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "background: transparent; border: none;"
        )
        info.addWidget(s)
    layout.addLayout(info, 1)

    badge_text = "STREAM" if item.entry_type == "radio" else "PODCAST"
    badge_color = (
        "rgba(143,183,255,0.80)" if item.entry_type == "radio"
        else "rgba(192,132,252,0.80)"
    )
    badge_bg = (
        "rgba(143,183,255,0.08)" if item.entry_type == "radio"
        else "rgba(192,132,252,0.08)"
    )
    badge = QLabel(badge_text)
    badge.setStyleSheet(
        f"color: {badge_color}; font-size: 9px; font-weight: 700; "
        f"background: {badge_bg}; border: 1px solid {badge_color.replace('0.80','0.15')}; "
        f"border-radius: 4px; padding: 1px 6px;"
    )
    layout.addWidget(badge)

    if item.completed:
        done = QLabel("COMPLETADO")
        done.setStyleSheet(
            "color: rgba(100,220,100,0.70); font-size: 9px; font-weight: 700; "
            "background: rgba(100,220,100,0.08); border: 1px solid rgba(100,220,100,0.12); "
            "border-radius: 4px; padding: 1px 6px;"
        )
        layout.addWidget(done)

    return row
