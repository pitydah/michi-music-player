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

    def show_audio_lab(self, key: str = ""):
        def _build():
            from ui.audio_lab.audio_lab_page import AudioLabPage
            page = AudioLabPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            self._win._playback.state_changed.connect(
                self._update_audio_lab_status)
            return page
        self._lazy("audio_lab", _build)
        self._update_audio_lab_status()

    def _update_audio_lab_status(self, _state=None):
        w = self._win
        page = w._views.widget("audio_lab") if hasattr(w, '_views') else None
        if not page or not hasattr(page, 'set_status_text'):
            return
        ref = getattr(w, '_current_ref', None)
        if not ref:
            page.set_status_text("Sin reproducción activa.")
            return
        parts = [ref.title or "Desconocido"]
        if ref.artist:
            parts.append(ref.artist)

        item = None
        if hasattr(w, '_ctx') and hasattr(w._ctx, 'items_index'):
            item = w._ctx.items_index.get(ref.uri)

        # Format probe for container / sample rate / bit depth
        if ref.uri:
            try:
                from audio.format_probe import probe_format
                fmt = probe_format(ref.uri)
                tech = fmt.container.upper() if fmt.container else ""
                sr = f"{fmt.sample_rate // 1000}" if fmt.sample_rate else ""
                bd = str(fmt.bit_depth) if fmt.bit_depth else ""
                if tech:
                    q = tech
                    if sr and bd:
                        q += f" {bd}/{sr}"
                    parts.append(q)
            except Exception:
                pass

        # Quality classifier (lossless / hires / dsd)
        try:
            from audio.quality_classifier import classify_audio_quality
            qc = classify_audio_quality(item or ref)
            label = qc.get("label", "")
            if label:
                parts.append(label)
        except Exception:
            pass

        # Bit-perfect / DAC status
        try:
            player = getattr(w, '_player', None)
            if player and hasattr(player, 'get_audio_diagnostics'):
                diag = player.get_audio_diagnostics()
                if isinstance(diag, dict):
                    bp = diag.get("bitperfect_status", "")
                    if bp and bp.lower() == "yes":
                        parts.append("Bit-perfect")
                    elif bp and bp.lower() == "no":
                        parts.append("DSP activo")
                    profile = diag.get("profile", "")
                    if profile:
                        parts.append(profile)
        except Exception:
            pass

        page.set_status_text(" · ".join(parts))

    def show_michi_disc_lab(self, key: str = ""):
        def _build():
            from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
            return MichiDiscLabPage()
        self._lazy("michi_disc_lab", _build)

    def show_library_hub(self, key: str = ""):
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
            page.tab_changed.connect(w._on_library_tab_changed)
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

    def show_audio_lab_diagnostics(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabDiagnosticsPage
            page = AudioLabDiagnosticsPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_diagnostics", _build)

    def show_audio_lab_identifier(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabIdentifierPage
            page = AudioLabIdentifierPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_identifier", _build)

    def show_audio_lab_backup(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabBackupPage
            page = AudioLabBackupPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_backup", _build)

    def show_audio_lab_output(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabOutputPage
            page = AudioLabOutputPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_output", _build)

    def show_audio_lab_conversion(self, key: str = ""):
        def _build():
            from ui.audio_lab.conversion_page import ConversionPage
            page = ConversionPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_conversion", _build)

    def show_audio_lab_vinyl_lab(self, key: str = ""):
        def _build():
            from ui.audio_lab.vinyl_lab_page import VinylLabPage
            page = VinylLabPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_vinyl_lab", _build)

    def show_audio_lab_intelligence(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabIntelligencePage
            page = AudioLabIntelligencePage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_intelligence", _build)

    def show_metadata_review(self, key: str = ""):
        def _build():
            from ui.metadata_review_panel import MetadataReviewPanel
            return MetadataReviewPanel()
        self._lazy("metadata_review", _build)
