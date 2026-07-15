"""MainWindow — 2 panels + nowplaying bar with library, EQ, and streaming."""

import os
import random
import logging
from PySide6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QPainter, QLinearGradient, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QMessageBox,
)



from ui.icons import app_icon
from audio.player import PlayerEngine
from library.library_db import (
    LibraryDB, DB_PATH, MediaItem,
    AUDIO_EXTS,
)
from ui.folder_browser import FolderBrowserWidget
from ui.search_controller import SearchController
from sources.local_source import LocalSource
from sources.radio_source import RadioSource
from sources.base_source import TrackRef
from library.trackref_model import TrackRefTableModel

from streaming.transmit_manager import TransmitManager

from streaming.subsonic_client import (
    load_servers,
)
from streaming.radio_manager import RadioManager
from ui.music_identifier_view import MusicIdentifierView
from ui.discover_dashboard import DiscoverDashboard
from ui.playlist_hub import PlaylistHubWidget
from ui.playlist_detail_view import PlaylistDetailView
from ui.metadata_editor import MetadataEditorWidget
from ui.artist_grid import ArtistGridWidget
from ui.artist_detail_view import ArtistDetailView
from ui.genre_grid import GenreGridWidget
from ui.genre_detail_view import GenreDetailView
try:
    from ui.home_audio_view import HomeAudioView
except ImportError:
    HomeAudioView = None
try:
    from recognition.detection_service import DetectionService
except ImportError:
    DetectionService = None


# Re-export from navigation controller for backward compat
from ui.controllers.navigation_controller import resolve_section_config

# Backward-compat alias
_resolve_section_config = resolve_section_config


class MainWindow(QMainWindow):
    def __init__(self):
        from time import perf_counter
        _t0 = perf_counter()
        _log = logging.getLogger("michi.startup")

        super().__init__()
        self._safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"
        from core.shutdown_manager import ShutdownManager
        self._shutdown = ShutdownManager()
        from core.feature_manager import FeatureManager
        self._features = FeatureManager()

        self._init_state()
        _log.info("Phase state: %.0f ms", (perf_counter() - _t0) * 1000)
        self._init_core()
        _log.info("Phase core: %.0f ms", (perf_counter() - _t0) * 1000)
        self._init_optional_services()
        _log.info("Phase optional: %.0f ms", (perf_counter() - _t0) * 1000)
        self._init_ui()
        _log.info("Phase ui: %.0f ms", (perf_counter() - _t0) * 1000)
        self._init_controllers()
        _log.info("Phase controllers: %.0f ms", (perf_counter() - _t0) * 1000)
        self._setup_shortcuts()
        self._wire_home_audio_signals()
        self._wire_identifier_signals()
        self._wire_enrichment_signals()
        self._connect_signals()
        _log.info("Phase signals: %.0f ms", (perf_counter() - _t0) * 1000)
        self._load_initial_data()
        _log.info("Phase data: %.0f ms", (perf_counter() - _t0) * 1000)
        _log.info("Startup complete: %.0f ms total", (perf_counter() - _t0) * 1000)

    def _init_state(self):
        """Simple attribute declarations — no imports or allocations."""
        self.setWindowTitle("Michi Music Player")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)
        self.setAcceptDrops(True)
        icon = app_icon()
        if icon:
            self.setWindowIcon(QIcon(icon))
        self._player_bar_ctrl = None
        self._current_ref = None
        self._all_items: list[MediaItem] = []
        self._items_index: dict[str, MediaItem] = {}
        self._current_section_key: str = "home"
        self._current_route_key: str = "home"
        self._current_sidebar_key: str = "home"
        self._initial_route_applied: bool = False
        self._ecosystem_page = None
        self._section_registry = None
        self._ecosystem_ctrl = None
        self._kind_filter: str | None = None
        self._search_text = ""
        self._current_playlist: int | None = None
        self._playlist_refs: list = []
        self._current_refs: list = []
        self._album_sort_key = "title"
        self._album_filter_mode = "all"
        self._coverflow_cache_key: tuple | None = None

        # Optional attributes — initialized as None, filled by their init phase
        self._playlist_ctrl = None
        self._genre_ctrl = None
        self._genre_repo = None
        self._album_repo = None
        self._identifier_view = None
        self._artist_ctrl = None
        self._artist_repo = None
        self._artist_enrich = None
        self._snapserver = None
        self._audio_capture = None
        self._snap_discovery = None
        self._group_mgr = None
        self._michi_api = None
        self._mdns = None
        self._local_media = None
        self._detection = None
        self._identifier_ctrl = None
        self._mpris_ctrl = None
        self._mpris = None
        self._transmit_mgr = None
        self._file_actions = None
        self._expanded_ctrl = None
        self._album_ctrl = None
        self._cast_ctrl = None
        self._snapcast_ctrl = None
        self._ha_ctrl = None
        self._local_media_ctrl = None
        self._mini_player_ctrl = None
        self._audio_output_ctrl = None
        self._playback_ctrl = None
        self._tray_ctrl = None
        self._assistant_panel = None
        self._assistant_ctrl = None
        self._metadata_review_panel = None
        self._metadata_review_ctrl = None
        self._audio_lab_page = None
        self._audio_lab_diagnostics_page = None
        self._audio_lab_identifier_page = None
        self._audio_lab_backup_page = None
        self._audio_lab_output_page = None
        self._audio_lab_intelligence_page = None
        self._michi_disc_lab_page = None
        self._library_hub_page = None
        self._mix_hub_page = None
        self._playback_hub_page = None
        self._connections_hub_page = None
        self._settings_hub_page = None
        self._devices_page = None

    def _init_core(self):
        """DB, player engine, playback service, model, search — must not fail."""
        self._db = LibraryDB(DB_PATH)
        self._player = PlayerEngine(parent=self)
        from audio.player_service import PlayerService
        self._playback = PlayerService(self._player, self)
        self._playback.set_volume(70)
        self._player.set_library_db(self._db)
        self._playback.backend_changed.connect(self._on_backend_changed)
        self._model = TrackRefTableModel(self)
        self._radio_manager = RadioManager()
        self._search_ctrl = SearchController(self)
        self._search_ctrl.register("local", LocalSource(self._db))
        self._search_ctrl.register("radio", RadioSource(self._radio_manager))
        self._search_ctrl.results_ready.connect(self._on_search_results)
        from core.app_context import AppContext
        self._ctx = AppContext(self)
        from ui.controllers.playlist_controller import PlaylistController
        self._playlist_ctrl = PlaylistController(self)
        # Genre services — new DB-backed repository + services
        from library.genre_repository import GenreRepository as DbGenreRepository
        self._db_genre_repo = DbGenreRepository(self._db.conn)
        from core.genre.genre_stats_service import GenreStatsService
        self._genre_stats_svc = GenreStatsService(self._db, self._db_genre_repo)
        from core.genre.genre_cleanup_service import GenreCleanupService
        self._genre_cleanup_svc = GenreCleanupService(self._db, self._db_genre_repo)
        from core.genre.genre_mix_service import GenreMixService
        self._genre_mix_svc = GenreMixService(
            self._db, self._db_genre_repo,
            playlist_store=lambda name: self._db.create_playlist(name) if self._db else None,
        )
        # Legacy in-memory genre repo (for backward compat)
        from ui.controllers.genre_repository import GenreRepository
        self._genre_repo = GenreRepository()
        from ui.controllers.genre_controller import GenreController
        self._genre_ctrl = GenreController(
            self, services=None,
            genre_stats_service=self._genre_stats_svc,
            genre_mix_service=self._genre_mix_svc,
        )
        from ui.controllers.genre_cleanup_controller import GenreCleanupController
        self._genre_cleanup_ctrl = GenreCleanupController(
            self, self._genre_cleanup_svc, self._genre_stats_svc, self._db_genre_repo)
        from core.toast_service import ToastService
        self._toast_svc = ToastService(self)
        from core.worker_manager import WorkerManager
        self._workers = WorkerManager(self)
        self._db._worker_mgr = self._workers
        from ui.view_registry import ViewRegistry
        self._view_registry = ViewRegistry(safe_mode=self._safe_mode)
        self._register_views()
        self._shutdown.register("playback", lambda: self._playback.stop())
        self._shutdown.register("workers", lambda: self._workers.shutdown(2000)
                               if hasattr(self, '_workers') and self._workers else None)
        self._shutdown.register("db", lambda: self._db.close())
        from ui.controllers.home_audio_handlers import HomeAudioHandlers
        self._ha_handlers = HomeAudioHandlers(self)
        from ui.builder.album_sort_menu import AlbumSortMenu
        self._album_sort_menu = AlbumSortMenu(self)
        from ui.controllers.smart_mix_preview import SmartMixPreview
        self._smart_preview = SmartMixPreview(self._db)

    def _init_ui(self):
        """Sidebar, header, content stack, nowplaying, views."""
        self._setup_actions()
        self._setup_ui()

    def _register_views(self):
        """Register optional views as lazy factories in the ViewRegistry."""
        vr = self._view_registry

        vr.register("home_audio", lambda: HomeAudioView(), experimental=True,
                    title="Home Audio", description="Desactivado en modo seguro.")
        vr.register("identifier", lambda: MusicIdentifierView(), experimental=True,
                    title="Identificador", description="Desactivado en modo seguro.")
        vr.register("discover", lambda: DiscoverDashboard(), experimental=False,
                    title="Descubrir", description="Panel no disponible.")
        vr.register("playlist_hub", lambda: PlaylistHubWidget(), experimental=False,
                    title="Playlists", description="No disponible.")
        vr.register("playlist_detail", lambda: PlaylistDetailView(), experimental=False,
                    title="Detalle", description="No disponible.")
        vr.register("metadata_editor", lambda: MetadataEditorWidget(), experimental=False,
                    title="Editor", description="No disponible.")
        vr.register("artist_grid", lambda: ArtistGridWidget(), experimental=False,
                    title="Artistas", description="No disponible.")
        vr.register("artist_detail", lambda: ArtistDetailView(), experimental=False,
                    title="Detalle", description="No disponible.")
        vr.register("genre_grid", lambda: GenreGridWidget(), experimental=False,
                    title="Géneros", description="No disponible.")
        vr.register("genre_detail", lambda: GenreDetailView(), experimental=False,
                    title="Detalle", description="No disponible.")
        vr.register("folder_browser", lambda: FolderBrowserWidget(), experimental=False,
                    title="Carpetas", description="No disponible.")

    def _init_controllers(self):
        """Required controllers — navigation, playback, playlist, library."""
        # Repos first
        from ui.controllers.artist_repository import ArtistRepository
        self._artist_repo = ArtistRepository()

        # SectionContextRegistry + ContextService before AppServices
        from core.context.setup_section_providers import setup_section_providers
        from library.genre_repository import GenreRepository as DbGenreRepo
        db_genre_repo = getattr(self, '_db_genre_repo', DbGenreRepo(self._db.conn))
        genre_stats_svc = getattr(self, '_genre_stats_svc', None)
        self._section_registry = setup_section_providers(
            db=self._db,
            playback=self._playback,
            genre_repo=db_genre_repo,
            genre_stats_svc=genre_stats_svc,
        )
        from core.context.context_service import ContextService
        self._context_svc = ContextService(
            db=self._db,
            playback=self._playback,
            section_registry=self._section_registry,
        )

        # AppServices before controllers that use them
        from core.app_services import AppServices
        svc = AppServices(
            db=self._db, playback=self._playback, player=self._player,
            model=self._model, workers=self._workers, toast=self._toast_svc,
            player_bar=getattr(self, '_player_bar_ctrl', None),
            features=self._features,
            artist_repo=self._artist_repo, genre_repo=self._genre_repo,
            context_svc=self._context_svc,
            fade_to=self._fade_content, navigate=self._on_sidebar_navigate,
            configure_header=self._configure_header_for_section,
            rebuild_sidebar=self._rebuild_sidebar,
            load_library=self._load_library, play_file=self._play_file,
        )
        self._services = svc

        from library.import_service import LibraryImportService
        self._library_import = LibraryImportService(
            self._db,
            scan_path=self._scan_path,
            reload_library=self._reload_library_after_change,
        )

        # Controllers — pass AppServices for progressive migration
        from core.file_actions import FileActions
        self._file_actions = FileActions(self)
        from ui.controllers.album_controller import AlbumController
        self._album_ctrl = AlbumController(self, refresh_grid=self._show_album_grid, services=svc)
        from ui.controllers.transmit_controller import TransmitController
        self._transmit_ctrl = TransmitController(self, services=svc)
        from ui.controllers.audio_output_controller import AudioOutputController
        self._audio_output_ctrl = AudioOutputController(self, services=svc)
        from ui.controllers.snapcast_controller import SnapcastController
        self._snapcast_ctrl = SnapcastController(self, self, services=svc)
        from ui.controllers.home_audio_controller import HomeAudioController
        self._ha_ctrl = HomeAudioController(self, self, services=svc)
        from ui.controllers.cast_controller import CastController
        self._cast_ctrl = CastController(self, services=svc)
        from ui.controllers.local_media_server_controller import LocalMediaServerController
        self._local_media_ctrl = LocalMediaServerController(self, self)
        from ui.controllers.mini_player_controller import MiniPlayerController
        self._mini_player_ctrl = MiniPlayerController(self, self, services=svc)
        from ui.controllers.expanded_controller import ExpandedController
        self._expanded_ctrl = ExpandedController(self, services=svc)
        from ui.controllers.artist_controller import ArtistController
        self._artist_ctrl = ArtistController(self, services=svc)
        from ui.controllers.home_controller import HomeController
        self._home_ctrl = HomeController(self)
        from ui.controllers.navigation_controller import NavigationController
        self._nav_ctrl = NavigationController(self)
        from ui.controllers.library_controller import LibraryController
        self._lib_ctrl = LibraryController(self)
        from ui.controllers.coverflow_controller import CoverFlowController
        self._cf_ctrl = CoverFlowController(self)
        from ui.controllers.smart_mix_controller import SmartMixController
        self._smart_ctrl = SmartMixController(self)
        from ui.controllers.server_browser_controller import ServerBrowserController
        self._srv_ctrl = ServerBrowserController(self)
        from ui.controllers.identifier_handlers import IdentifierHandlers
        self._id_handlers = IdentifierHandlers(self)
        from ui.controllers.sidebar_menu_controller import SidebarMenuController
        self._sidebar_menu_ctrl = SidebarMenuController(self)
        from ui.routers.search_router import SearchRouter
        self._search_router = SearchRouter(self)
        from ui.routers.view_mode_router import ViewModeRouter
        self._view_router = ViewModeRouter(self)
        from ui.controllers.devices_controller import DevicesController
        self._devices_ctrl = DevicesController(self)
        from ui.controllers.audio_lab_controller import AudioLabController
        self._audio_lab_ctrl = AudioLabController(self)
        from ui.controllers.michi_link_controller import MichiLinkController
        self._michi_link_ctrl = MichiLinkController(self)

        from ui.controllers.folder_controller import FolderController
        self._folder_ctrl = FolderController(
            db=self._db,
            file_actions=self._file_actions,
            context_svc=self._context_svc,
            play_files=self._play_filepaths,
            parent=self,
        )

        from ui.controllers.hub_route_controller import HubRouteController
        self._hub_route_ctrl = HubRouteController(self)

        # FileWatcher + LibraryWatcherController (needs _lib_ctrl, created above)
        from library.file_watcher import FileWatcher
        from ui.controllers.library_watcher_controller import LibraryWatcherController
        self._file_watcher = FileWatcher(self._db, parent=self)
        self._library_watcher_ctrl = LibraryWatcherController(
            db=self._db,
            file_actions=self._file_actions,
            library_controller=self._lib_ctrl,
            toast_service=self._toast_svc,
        )
        self._file_watcher.files_added.connect(self._library_watcher_ctrl.on_files_added)
        self._file_watcher.files_removed.connect(self._library_watcher_ctrl.on_files_removed)
        self._file_watcher.files_modified.connect(self._library_watcher_ctrl.on_files_modified)
        self._shutdown.register("file_watcher", lambda: self._file_watcher.stop())

        # Periodic analyzer for Audio Lab (background diagnostics)
        from core.audio_lab.periodic_analyzer import PeriodicAnalyzer
        self._periodic_analyzer = PeriodicAnalyzer(self._db, parent=self)
        self._periodic_analyzer.start()
        self._shutdown.register("periodic_analyzer", lambda: self._periodic_analyzer.stop())

        from core.audio_lab.diagnostics_service import close_global_cache
        self._shutdown.register("diagnostics_cache", close_global_cache)

        # Wire FolderController signals — deferred until UI is built
        self._connect_folder_signals_later()

    def _connect_folder_signals_later(self):
        """Wire FolderController to FolderBrowserWidget after UI init."""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._wire_folder_controller)

    def _wire_folder_controller(self):
        """Connect FolderController to the FolderBrowserWidget instance."""
        if not hasattr(self, '_folder_browser') or not self._folder_browser:
            return
        self._folder_ctrl.connect(self._folder_browser)
        self._folder_ctrl.toast_requested.connect(self._on_folder_toast)
        self._folder_ctrl.health_ready.connect(self._folder_browser.update_health)
        self._folder_ctrl.integrity_ready.connect(self._on_folder_integrity_result)
        self._folder_browser.set_audio_lab_available(
            hasattr(self, '_audio_lab_ctrl') and self._audio_lab_ctrl is not None)

        fb = self._folder_browser
        fb.files_for_metadata.connect(self._open_metadata_for_files)
        fb.show_problem_report.connect(self._show_folder_problem_report)
        fb.safe_rename_dialog.connect(self._on_safe_rename_folder)
        fb.safe_move_dialog.connect(self._on_safe_move_folder)

    def _on_folder_integrity_result(self, result):
        if not result:
            return
        if result.errors:
            msg = "\n".join(result.errors[:5])
            self._toast_svc.warning(
                f"Integridad: {len(result.errors)} errores.\n{msg}" if msg
                else "Errores de integridad detectados", self)
        elif result.changed_files:
            self._toast_svc.info(
                f"Integridad: {len(result.changed_files)} archivos cambiados", self)
        elif result.passed:
            self._toast_svc.success(
                f"Integridad: {result.checked_files} archivos verificados, todo OK", self)
        else:
            self._toast_svc.info(
                f"Integridad: {result.checked_files} revisados", self)

    def _on_folder_toast(self, message: str, kind: str = "info"):
        if kind == "success":
            from ui.toast_notification import ToastNotification as T
            T.success(message, self)
        elif kind == "warning":
            from ui.toast_notification import ToastNotification as T
            T.warning(message, self)
        elif kind == "error":
            from ui.toast_notification import ToastNotification as T
            T.error(message, self)
        else:
            from ui.toast_notification import ToastNotification as T
            T.info(message, self)

    def _show_folder_problem_report(self, health):
        from ui.folders.folder_problem_report import show_problem_report
        show_problem_report(health, parent=self)

    def _on_safe_rename_folder(self, path: str):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        new_name, ok = QInputDialog.getText(
            self, "Renombrar carpeta",
            f"Nuevo nombre para:\n{os.path.basename(path)}",
            text=os.path.basename(path))
        if ok and new_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            from core.safe_file_ops import SafeFileOperations
            ops = SafeFileOperations(db=self._db)
            plan = ops.plan_move(path, new_path)
            if plan.can_proceed:
                result = ops.execute_move(plan)
                if result.success:
                    self._toast_svc.success(
                        f"Carpeta renombrada: {new_name}", self)
                    if hasattr(self, '_folder_browser'):
                        self._folder_browser._load(new_path)
                else:
                    QMessageBox.warning(self, "Error",
                        f"No se pudo renombrar: {result.error_message}")
            else:
                msg = "\n".join(plan.warnings + plan.conflicts)
                QMessageBox.warning(self, "No se puede renombrar",
                    f"Problemas:\n{msg}" if msg else "No se puede renombrar")

    def _on_safe_move_folder(self, path: str):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        new_parent = QFileDialog.getExistingDirectory(
            self, "Mover carpeta a...", os.path.dirname(path))
        if not new_parent:
            return
        new_path = os.path.join(new_parent, os.path.basename(path))
        from core.safe_file_ops import SafeFileOperations
        ops = SafeFileOperations(db=self._db)
        plan = ops.plan_move(path, new_path)
        if not plan.can_proceed:
            msg = "\n".join(plan.warnings + plan.conflicts)
            QMessageBox.warning(self, "No se puede mover",
                f"Problemas:\n{msg}" if msg else "No se puede mover")
            return
        confirm = QMessageBox.question(
            self, "Confirmar movimiento",
            f"\u00bfMover '{os.path.basename(path)}' a '{new_parent}'?\n\n"
            f"Archivos: {plan.files_to_move}\n"
            f"Items en DB: {plan.affected_media_items}\n"
            f"Playlists: {len(plan.affected_playlists)}",
            QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            result = ops.execute_move(plan)
            if result.success:
                self._toast_svc.success(
                    f"Carpeta movida a {new_parent}", self)
                if hasattr(self, '_folder_browser'):
                    self._folder_browser._load(new_path)
            else:
                QMessageBox.warning(self, "Error",
                    f"No se pudo mover: {result.error_message}")

    def _on_backend_changed(self, old_id: str, new_id: str):
        from ui.toast_notification import ToastNotification as T
        T.info(f"Motor de audio: {old_id} → {new_id}", self)
        if new_id == "mpd":
            self._toast_svc.show(
                "MPD Hi-Fi activo — EQ, ReplayGain y Spectrum desactivados",
                timeout=5000)

    def _init_optional_services(self):
        """Music identifier, HomeAudioView, Snapcast, API, mDNS, enrichment, MPRIS."""
        import core.settings_manager as sm
        _log = logging.getLogger("michi.setup")

        # Music Identifier
        self._features.register("recognition", enabled=self._safe_mode is False)
        self._detection = self._safe_init("recognition",
            lambda: DetectionService(self._db, parent=self))
        self._identifier_view = self._get_view("identifier",
            lambda: MusicIdentifierView())
        if self._detection:
            from recognition.identifier_controller import IdentifierController
            self._identifier_ctrl = IdentifierController(self._db, self._detection, self)
            self._detection.set_worker_manager(self._workers)
        else:
            self._identifier_ctrl = None

        # HomeAudioView
        self._home_audio_view = self._get_view("home_audio",
            lambda: HomeAudioView())

        # Snapcast
        for key, _name, factory in [
            ("snapcast", "SnapServerManager",
             lambda: self._make_snapserver()),
            ("audio_capture", "AudioCaptureManager",
             lambda: self._make_audio_capture()),
            ("snap_discovery", "SnapClientDiscovery",
             lambda: self._make_snap_discovery()),
            ("group_manager", "GroupManager",
             lambda: self._make_group_manager()),
        ]:
            self._features.register(key, enabled=not self._safe_mode)
            svc = self._safe_init(key, factory)
            if key == "snapcast":
                self._snapserver = svc
            elif key == "audio_capture":
                self._audio_capture = svc
            elif key == "snap_discovery":
                self._snap_discovery = svc
            elif key == "group_manager":
                self._group_mgr = svc

        # Michi API
        self._features.register("michi_api",
            enabled=sm.get_bool("home_audio/michi_api_enabled") and not self._safe_mode)
        if self._features.is_enabled("michi_api"):
            self._michi_api = self._safe_init("michi_api",
                lambda: self._make_michi_api())
        else:
            self._michi_api = None

        # mDNS
        self._features.register("mdns",
            enabled=sm.get_bool("home_audio/mdns_enabled") and not self._safe_mode)
        if self._features.is_enabled("mdns"):
            self._mdns = self._safe_init("mdns",
                lambda: self._make_mdns())
        else:
            self._mdns = None

        # Local media server
        self._features.register("local_media",
            enabled=not self._safe_mode)
        self._local_media = self._safe_init("local_media",
            lambda: self._make_local_media())
        self._local_ip = self._resolve_lan_ip()

        # Artist enrichment
        self._features.register("enrichment",
            enabled=sm.get_bool("artist_enrichment/enabled") and not self._safe_mode)
        self._artist_enrich = self._safe_init("enrichment",
            lambda: self._make_artist_enrichment())

        # Album info repository
        from metadata.album_info_repository import AlbumInfoRepository
        self._album_repo = AlbumInfoRepository()

        # MPRIS
        self._features.register("mpris", enabled=not self._safe_mode)
        self._mpris_ctrl = self._safe_init("mpris",
            lambda: self._make_mpris())
        if self._mpris_ctrl:
            self._mpris = getattr(self._mpris_ctrl, 'adapter', None)
        else:
            self._mpris = None

        # TransmitManager
        self._transmit_mgr = TransmitManager(self)
        self._transmit_mgr.active_changed.connect(self._on_transmit_active_changed)
        self._shutdown.register("transmit", lambda: None)  # no explicit stop needed
        self._validate_nav_routes()

    def _validate_nav_routes(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        missing = []
        for key, method_name in NAV_ROUTES.items():
            if not hasattr(self, method_name):
                missing.append(f"{key} -> {method_name}")
        if missing:
            import logging
            logging.getLogger("michi.startup").warning(
                "NAV_ROUTES missing methods: %s", "; ".join(missing))

    def _load_initial_data(self):
        """Library loading, enrichment, tray — after everything is wired."""
        if self._safe_mode:
            self._toast_svc.show(
                "Modo seguro activado — servicios opcionales deshabilitados", "info")
        self._load_library()

        # Backfill scheduling is owned by LibraryController.load()
        # Keep FileWatcher start and folder browser indicator below

        # Start FileWatcher after library is loaded
        if not self._safe_mode and hasattr(self, '_file_watcher'):
            try:
                self._file_watcher.start()
            except Exception:
                logging.getLogger("michi.setup").warning("FileWatcher failed to start")

        # Update folder browser watcher indicator
        if (hasattr(self, '_file_watcher') and hasattr(self, '_folder_browser')
                and self._file_watcher and self._folder_browser):
            self._folder_browser.set_watcher_active(self._file_watcher.is_running)

        if (hasattr(self, '_artist_enrich') and self._artist_enrich
                and hasattr(self._artist_repo, 'groups')):
            from core.settings_manager import get_bool
            if get_bool("artist_enrichment/enabled"):
                self._artist_enrich.enrich_visible_artists(
                    self._artist_repo.groups, limit=20)

        self._setup_tray()
        if not self._initial_route_applied:
            self._initial_route_applied = True
            from PySide6.QtCore import QTimer
            from ui.controllers.navigation_controller import INITIAL_ROUTE
            QTimer.singleShot(0, lambda: self._nav_ctrl.dispatch(INITIAL_ROUTE))

    # ── Safe init helper ──

    def _safe_init(self, name: str, factory):
        """Initialize an optional feature. Returns service or None if disabled/failed."""
        if not self._features.is_enabled(name):
            _log = logging.getLogger("michi.setup")
            _log.debug("%s skipped — feature disabled", name)
            return None
        try:
            svc = factory()
            self._features.mark_available(name)
            return svc
        except Exception as e:
            _log = logging.getLogger("michi.setup")
            _log.warning("%s init failed — disabled: %s", name, e)
            self._features.mark_error(name, str(e))
            return None

    def _get_view(self, key: str, factory) -> QWidget:
        """Lazy-load a view widget via the ViewRegistry (safe-mode gated)."""
        if not self._view_registry.has(key):
            self._view_registry.register(key, factory)
        view = self._view_registry.get(key)
        if view is None:
            from ui.safe_view_factory import safe_create_view
            view = safe_create_view(key, factory, title=key)
        return view

    # ── Optional service factories ──

    def _make_snapserver(self):
        from integrations.snapcast.snapserver_manager import SnapServerManager
        svc = SnapServerManager(self)
        svc.started.connect(self._ha_handlers.on_snapserver_started)
        svc.stopped.connect(self._ha_handlers.on_snapserver_stopped)
        svc.error_occurred.connect(self._ha_handlers.on_snapserver_error)
        self._shutdown.register("snapserver", lambda: svc.stop())
        return svc

    def _make_audio_capture(self):
        from integrations.snapcast.audio_capture import AudioCaptureManager
        svc = AudioCaptureManager(self)
        svc.sink_ready.connect(self._ha_handlers.on_audio_sink_ready)
        svc.error_occurred.connect(self._ha_handlers.on_snapserver_error)
        self._shutdown.register("audio_capture", lambda: svc.remove_sink()
                                if hasattr(svc, 'remove_sink') else None)
        return svc

    def _make_snap_discovery(self):
        from integrations.snapcast.discovery import SnapClientDiscovery
        svc = SnapClientDiscovery(self)
        svc.clients_found.connect(self._ha_handlers.on_snap_clients_found)
        return svc

    def _make_group_manager(self):
        from integrations.snapcast.group_manager import GroupManager
        svc = GroupManager(self)
        svc.groups_changed.connect(self._ha_handlers.on_groups_changed)
        return svc

    def _make_michi_api(self):
        return self._michi_link_ctrl.make_michi_api()

    def _make_mdns(self):
        return self._michi_link_ctrl.make_mdns()

    def _make_local_media(self):
        from integrations.home_assistant.local_media_server import LocalMediaServer
        svc = LocalMediaServer(self)
        self._shutdown.register("local_media", lambda: svc.stop())
        return svc

    def _make_artist_enrichment(self):
        from integrations.artist_metadata.artist_enrichment_service import ArtistEnrichmentService
        from core.settings_manager import get_bool
        svc = ArtistEnrichmentService(self)
        svc.configure(enabled=get_bool("artist_enrichment/enabled"))
        return svc

    def _make_mpris(self):
        from ui.controllers.mpris_controller import MPRISController
        svc = MPRISController(self)
        svc.init()
        self._shutdown.register("mpris", lambda: svc.shutdown()
                                if hasattr(svc, 'shutdown') else None)
        return svc

    def _wire_home_audio_signals(self):
        self._ha_handlers.wire_signals()

    def _wire_identifier_signals(self):
        if getattr(self, '_id_handlers', None):
            self._id_handlers.wire_signals()

    def _wire_enrichment_signals(self):
        if not getattr(self, '_artist_enrich', None) or not getattr(self, '_artist_ctrl', None):
            return
        self._artist_enrich.artist_enriched.connect(
            self._artist_ctrl.on_artist_enriched)
        self._artist_enrich.artist_image_loaded.connect(
            self._artist_ctrl.on_artist_image_loaded)
        self._artist_enrich.enrichment_failed.connect(
            self._artist_ctrl.on_artist_enrichment_failed)

    def _setup_actions(self):
        from ui.controllers.action_controller import ActionController
        self._action_ctrl = ActionController(self)
        self._action_ctrl.setup()

    # _lazy_hub removed — migrated to HubRouteController

    def _ensure_sync_manager(self):
        return self._michi_link_ctrl.ensure_sync_manager()

    def _show_preferences(self, section: str = ""):
        from ui.preferences_window import PreferencesWindow, PAGE_DEFS
        dlg = PreferencesWindow(self)
        dlg.settings_applied.connect(self._on_settings_applied)
        if section:
            for i, (_name, key, _icon) in enumerate(PAGE_DEFS):
                if key == section:
                    dlg._nav.setCurrentRow(i)
                    break
        dlg.exec()

    def _on_settings_applied(self, settings: dict):
        if self._toast_svc:
            self._toast_svc.show("Preferencias aplicadas", "info")

    def _show_shortcuts(self):
        shortcuts = [
            ("Ctrl+O", "Abrir archivos"),
            ("Ctrl+D", "Añadir carpeta"),
            ("Space", "Reproducir / Pausar"),
            ("Ctrl+Right", "Siguiente canción"),
            ("Ctrl+Left", "Canción anterior"),
            ("Ctrl+Up", "Subir volumen"),
            ("Ctrl+Down", "Bajar volumen"),
            ("Ctrl+M", "Silenciar"),
            ("Ctrl+F", "Buscar"),
            ("Alt+Left", "Navegar atrás"),
            ("Alt+Right", "Navegar adelante"),
            ("Ctrl+P", "Preferencias"),
            ("Ctrl+Q", "Salir"),
        ]
        text = "<table>"
        text += "<tr><th style='text-align:left;padding:4px 12px;color:#8FB7FF'>Atajo</th>" \
                "<th style='text-align:left;padding:4px 12px;color:#8FB7FF'>Acción</th></tr>"
        for key, action in shortcuts:
            text += f"<tr><td style='padding:3px 12px'>{key}</td>" \
                    f"<td style='padding:3px 12px;color:rgba(245,245,247,0.7)'>{action}</td></tr>"
        text += "</table>"
        QMessageBox.information(self, "Atajos de teclado", text)

    def _show_about(self):
        QMessageBox.about(self, "Acerca de",
            "<h2>Michi Music Player</h2><p>Sincronización Android, ecualizador paramétrico, "
            "CoverFlow 3D, streaming Navidrome/Jellyfin.</p>"
            "<p>Python 3 · PySide6 · GStreamer</p>")

    def _setup_ui(self):
        from ui.builder.ui_builder import UIBuilder
        UIBuilder(self).build()

    def _connect_signals(self):
        pb = self._player_bar
        self._playback.position_changed.connect(pb.set_position)
        self._playback.duration_changed.connect(pb.set_duration)
        self._playback.state_changed.connect(
            lambda state: self._playback_ctrl.on_state(state))
        self._playback.error_occurred.connect(lambda m: self._toast_svc.show(f"Error: {m}", "error"))
        pb.play_clicked.connect(self._playback.toggle)
        pb.prev_clicked.connect(self._playback.play_prev)
        pb.next_clicked.connect(self._playback.play_next)
        pb.shuffle_clicked.connect(
            self._playback_ctrl.toggle_shuffle_with_context
            if self._playback_ctrl else self._playback.toggle_shuffle)
        pb.repeat_clicked.connect(
            self._playback_ctrl.toggle_repeat_with_context
            if self._playback_ctrl else self._playback.toggle_repeat)
        pb.seek_requested.connect(self._playback.seek)
        pb.volume_changed.connect(self._playback.set_volume)
        pb.eq_clicked.connect(self._playback_ctrl.open_eq)
        pb.cover_preview_requested.connect(self._show_cover_preview)
        pb.track_details_requested.connect(self._show_nowplaying_details)
        pb.expanded_requested.connect(
            lambda: self._expanded_ctrl.show_expanded())
        pb.transmit_clicked.connect(self._show_transmit_menu)
        pb.audio_output_clicked.connect(self._show_audio_output_menu)
        pb.mini_player_clicked.connect(self._mini_player_ctrl.open)
        pb.cover_loaded.connect(self._bg_theme.apply)
        pb.quality_details_requested.connect(self._show_audio_diagnostics)

        # Wire context service
        if self._playback_ctrl:
            self._playback_ctrl.connect_context_events(
                self._playback, self._context_svc)

    def _setup_tray(self):
        from ui.controllers.tray_controller import TrayController
        self._tray_ctrl = TrayController(self)
        self._tray_ctrl.setup()
        self._tray = self._tray_ctrl.icon

    def _notify_track(self, title: str, artist: str):
        if hasattr(self, '_tray_ctrl') and self._tray_ctrl:
            self._tray_ctrl.notify(title, artist)

    def _setup_shortcuts(self):
        from ui.controllers.shortcut_controller import ShortcutController
        self._shortcut_ctrl = ShortcutController(self)
        self._shortcut_ctrl.setup()

    # ── Library ──

    def _load_library(self):
        self._lib_ctrl.load()

    def _apply_filters(self):
        self._lib_ctrl.apply_filters()

    # ── Sidebar ──

    def _rebuild_sidebar(self):
        sync_peers = []
        mgr = getattr(self, '_sync_mgr', None)
        if mgr and getattr(mgr, 'is_active', False):
            try:
                sync_peers = mgr.get_all_peers()
            except Exception:
                logging.getLogger("michi").debug("Failed to get sync peers for sidebar")
        self._sidebar_controller.rebuild(load_servers(), sync_peers)

        # Restaurar sidebar activo tras rebuild (sub-secciones mapean al hub padre)
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        current = getattr(self, "_current_sidebar_key", None)
        if not current:
            current = resolve_sidebar_active_key(getattr(self, "_current_route_key", "home"))
        self._sidebar_controller.set_active(current)

    # ── Static route handlers ──

    def _show_playlist_hub(self, key):
        self._playlist_ctrl.show_playlist_hub(key)

    def _show_metadata_editor(self, key):
        self._fade_content("metadata_editor")

    def _show_playlist_detail(self, key):
        self._playlist_ctrl.show_playlist_detail(key)

    def _on_playlist_track_activated(self, row: int, filepath: str):
        self._playlist_ctrl.on_playlist_track_activated(row, filepath)

    def _show_artists(self, key):
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("artists")

    def _show_albums(self, key):
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("albums")

    def _show_genres(self, key):
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("genres")
        if self._genre_ctrl:
            self._genre_ctrl.show_genres_hub()

    def _show_folders(self, key):
        self._lib_ctrl.show_folders(key)

    def _show_radio(self, key):
        self._srv_ctrl.show_radio(key)
    def _show_add_server(self, key):
        self._srv_ctrl.add_server()

    def _show_server(self, key):
        name = key.split(":", 1)[1]
        self._srv_ctrl.open_server(name)

    def _show_device(self, key):
        self._devices_ctrl.show_device(key)

    def _show_discover(self, key):
        self._fade_content("discover")

    def _show_smart_mix(self, key):
        self._smart_ctrl.show_smart_mix(key)
    def _show_favs(self, key):
        self._smart_ctrl.show_favs(key)
    def _show_recent(self, key):
        self._smart_ctrl.show_recent(key)
    def _show_identifier(self, key):
        self._id_handlers.show(key)
    def _show_home_audio(self, key=None):
        self._fade_content("home_audio")
        if self._home_audio_view and self._home_audio_view._needs_refresh:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self._home_audio_view.refresh_if_needed)

    def _show_assistant(self, key=None):
        self._hub_route_ctrl.show_assistant(key)

    def _show_michi_ai_page(self, key=None):
        self._hub_route_ctrl.show_michi_ai_page(key)

    def _on_assistant_state(self, state: str):
        if self._assistant_panel:
            self._assistant_panel.set_thinking(state == "thinking")

    def _on_assistant_response(self, response):
        if not self._assistant_panel:
            return
        if isinstance(response, dict):
            self._assistant_panel.add_response(response)
            data = response.get("data") if isinstance(response, dict) else None
            if data and isinstance(data, dict) and data.get("_navigate"):
                self._on_sidebar_navigate(data["_navigate"])
        else:
            self._assistant_panel.add_message_r(str(response))

    def _show_metadata_review(self, key=None):
        self._hub_route_ctrl.show_metadata_review(key)

    def _show_audio_lab(self, key=None):
        self._hub_route_ctrl.show_audio_lab(key)

    def _show_audio_lab_diagnostics(self, key=None):
        self._hub_route_ctrl.show_audio_lab_diagnostics(key)

    def _show_audio_lab_bitperfect_monitor(self, key=None):
        self._hub_route_ctrl.show_audio_lab_bitperfect_monitor(key)

    def _show_audio_lab_identifier(self, key=None):
        self._hub_route_ctrl.show_audio_lab_identifier(key)

    def _show_audio_lab_backup(self, key=None):
        self._hub_route_ctrl.show_audio_lab_backup(key)

    def _show_audio_lab_output(self, key=None):
        self._hub_route_ctrl.show_audio_lab_output(key)

    def _show_audio_lab_intelligence(self, key=None):
        self._hub_route_ctrl.show_audio_lab_intelligence(key)

    def _show_audio_lab_lyrics(self, key=None):
        self._hub_route_ctrl.show_audio_lab_lyrics(key)

    def _show_audio_lab_artwork(self, key=None):
        self._hub_route_ctrl.show_audio_lab_artwork(key)

    def _show_audio_lab_musicbrainz(self, key=None):
        self._hub_route_ctrl.show_audio_lab_musicbrainz(key)

    def _show_audio_lab_organize(self, key=None):
        self._hub_route_ctrl.show_audio_lab_organize(key)

    def _show_audio_lab_conversion(self, key=None):
        self._hub_route_ctrl.show_audio_lab_conversion(key)

    def _show_audio_lab_vinyl_lab(self, key=None):
        self._hub_route_ctrl.show_audio_lab_vinyl_lab(key)

    def _show_michi_disc_lab(self, key=None):
        self._hub_route_ctrl.show_michi_disc_lab(key)

    def _show_genre_cleanup(self, key=None):
        self._show_library_hub_page()
        if self._genre_ctrl:
            self._genre_ctrl.show_cleanup_page()

    def _show_album_detail_route(self, album_key: str):
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("albums")
        w = self
        if hasattr(w, '_album_ctrl') and w._album_ctrl:
            from library.album_art import CoverFlowItem
            repo = getattr(w, '_album_data_repo', None)
            group = repo.get_group(album_key) if repo else None
            if group:
                from PySide6.QtGui import QPixmap
                fake = CoverFlowItem(
                    pixmap=QPixmap(1, 1), title=group.identity.display_title,
                    subtitle=group.identity.display_artist,
                    data={"album_group": group, "album_key": album_key,
                          "tracks": group.tracks},
                )
                w._album_ctrl.show_album_detail_from_cover_item(fake)

    def _show_artist_detail_route(self, artist_key: str):
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("artists")
        if hasattr(self, '_artist_ctrl') and self._artist_ctrl:
            self._artist_ctrl.open_artist_detail(artist_key)

    def _show_genre_detail_route(self, genre_key: str):
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("genres")
        if hasattr(self, '_genre_ctrl') and self._genre_ctrl:
            self._genre_ctrl.open_genre_detail(genre_key)

    def _show_home_page(self, key=None):
        self._home_ctrl.show()

    def _show_library_hub_page(self, key=None):
        self._lib_ctrl.show_library_hub(key)

    def _on_library_tab_changed(self, section_key: str, force: bool = False):
        self._lib_ctrl._on_library_tab_changed(section_key, force)

    def _show_mix_hub_page(self, key=None):
        self._hub_route_ctrl.show_mix_hub(key)

    def _show_playback_hub_page(self, key=None):
        self._hub_route_ctrl.show_playback_hub(key)

    def _show_connections_hub_page(self, key=None):
        self._hub_route_ctrl.show_connections_hub(key)

    def _show_settings_hub_page(self, key=None):
        self._hub_route_ctrl.show_settings_hub(key)

    def _show_devices_page(self, key=None):
        self._hub_route_ctrl.show_devices_page(key)

    def _show_ecosystem_page(self, key=None):
        self._hub_route_ctrl.show_ecosystem_page(key)

    def _show_new_playlist(self, key):
        self._sidebar_menu_ctrl.create_playlist()

    # ── Michi API Bridge handlers ──

    @staticmethod
    def state_to_str(state) -> str:
        if state is None:
            return "idle"
        return str(state).split(".")[-1].lower() if "." in str(state) else str(state).lower()

    def _on_api_play_media(self, body: dict):
        media_id = body.get("media_id", "")
        if media_id and self._playback:
            self._playback.play(media_id, body.get("title", ""), body.get("artist", ""))

    def _on_api_select_dest(self, dest_id: str):
        if dest_id == "local":
            if hasattr(self, '_ctx') and hasattr(self._ctx, 'player_bar'):
                self._ctx.player_bar.set_transmit_active(False)
        elif hasattr(self, '_group_mgr'):
            self._group_mgr.activate_group(dest_id)

    def _on_api_library_play(self, body: dict):
        media_id = body.get("media_id", "")
        if media_id and self._playback:
            self._playback.play(media_id)
    def _on_search_results(self, results):
        self._search_router.on_results(results)
    def _current_available_views(self) -> list[str]:
        config = _resolve_section_config(self._current_section_key, {})
        return config.get("views", [])

    def _show_current_section_view(self, mode: str):
        self._view_router._show_current_section_view(mode)

    def _configure_header_for_section(self, section_key: str):
        self._nav_ctrl.configure_header(section_key)

    def _setup_album_sort_menu(self):
        self._album_sort_menu.build_sort()

    def _setup_album_filter_menu(self):
        self._album_sort_menu.build_filter()

    def _fade_content(self, target: str):
        self._nav.show(target)

    def _restore_central_opacity(self):
        self._nav.restore_opacity()

    def _on_album_open_folder(self, folder):
        self._album_ctrl.open_folder(folder)

    def _on_view_mode_changed(self, mode):
        self._view_router.on_mode_changed(mode)

    def _show_expanded(self):
        self._expanded_ctrl.show_expanded()

    def _on_radio_count(self, visible, total):
        self._srv_ctrl.on_radio_count(visible, total)

    def _play_radio(self, url, name):
        self._srv_ctrl.play_radio(url, name)

    def _on_sidebar_navigate(self, key):
        self._nav_ctrl.dispatch(key)
    def _show_album_grid(self):
        self._lib_ctrl.show_album_grid()

    def _show_song_grid(self):
        self._lib_ctrl.show_song_grid()


    def _show_coverflow(self):
        self._cf_ctrl.show()
    def _on_metadata_saved(self, filepaths: list):
        self._playlist_ctrl.metadata_saved(filepaths)
        self._reload_library_after_change(reason="metadata_saved")

    def _reload_library_after_change(self, reason: str = ""):
        self._lib_ctrl.reload_after_change(reason)

    # Extracted to ui/controllers/artist_controller.py — grid + detail logic

    def _show_artists_view(self, mode: str):
        self._artist_ctrl.show_artists_view(mode)
    def _refresh_artist_info(self, artist_key: str):
        self._artist_ctrl.refresh_artist_info(artist_key)
    # Extracted to ui/controllers/artist_controller.py — enrichment signal handlers

    # Extracted to ui/controllers/expanded_controller.py — now playing expanded

    def _show_cover_preview(self):
        from ui.builder.inline_dialogs import show_cover_preview
        pixmap = getattr(getattr(self, '_player_bar', None), '_cover', None)
        pm = pixmap.pixmap() if pixmap and hasattr(pixmap, 'pixmap') else None
        show_cover_preview(self, pm)

    def _show_nowplaying_details(self):
        from PySide6.QtGui import QCursor
        from ui.builder.inline_dialogs import show_nowplaying_details
        show_nowplaying_details(self, QCursor.pos(), self._current_ref)

    def _open_metadata_for_files(self, filepaths: list[str]):
        self._artist_ctrl.open_metadata_for_files(filepaths)

    # ── FileWatcher handlers ──

    # FileWatcher handlers moved to LibraryWatcherController.
    # Signals connected in _init_controllers().

    def _scan_path(self, path: str):
        self._file_actions.scan_path(path)

    # Extracted to core/playback_controller.py — play/pause/queue logic
    def _play_filepaths(self, filepaths: list[str], play_now: bool = True):
        """Centralized playback entry point — ensures all tracks go through _play_trackref."""
        self._playback_ctrl.play_filepaths(filepaths, play_now=play_now)

    def _on_folder_selected(self, fps: list[str]):
        ctx = self._context_svc
        folder_name = "Carpeta seleccionada"
        try:
            if fps:
                common = os.path.commonpath(fps)
                folder_name = os.path.basename(common.rstrip("/")) or folder_name
        except Exception:
            pass
        if ctx:
            ctx.update_selection(
                scope="folder", folder_name=folder_name,
                album="", artist="", genre="",
                playlist_id=None, playlist_name="",
                mix_key="", search_query="",
            )
            ctx.record_folder_selected(folder_name=folder_name, count=len(fps))
        self._play_filepaths(fps, play_now=True)

    def _on_folder_queued(self, fps: list[str]):
        ctx = self._context_svc
        folder_name = "Carpeta seleccionada"
        try:
            if fps:
                common = os.path.commonpath(fps)
                folder_name = os.path.basename(common.rstrip("/")) or folder_name
        except Exception:
            pass
        if ctx:
            ctx.update_selection(
                scope="folder", folder_name=folder_name,
                album="", artist="", genre="",
                playlist_id=None, playlist_name="",
                mix_key="", search_query="",
            )
            ctx.record_folder_queued(folder_name=folder_name, count=len(fps))
        self._play_filepaths(fps, play_now=False)

    def _on_folder_scan_requested(self, path: str):
        ctx = self._context_svc
        if ctx:
            ctx.update_selection(
                scope="folder",
                folder_name=os.path.basename(path.rstrip("/")),
                album="", artist="", genre="",
                playlist_id=None, playlist_name="",
                mix_key="", search_query="",
            )
            ctx.record_folder_scanned(folder_name=path)
        self._scan_path(path)

    def _play_trackref(self, track: TrackRef):
        # Notify identifier controller of source change
        if hasattr(self, '_identifier_ctrl') and self._identifier_ctrl:
            self._identifier_ctrl.set_current_track(
                source_type=track.source_type,
                source_label=track.source_label,
                uri=track.uri,
                title=track.title,
                artist=track.artist)
        self._playback_ctrl.play_trackref(track)

    def _play_file(self, filepath: str, add_to_queue: bool = False):
        self._playback_ctrl.play_file(filepath, add_to_queue)

    def _toggle_favorite_by_filepath(self, filepath: str, songs_ctrl):
        from library.library_db import MediaItem
        item = MediaItem(filepath=filepath)
        songs_ctrl.toggle_favorite(item)

    def _show_song_context_menu(self, filepath: str, pos):
        from PySide6.QtWidgets import QMenu
        from ui.central.central_styles import menu_qss
        menu = QMenu(self)
        menu.setStyleSheet(menu_qss())

        play_act = menu.addAction("Reproducir")
        queue_act = menu.addAction("Añadir a la cola")
        menu.addSeparator()
        locate_act = menu.addAction("Localizar archivo")
        menu.addSeparator()
        fav_act = menu.addAction("Favorito / Quitar favorito")
        metadata_act = menu.addAction("Editar metadatos")

        action = menu.exec(pos)
        if action == play_act:
            self._play_file(filepath)
        elif action == queue_act:
            self._play_file(filepath, add_to_queue=True)
        elif action == locate_act:
            from core.file_actions import open_containing_folder
            open_containing_folder(filepath)
        elif action == fav_act:
            songs_ctrl = getattr(self, '_songs_ctrl', None)
            if songs_ctrl and hasattr(songs_ctrl, 'toggle_favorite'):
                self._toggle_favorite_by_filepath(filepath, songs_ctrl)
        elif action == metadata_act and hasattr(self, '_open_metadata_for_files'):
            self._open_metadata_for_files([filepath])
    # Streaming/Cast/AudioOutput — now split into focused controllers
    # CastController → unified transmit menu (local + net + snapcast + HA)
    # AudioOutputController → local output device selection
    # SnapcastController → Snapcast zone lifecycle
    # HomeAudioController → Home Assistant casting
    # TransmitController → TransmitManager devices (add/manage/activate)
    # LocalMediaServerController → local HTTP file server lifecycle
    # MiniPlayerController → mini player window lifecycle

    def _show_transmit_menu(self):
        self._cast_ctrl.show_cast_menu()

    def _on_transmit_active_changed(self):
        self._transmit_ctrl.on_active_changed()

    def _show_audio_output_menu(self):
        self._audio_output_ctrl.show_menu()

    def _show_audio_diagnostics(self):
        from ui.builder.inline_dialogs import show_audio_diagnostics
        show_audio_diagnostics(self, self._playback)

    # ── Home Audio ──

    @staticmethod
    def _resolve_lan_ip() -> str:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return ""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0, QColor(18, 18, 21))
        grad.setColorAt(0.5, QColor(15, 15, 18))
        grad.setColorAt(1, QColor(12, 12, 14))
        painter.fillRect(rect, grad)
        # subtle noise texture — pre-rendered 4x4 tile
        if not hasattr(MainWindow, '_noise_tile'):
            noise = QImage(4, 4, QImage.Format_Grayscale8)
            for y in range(4):
                for x in range(4):
                    noise.setPixel(x, y, random.randint(0, 5))
            MainWindow._noise_tile = noise
        painter.setOpacity(0.03)
        painter.drawImage(rect, MainWindow._noise_tile.scaled(rect.size()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_view_switcher'):
            self._view_switcher.update_for_width(self.width())

    def closeEvent(self, event):
        # Confirm exit if setting enabled
        from core.settings_manager import get_bool
        if get_bool("general/confirm_exit"):
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Cerrar Michi Music Player",
                "¿Estás seguro de que querés cerrar?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        # Cancel active scans
        if hasattr(self, '_file_actions') and self._file_actions:
            self._file_actions.cancel_all_scans()
        # Save queue state before shutdown
        try:
            paths, idx = self._playback.get_queue_state()
            if paths and self._db:
                self._db.save_queue(paths, idx)
        except Exception:
            logging.getLogger("michi").warning("Failed to save queue on close", exc_info=True)
        # Disconnect player signals to prevent leaks
        import contextlib
        with contextlib.suppress(TypeError, RuntimeError, AttributeError):
            self._playback.position_changed.disconnect()
        with contextlib.suppress(TypeError, RuntimeError, AttributeError):
            self._playback.duration_changed.disconnect()
        with contextlib.suppress(TypeError, RuntimeError, AttributeError):
            self._playback.state_changed.disconnect()
        # Record app_closed event
        ctx = getattr(self, '_context_svc', None)
        if ctx:
                    import contextlib
                    with contextlib.suppress(Exception):
                        self._bg_theme.update()
        self._shutdown.shutdown()
        event.accept()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    event.acceptProposedAction()
                    return
                ext = os.path.splitext(path)[1].lower()
                if ext in AUDIO_EXTS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        self._file_actions.add_files_by_drop(urls)
        files = [url.toLocalFile() for url in urls
                 if os.path.splitext(url.toLocalFile())[1].lower() in AUDIO_EXTS]
        if files:
            if len(files) == 1:
                self._play_file(files[0])
            else:
                self._play_filepaths(files, play_now=True)


def _album_key(item, tracks: list = None) -> str:
    """Stable SHA1 album key from albumartist/artist + album title."""
    import hashlib
    artist_val = ""
    album = item.title or ""
    if tracks:
        artist_val = getattr(tracks[0], 'albumartist', '') or getattr(
            tracks[0], 'artist', '') or ""
    if not artist_val and item.subtitle:
        artist_val = item.subtitle.split(" \u00b7 ")[0]
    raw = f"{artist_val}|{album}".lower().strip()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]
