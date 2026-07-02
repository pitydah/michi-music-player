"""BroadcastHubPage — main hub for radio and podcasts (Transmisiones)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QLineEdit,
    QStackedWidget,
)

from ui.central.central_styles import (
    glass_button_qss, glass_input_qss,
)
from ui.broadcast.broadcast_cards import summary_card
from streaming.radio_manager import RadioManager
from streaming.podcast_manager import PodcastManager


class BroadcastHubPage(QWidget):
    navigate_requested = Signal(str)
    play_track_requested = Signal(object)  # TrackRef

    def __init__(self, radio_manager: RadioManager | None = None,
                 podcast_manager: PodcastManager | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("broadcastHubPage")
        self._radio_manager = radio_manager
        self._podcast_manager = podcast_manager
        self._tabs: list[str] = ["live", "podcasts", "episodes", "downloads", "history"]
        self._tab_widgets: dict[str, QWidget] = {}
        self._current_tab = "live"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        title = QLabel("Transmisiones")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent; border: none;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Radio en vivo, podcasts y episodios para escuchar, guardar o continuar."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent; border: none;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        action_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar en transmisiones...")
        self._search_input.setStyleSheet(glass_input_qss())
        self._search_input.textChanged.connect(self._on_search)
        action_row.addWidget(self._search_input, 1)

        self._add_radio_btn = QPushButton("+ Añadir emisora")
        self._add_radio_btn.setCursor(Qt.PointingHandCursor)
        self._add_radio_btn.setStyleSheet(glass_button_qss("secondary"))
        self._add_radio_btn.clicked.connect(self._add_station)
        action_row.addWidget(self._add_radio_btn)

        self._add_podcast_btn = QPushButton("+ Añadir podcast RSS")
        self._add_podcast_btn.setCursor(Qt.PointingHandCursor)
        self._add_podcast_btn.setStyleSheet(glass_button_qss("secondary"))
        self._add_podcast_btn.clicked.connect(self._add_podcast)
        action_row.addWidget(self._add_podcast_btn)

        cl.addLayout(action_row)

        self._summary_row = QHBoxLayout()
        self._summary_row.setSpacing(10)
        self._summary_cards: dict[str, QWidget] = {}
        for key, label, accent in [
            ("live", "En vivo", "rgba(143,183,255,0.90)"),
            ("podcasts", "Podcasts", "rgba(143,183,255,0.90)"),
            ("new", "Nuevos", "#FFB347"),
            ("downloads", "Descargas", "#64DC64"),
        ]:
            card = summary_card(label, "0", accent)
            self._summary_cards[key] = card
            self._summary_row.addWidget(card)
        cl.addLayout(self._summary_row)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        tab_labels = {
            "live": "En vivo",
            "podcasts": "Podcasts",
            "episodes": "Episodios",
            "downloads": "Descargas",
            "history": "Historial",
        }
        self._tab_btns: dict[str, QPushButton] = {}
        for tab_key, tab_label in tab_labels.items():
            btn = QPushButton(tab_label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(tab_key == self._current_tab)
            btn.clicked.connect(lambda checked=False, k=tab_key: self._switch_tab(k))
            btn.setStyleSheet(self._tab_qss(tab_key == self._current_tab))
            self._tab_btns[tab_key] = btn
            tab_row.addWidget(btn)
        tab_row.addStretch()
        cl.addLayout(tab_row)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")

        from ui.broadcast.radio_live_tab import RadioLiveTab
        live_tab = RadioLiveTab(self._radio_manager)
        live_tab.station_selected.connect(self._on_station_selected)
        live_tab.add_station_requested.connect(self._add_station)
        self._tab_widgets["live"] = live_tab
        self._stack.addWidget(live_tab)

        from ui.broadcast.podcasts_tab import PodcastsTab
        podcasts_tab = PodcastsTab(self._podcast_manager)
        podcasts_tab.add_feed_requested.connect(self._add_podcast)
        self._tab_widgets["podcasts"] = podcasts_tab
        self._stack.addWidget(podcasts_tab)

        from ui.broadcast.episodes_tab import EpisodesTab
        ep_tab = EpisodesTab(self._podcast_manager)
        ep_tab.episode_play_requested.connect(self._on_episode_play)
        self._tab_widgets["episodes"] = ep_tab
        self._stack.addWidget(ep_tab)

        from ui.broadcast.downloads_tab import DownloadsTab
        dl_tab = DownloadsTab(self._podcast_manager)
        self._tab_widgets["downloads"] = dl_tab
        self._stack.addWidget(dl_tab)

        from ui.broadcast.history_tab import HistoryTab
        hist_tab = HistoryTab(self._podcast_manager)
        hist_tab.history_play_requested.connect(self._on_history_play)
        self._tab_widgets["history"] = hist_tab
        self._stack.addWidget(hist_tab)

        self._stack.setCurrentIndex(0)
        cl.addWidget(self._stack, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._refresh_counts()

    def _refresh_counts(self):
        live = self._radio_manager.count() if self._radio_manager else 0
        self._set_summary("live", str(live))

        if self._podcast_manager:
            counts = self._podcast_manager.get_counts()
            self._set_summary("podcasts", str(counts.get("shows", 0)))
            self._set_summary("new", str(counts.get("unplayed", 0)))
            self._set_summary("downloads", str(counts.get("downloaded", 0)))
        else:
            for k in ("podcasts", "new", "downloads"):
                self._set_summary(k, "0")

    def _set_summary(self, key: str, value: str):
        card = self._summary_cards.get(key)
        if card:
            from ui.broadcast.broadcast_cards import _set_card_value
            _set_card_value(card, value)

    def _switch_tab(self, tab_key: str):
        self._current_tab = tab_key
        idx = self._tabs.index(tab_key)
        self._stack.setCurrentIndex(idx)
        for k, btn in self._tab_btns.items():
            checked = k == tab_key
            btn.setChecked(checked)
            btn.setStyleSheet(self._tab_qss(checked))

    def _on_station_selected(self, url: str, name: str):
        from sources.base_source import TrackRef
        track = TrackRef(
            uri=url, title=name, artist="",
            source_type="radio", source_label="Radio",
        )
        self.play_track_requested.emit(track)

    def switch_to(self, tab_key: str):
        if tab_key in self._tabs:
            self._switch_tab(tab_key)

    def _on_search(self, text: str):
        tab = self._tab_widgets.get(self._current_tab)
        if tab and hasattr(tab, 'set_filter'):
            tab.set_filter(text)

    def _add_station(self):
        tab = self._tab_widgets.get("live")
        if tab and hasattr(tab, 'add_station'):
            tab.add_station()

    def _on_episode_play(self, ep):
        """Play a podcast episode via PlayerService."""
        from sources.base_source import TrackRef
        track = TrackRef(
            uri=ep.local_path if ep.downloaded and ep.local_path else ep.audio_url,
            title=ep.title,
            artist="",
            source_type="podcast",
            source_label="Podcast",
        )
        self.play_track_requested.emit(track)

    def _on_history_play(self, item):
        """Play a history entry (radio or podcast)."""
        from sources.base_source import TrackRef
        track = TrackRef(
            uri=item.ref_id or item.extra.get("url", ""),
            title=item.title,
            artist=item.subtitle,
            source_type=item.entry_type,
            source_label="Historial",
        )
        if track.uri:
            self.play_track_requested.emit(track)

    def _add_podcast(self):
        from ui.broadcast.add_feed_dialog import AddFeedDialog
        dialog = AddFeedDialog(self._podcast_manager, self)
        if dialog.exec() and dialog.feed_url:
            result = self._podcast_manager.add_feed(dialog.feed_url)
            if result.get("ok"):
                self._refresh_counts()
                podcasts_tab = self._tab_widgets.get("podcasts")
                if podcasts_tab and hasattr(podcasts_tab, 'reload'):
                    podcasts_tab.reload()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", result.get("error", "Error desconocido"))

    def reload_counts(self):
        self._refresh_counts()

    @staticmethod
    def _tab_qss(active: bool) -> str:
        if active:
            return (
                "QPushButton { background: rgba(143,183,255,0.12); "
                "border: 1px solid rgba(143,183,255,0.20); border-radius: 8px; "
                "color: rgba(255,255,255,0.90); font-size: 12px; font-weight: 600; "
                "padding: 6px 16px; }"
            )
        return (
            "QPushButton { background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; "
            "color: rgba(255,255,255,0.56); font-size: 12px; font-weight: 500; "
            "padding: 6px 16px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06); }"
        )
