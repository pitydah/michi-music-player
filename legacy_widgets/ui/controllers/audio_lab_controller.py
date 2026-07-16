"""LEGACY — reemplazado por ui_qml_bridge correspondiente.

AudioLabController — lazy-init + navigation for Audio Lab pages and sub-pages."""
from __future__ import annotations



import os
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.audio_lab_ctrl")


class AudioLabController:
    def __init__(self, window: MainWindow):
        self._win = window

    def _lazy(self, name: str, factory):
        w = self._win
        if not w._views.widget(name):
            w._views.register(name, factory())
        w._fade_content(name)

    def analyze_filepaths(self, filepaths: list[str]):
        """Analyze audio files in Audio Lab diagnostics. Non-blocking."""
        if not filepaths:
            return
        from core.audio_lab.diagnostics_service import analyse_file
        audio_paths = [fp for fp in filepaths if os.path.isfile(fp)]
        if not audio_paths:
            return
        for fp in audio_paths:
            try:
                analyse_file(fp)
            except Exception as e:
                logger.debug("audio_lab analyze failed for %s: %s", fp, e)
        self._refresh_songs_badges(audio_paths)
        self.show_diagnostics("")

    def _build_diagnostics(self):
        w = self._win
        from ui.audio_lab.sub_pages import AudioLabDiagnosticsPage
        from core.jobs.job_manager import JobManager
        jm = JobManager(
            worker_mgr=getattr(w, '_workers', None),
        ) if hasattr(w, '_workers') else None
        page = AudioLabDiagnosticsPage(
            worker_mgr=getattr(w, '_workers', None),
            job_manager=jm,
            db=getattr(w, '_db', None),
        )
        page.navigate_requested.connect(w._on_sidebar_navigate)
        page.diagnostics_updated.connect(
            lambda paths: self._refresh_songs_badges(paths))
        return page

    @staticmethod
    def _show_page(name: str, factory):
        pass  # Navigation is handled by the caller

    def show_audio_lab(self, key: str = ""):
        def _build():
            from ui.audio_lab.audio_lab_page import AudioLabPage
            page = AudioLabPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            self._win._playback.state_changed.connect(self._update_status)
            return page
        self._lazy("audio_lab", _build)
        self._update_status()

    def _update_status(self, _state=None):
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
        try:
            from audio.quality_classifier import classify_audio_quality
            qc = classify_audio_quality(item or ref)
            label = qc.get("label", "")
            if label:
                parts.append(label)
        except Exception:
            pass
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

    def show_bitperfect_monitor(self, key: str = ""):
        def _build():
            from ui.audio_lab.bitperfect_monitor_page import BitperfectMonitorPage
            page = BitperfectMonitorPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        page_name = "audio_lab_bitperfect_monitor"
        w = self._win
        if not w._views.widget(page_name):
            w._views.register(page_name, _build())
        w._fade_content(page_name)

    def show_diagnostics(self, key: str = ""):
        self._lazy("audio_lab_diagnostics", self._build_diagnostics)

    def _refresh_songs_badges(self, paths: list[str]):
        """Refresh songs page badges after diagnostics update."""
        w = self._win
        songs_ctrl = getattr(w, '_songs_ctrl', None)
        if songs_ctrl and hasattr(songs_ctrl, 'refresh_audio_lab_badges'):
            songs_ctrl.refresh_audio_lab_badges(paths)
        elif songs_ctrl:
            songs_ctrl._refresh_status()

    def show_identifier(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabIdentifierPage
            page = AudioLabIdentifierPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_identifier", _build)

    def show_backup(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabBackupPage
            page = AudioLabBackupPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_backup", _build)

    def show_output(self, key: str = ""):
        def _build():
            from ui.audio_lab.sub_pages import AudioLabOutputPage
            page = AudioLabOutputPage()
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_output", _build)

    def show_intelligence(self, key: str = ""):
        def _build():
            from ui.audio_lab.intelligence_page import IntelligencePage
            page = IntelligencePage(db=self._win._db if hasattr(self._win, '_db') else None)
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_intelligence", _build)

    def show_lyrics(self, key: str = ""):
        def _build():
            w = self._win
            from ui.audio_lab.lyrics_page import LyricsPage
            page = LyricsPage(worker_mgr=getattr(w, '_workers', None))
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_lyrics", _build)

    def show_artwork(self, key: str = ""):
        def _build():
            w = self._win
            from ui.audio_lab.artwork_page import ArtworkPage
            page = ArtworkPage(db=getattr(w, '_db', None),
                               worker_mgr=getattr(w, '_workers', None))
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_artwork", _build)

    def show_musicbrainz(self, key: str = ""):
        def _build():
            w = self._win
            from ui.audio_lab.musicbrainz_page import MusicBrainzPage
            page = MusicBrainzPage(worker_mgr=getattr(w, '_workers', None))
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_musicbrainz", _build)

    def show_organize(self, key: str = ""):
        def _build():
            w = self._win
            from ui.audio_lab.organize_page import OrganizePage
            page = OrganizePage(db=getattr(w, '_db', None),
                                worker_mgr=getattr(w, '_workers', None))
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_organize", _build)

    def show_conversion(self, key: str = ""):
        def _build():
            w = self._win
            from ui.audio_lab.conversion_page import ConversionPage
            page = ConversionPage(
                encoder=getattr(w, '_encoder', None),
            )
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_conversion", _build)

    def show_vinyl_lab(self, key: str = ""):
        def _build():
            w = self._win
            from ui.audio_lab.vinyl_lab_page import VinylLabPage
            page = VinylLabPage(worker_mgr=getattr(w, '_workers', None))
            page.navigate_requested.connect(self._win._on_sidebar_navigate)
            return page
        self._lazy("audio_lab_vinyl_lab", _build)

    def show_disc_lab(self, key: str = ""):
        def _build():
            from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
            return MichiDiscLabPage()
        self._lazy("michi_disc_lab", _build)
