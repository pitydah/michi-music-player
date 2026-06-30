"""HubRouteController — lazy-init + fade for hub/detail pages.

Extracted from MainWindow to reduce window.py size.
Each hub page is created once on first navigation, then cached.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.hub_route")


class HubRouteController:
    def __init__(self, window: MainWindow):
        self._win = window

    def _lazy(self, name: str, factory: Callable):
        w = self._win
        if not w._views.widget(name):
            w._views.register(name, factory())
        w._fade_content(name)

    # ── Delegate audio lab to AudioLabController ──

    def show_audio_lab(self, key: str = ""):
        self._win._audio_lab_ctrl.show_audio_lab(key)

    def show_audio_lab_diagnostics(self, key: str = ""):
        self._win._audio_lab_ctrl.show_diagnostics(key)

    def show_audio_lab_identifier(self, key: str = ""):
        self._win._audio_lab_ctrl.show_identifier(key)

    def show_audio_lab_backup(self, key: str = ""):
        self._win._audio_lab_ctrl.show_backup(key)

    def show_audio_lab_output(self, key: str = ""):
        self._win._audio_lab_ctrl.show_output(key)

    def show_audio_lab_intelligence(self, key: str = ""):
        self._win._audio_lab_ctrl.show_intelligence(key)

    def show_audio_lab_lyrics(self, key: str = ""):
        self._win._audio_lab_ctrl.show_lyrics(key)

    def show_audio_lab_artwork(self, key: str = ""):
        self._win._audio_lab_ctrl.show_artwork(key)

    def show_audio_lab_musicbrainz(self, key: str = ""):
        self._win._audio_lab_ctrl.show_musicbrainz(key)

    def show_audio_lab_organize(self, key: str = ""):
        self._win._audio_lab_ctrl.show_organize(key)

    def show_audio_lab_conversion(self, key: str = ""):
        self._win._audio_lab_ctrl.show_conversion(key)

    def show_audio_lab_vinyl_lab(self, key: str = ""):
        self._win._audio_lab_ctrl.show_vinyl_lab(key)

    def show_michi_disc_lab(self, key: str = ""):
        self._win._audio_lab_ctrl.show_disc_lab(key)
        def _build():
            w = self._win
            from ui.hubs.library_hub_page import LibraryHubPage
            page = LibraryHubPage(
                db=w._db,
                window=w,
                songs_widget=w._songs_stack,
                albums_widget=w._albums_stack,
                artists_widget=w._artists_stack,
                genres_widget=w._genres_stack,
                folders_widget=w._folder_browser,
            )
            page.tab_changed.connect(w._lib_ctrl._on_library_tab_changed)
            return page
        self._lazy("library_hub", _build)

    def show_mix_hub(self, key: str = ""):
        def _build():
            w = self._win
            from ui.hubs.mix_hub_page import MixHubPage
            return MixHubPage(preview=w._smart_preview)
        self._lazy("mix_hub", _build)

    def show_playback_hub(self, key: str = ""):
        def _build():
            w = self._win
            from ui.hubs.playback_hub_page import PlaybackHubPage
            return PlaybackHubPage(db=w._db, playback=w._playback)
        self._lazy("playback_hub", _build)

    def show_connections_hub(self, key: str = ""):
        def _build():
            w = self._win
            from ui.hubs.connections_hub_page import ConnectionsHubPage
            return ConnectionsHubPage(db=w._db)
        self._lazy("connections_hub", _build)

    def show_settings_hub(self, key: str = ""):
        def _build():
            from ui.hubs.settings_hub_page import SettingsHubPage
            return SettingsHubPage()
        self._lazy("settings_hub", _build)

    def show_devices_page(self, key: str = ""):
        def _build():
            w = self._win
            from ui.devices_page import DevicesPage
            sync_mgr = w._ensure_sync_manager()
            return DevicesPage(db=w._db, sync_manager=sync_mgr)
        self._lazy("devices_page", _build)

    def show_metadata_review(self, key: str = ""):
        def _build():
            from ui.metadata_review_panel import MetadataReviewPanel
            return MetadataReviewPanel()
        self._lazy("metadata_review", _build)
