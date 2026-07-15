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
        self._suggestion_ctrl = None

    def _ensure_suggestion_ctrl(self):
        if self._suggestion_ctrl is None:
            from ui.controllers.suggestion_bar_controller import SuggestionBarController
            ctx = getattr(self._win, '_context_svc', None)
            self._suggestion_ctrl = SuggestionBarController(
                context_service=ctx, parent=self._win,
            )
        return self._suggestion_ctrl

    def _lazy(self, name: str, factory: Callable):
        w = self._win
        was_new = not w._views.widget(name)
        if was_new:
            w._views.register(name, factory())
        w._fade_content(name)
        self._refresh_suggestions(name)
        if was_new:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(120, lambda: self._insert_suggestion_bar(name))
        else:
            self._insert_suggestion_bar(name)

    def _refresh_suggestions(self, section_key: str):
        ctrl = self._ensure_suggestion_ctrl()
        ctrl.set_section(section_key, title="")

    def _insert_suggestion_bar(self, view_name: str):
        if view_name in ("assistant", "ecosystem_hub"):
            return
        w = self._win
        page = w._views.widget(view_name)
        if page is None:
            return
        bar = self._ensure_suggestion_ctrl().bar()
        if bar.parent() is page:
            bar.raise_()
            bar.show()
            return
        bar.setParent(page)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._do_insert_bar(page, bar))

    def _do_insert_bar(self, page, bar):
        if bar.parent() is not page:
            bar.setParent(page)
        layout = page.layout()
        if layout is not None and hasattr(layout, "insertWidget"):
            layout.insertWidget(0, bar)
        bar.show()

    # ── Delegate audio lab to AudioLabController ──

    def show_audio_lab(self, key: str = ""):
        self._win._audio_lab_ctrl.show_audio_lab(key)

    def show_audio_lab_diagnostics(self, key: str = ""):
        self._win._audio_lab_ctrl.show_diagnostics(key)

    def show_audio_lab_bitperfect_monitor(self, key: str = ""):
        self._win._audio_lab_ctrl.show_bitperfect_monitor(key)

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

    def show_ecosystem_page(self, key: str = ""):
        w = self._win
        ctrl = getattr(w, '_ecosystem_ctrl', None)
        if ctrl is None:
            from ui.controllers.ecosystem_controller import EcosystemController
            ctrl = EcosystemController(w)
            w._ecosystem_ctrl = ctrl
        ctrl.show()

    def show_michi_ai_page(self, key: str = ""):
        w = self._win
        ctrl = getattr(w, '_michi_ai_ctrl', None)
        if ctrl is None:
            from ui.controllers.michi_ai_controller import MichiAIController
            ctrl = MichiAIController(w, context_service=getattr(w, '_context_svc', None))
            w._michi_ai_ctrl = ctrl
        ctrl.show()

    def show_assistant(self, key: str = ""):
        w = self._win
        if getattr(w, '_assistant_ctrl', None) is None:
            from ui.controllers.ai_assistant_controller import AiAssistantController
            w._assistant_ctrl = AiAssistantController(
                db=w._db, worker_manager=w._workers,
                playback=w._playback, safe_mode=w._safe_mode,
                parent=w,
            )
            ctx = getattr(w, '_context_svc', None)
            if ctx:
                w._assistant_ctrl.set_context_service(ctx)
        w._assistant_ctrl.show_assistant(
            w, w._views, panel=getattr(w, '_assistant_panel', None))
        ctx = getattr(w, '_context_svc', None)
        if ctx:
            ctx.record_assistant_opened()
        self._refresh_suggestions("assistant")
