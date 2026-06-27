"""MainWindow — 2 panels + nowplaying bar with library, EQ, and streaming."""

import os
import random
import logging
from PySide6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QPainter, QLinearGradient, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QMessageBox,
)



from ui.icons import app_icon
from audio.player import PlayerEngine
from library.library_db import (
    LibraryDB, DB_PATH, MediaItem,
    AUDIO_EXTS, ALL_EXTS,
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
        self._current_section_key: str = "library"
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
        self._album_repo = None
        self._audio_lab_page = None
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
        from ui.controllers.genre_repository import GenreRepository
        self._genre_repo = GenreRepository()
        from ui.controllers.genre_controller import GenreController
        self._genre_ctrl = GenreController(self, services=None)
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

        # AppServices before controllers that use them
        from core.app_services import AppServices
        svc = AppServices(
            db=self._db, playback=self._playback, player=self._player,
            model=self._model, toast=self._toast_svc,
            player_bar=getattr(self, '_player_bar_ctrl', None),
            features=self._features,
            artist_repo=self._artist_repo, genre_repo=self._genre_repo,
            fade_to=self._fade_content, navigate=self._on_sidebar_navigate,
            configure_header=self._configure_header_for_section,
            rebuild_sidebar=self._rebuild_sidebar,
            load_library=self._load_library, play_file=self._play_file,
        )
        self._services = svc

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
        if self._artist_enrich:
            self._artist_enrich.artist_enriched.connect(self._on_artist_enriched)
            self._artist_enrich.artist_image_loaded.connect(self._on_artist_image_loaded)
            self._artist_enrich.enrichment_failed.connect(self._on_artist_enrichment_failed)

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

        # FileWatcher — real-time monitoring of library roots
        from library.file_watcher import FileWatcher
        self._file_watcher = FileWatcher(self._db, parent=self)
        self._file_watcher.files_added.connect(self._on_watcher_files_added)
        self._file_watcher.files_removed.connect(self._on_watcher_files_removed)
        self._file_watcher.files_modified.connect(self._on_watcher_files_modified)
        self._shutdown.register("file_watcher", lambda: self._file_watcher.stop())
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

        # Backfill missing metadata after library load
        if not self._safe_mode and hasattr(self, '_workers'):
            self._workers.run_task("backfill_metadata",
                lambda: self._db.backfill_missing_metadata(), priority=5)
            self._workers.run_task("backfill_album_art",
                lambda: self._db.backfill_missing_album_art(), priority=5)

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
        from core.state_store import AppStateStore
        from integrations.http_api.bridge import MichiApiBridge
        from integrations.http_api.http_api import MichiHttpApi
        store = AppStateStore(self)
        bridge = MichiApiBridge(self)
        # Wire bridge signals to window handlers
        bridge.play_requested.connect(lambda: self._playback.play_or_resume())
        bridge.pause_requested.connect(lambda: self._playback.pause())
        bridge.stop_requested.connect(lambda: self._playback.stop())
        bridge.next_requested.connect(lambda: self._playback.play_next())
        bridge.previous_requested.connect(lambda: self._playback.play_prev())
        bridge.volume_requested.connect(lambda v: self._playback.set_volume(v))
        bridge.play_media_requested.connect(self._on_api_play_media)
        bridge.select_destination_requested.connect(self._on_api_select_dest)
        bridge.library_play_requested.connect(self._on_api_library_play)
        self._state_store = store
        self._api_bridge = bridge
        svc = MichiHttpApi(self)
        svc.configure()
        svc.set_store_and_bridge(store, bridge)
        # Update state store on player changes
        self._playback.state_changed.connect(
            lambda s: store.update_player(state=self._state_to_str(s)))
        self._playback.volume_changed.connect(
            lambda v: store.update_player(volume=v))
        self._shutdown.register("michi_api", lambda: svc.stop())
        return svc

    def _make_mdns(self):
        from integrations.http_api.mdns_advertiser import MDNSAdvertiser
        svc = MDNSAdvertiser(self)
        svc.configure()
        self._shutdown.register("mdns", lambda: svc.stop())
        return svc

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
        self._id_handlers.wire_signals()
    def _setup_actions(self):
        from PySide6.QtGui import QAction

        self._open_file_action = QAction("Abrir archivo...", self)
        self._open_file_action.setShortcut("Ctrl+O")
        self._open_file_action.triggered.connect(
            lambda: self._file_actions.open_files(ALL_EXTS))
        self.addAction(self._open_file_action)

        self._add_folder_action = QAction("Añadir carpeta...", self)
        self._add_folder_action.setShortcut("Ctrl+D")
        self._add_folder_action.triggered.connect(self._add_folder)
        self.addAction(self._add_folder_action)

        self._import_playlist_action = QAction("Importar playlist...", self)
        self._import_playlist_action.triggered.connect(self._import_playlist)
        self.addAction(self._import_playlist_action)

        self._export_playlist_action = QAction("Exportar playlist...", self)
        self._export_playlist_action.triggered.connect(self._export_playlist)
        self.addAction(self._export_playlist_action)

        self._sync_action = QAction("Activar sincronización Android", self)
        self._sync_action.setCheckable(True)
        self._sync_action.triggered.connect(self._toggle_sync)
        self.addAction(self._sync_action)

        self._preferences_action = QAction("Preferencias...", self)
        self._preferences_action.setShortcut("Ctrl+P")
        self._preferences_action.triggered.connect(self._show_preferences)
        self.addAction(self._preferences_action)

        back_action = QAction(self)
        back_action.setShortcut("Alt+Left")
        back_action.triggered.connect(lambda: self._nav_ctrl.navigate_back())
        self.addAction(back_action)

        forward_action = QAction(self)
        forward_action.setShortcut("Alt+Right")
        forward_action.triggered.connect(lambda: self._nav_ctrl.navigate_forward())
        self.addAction(forward_action)

        self._add_transmit_device_action = QAction("Añadir dispositivo...", self)
        self._add_transmit_device_action.triggered.connect(
            lambda: self._transmit_ctrl.add_device())
        self.addAction(self._add_transmit_device_action)

        self._manage_transmit_devices_action = QAction("Administrar dispositivos...", self)
        self._manage_transmit_devices_action.triggered.connect(self._manage_transmit_devices)
        self.addAction(self._manage_transmit_devices_action)

        self._shortcuts_action = QAction("Atajos de teclado", self)
        self._shortcuts_action.triggered.connect(self._show_shortcuts)
        self.addAction(self._shortcuts_action)

        self._about_action = QAction("Acerca de", self)
        self._about_action.triggered.connect(self._show_about)
        self.addAction(self._about_action)

        self._duplicates_action = QAction("Buscar duplicados...", self)
        self._duplicates_action.triggered.connect(self._show_duplicates)
        self.addAction(self._duplicates_action)

        self._quit_action = QAction("Salir", self)
        self._quit_action.setShortcut("Ctrl+Q")
        self._quit_action.triggered.connect(self.close)
        self.addAction(self._quit_action)

        self.menuBar().hide()

    def _ensure_sync_manager(self):
        """Lazy-create SyncManager with all signal wiring."""
        if hasattr(self, '_sync_mgr'):
            return self._sync_mgr
        from sync.sync_manager import SyncManager
        self._sync_mgr = SyncManager(self._db, self)
        self._sync_mgr.sync_started.connect(
            lambda p: self._sync_action.setText(
                f"✓ Sincronización activa (puerto {p})"))
        self._sync_mgr.sync_stopped.connect(
            lambda: self._sync_action.setText(
                "Activar sincronización Android"))
        self._sync_mgr.error_occurred.connect(
            lambda m: (self._toast_svc.show(f"Sync error: {m}", "error")
                       if self._toast_svc else None))
        self._sync_mgr.client_connected.connect(
            lambda d: (self._toast_svc.show(f"Dispositivo conectado: {d}", "info")
                       if self._toast_svc else None))
        self._sync_mgr.peer_found.connect(
            lambda a, ip: self._rebuild_sidebar())
        self._sync_mgr.peer_lost.connect(
            lambda a: self._rebuild_sidebar())
        return self._sync_mgr

    def _toggle_sync(self):
        mgr = self._ensure_sync_manager()
        if mgr.is_active:
            mgr.stop()
            self._sync_action.setChecked(False)
        else:
            mgr.start()
            self._sync_action.setChecked(True)

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
        self._player.position_changed.connect(pb.set_position)
        self._player.duration_changed.connect(pb.set_duration)
        self._player.state_changed.connect(
            lambda state: self._playback_ctrl.on_state(state))
        self._player.error_occurred.connect(lambda m: self._toast_svc.show(f"Error: {m}", "error"))
        pb.play_clicked.connect(self._playback.toggle)
        pb.prev_clicked.connect(self._playback.play_prev)
        pb.next_clicked.connect(self._playback.play_next)
        pb.shuffle_clicked.connect(self._playback.toggle_shuffle)
        pb.repeat_clicked.connect(self._playback.toggle_repeat)
        pb.seek_requested.connect(self._playback.seek)
        pb.volume_changed.connect(self._playback.set_volume)
        pb.eq_clicked.connect(self._open_eq)
        pb.cover_preview_requested.connect(self._show_cover_preview)
        pb.track_details_requested.connect(self._show_nowplaying_details)
        pb.expanded_requested.connect(
            lambda: self._expanded_ctrl.show_expanded())
        pb.transmit_clicked.connect(self._show_transmit_menu)
        pb.audio_output_clicked.connect(self._show_audio_output_menu)
        pb.mini_player_clicked.connect(self._open_mini_player)
        pb.cover_loaded.connect(self._bg_theme.apply)
        pb.quality_details_requested.connect(self._show_audio_diagnostics)

    def _setup_tray(self):
        from ui.controllers.tray_controller import TrayController
        self._tray_ctrl = TrayController(self)
        self._tray_ctrl.setup()
        self._tray = self._tray_ctrl.icon

    def _notify_track(self, title: str, artist: str):
        if hasattr(self, '_tray_ctrl') and self._tray_ctrl:
            self._tray_ctrl.notify(title, artist)

    def _import_playlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar playlist", os.path.expanduser("~"),
            "Playlists (*.m3u *.m3u8 *.pls);;Todos (*)")
        if not path:
            return
        from ui.playlist_io import parse_playlist_entries
        entries = parse_playlist_entries(path)
        if not entries:
            QMessageBox.information(
                self, "Importar", "No se encontraron entradas en la playlist.")
            return

        valid_files = []
        missing = 0
        remote = 0
        for e in entries:
            if e.is_remote:
                remote += 1
                continue
            if e.exists:
                self._db.add_file(e.resolved_path)
                valid_files.append(e.resolved_path)
            else:
                missing += 1

        self._load_library()
        if valid_files:
            self._playback.enqueue(valid_files, play_now=False)
        self._player_bar_ctrl.set_track(
                f"Importados {len(valid_files)} temas", "Playlist")

        summary = f"<p><b>{len(valid_files)}</b> archivos añadidos a la biblioteca.</p>"
        if missing:
            summary += f"<p><b>{missing}</b> archivos no encontrados en disco.</p>"
        if remote:
            summary += f"<p><b>{remote}</b> entradas remotas ignoradas.</p>"
        summary += f"<p>Total entradas en playlist: <b>{len(entries)}</b></p>"
        QMessageBox.information(self, "Importar playlist", summary)

    def _export_playlist(self):
        queue = self._playback.get_queue()
        if not queue:
            QMessageBox.information(
                self, "Exportar", "La cola de reproducción está vacía.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar playlist", "playlist.m3u",
            "M3U (*.m3u);;Todos (*)")
        if not path:
            return
        from ui.playlist_io import export_m3u
        export_m3u(path, [q["filepath"] for q in queue])
        QMessageBox.information(
            self, "Exportar", f"Playlist exportada a {path}")

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

        # Sidebar shadow
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setXOffset(3)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self._sidebar.setGraphicsEffect(shadow)

    # ── Static route handlers ──

    def _show_playlist_hub(self, key):
        pls = self._db.get_playlists()
        self._playlist_hub.set_playlists(pls)
        self._fade_content("playlist_hub")

    def _show_metadata_editor(self, key):
        self._fade_content("metadata_editor")

    def _show_playlist_detail(self, key):
        pid = int(key.split(":", 1)[1])
        self._current_playlist = pid
        items = self._db.get_playlist_items(pid)
        pl = next((p for p in self._db.get_playlists() if p["id"] == pid), {"name": "Playlist"})
        self._playlist_detail.set_playlist(pl, items)
        total_dur = int(sum(getattr(i, 'duration', 0) or 0 for i in items))
        h = total_dur // 3600
        m = (total_dur % 3600) // 60
        dur_str = f"{h} h {m} min" if h > 0 else f"{m} min" if m > 0 else ""
        subtitle = f"{len(items)} canciones"
        if dur_str:
            subtitle += f" · {dur_str}"
        self._section_title.setText(pl.get("name", "Playlist"))
        self._section_subtitle.setText(subtitle)
        self._search.show()
        self._fade_content("playlist_detail")

    def _on_playlist_track_activated(self, row: int, filepath: str):
        """Play entire playlist starting from the clicked track."""
        pid = getattr(self, '_current_playlist', 0)
        if not pid:
            return
        items = self._db.get_playlist_items(pid)
        paths = [i.filepath for i in items if getattr(i, 'filepath', '')]
        if not paths:
            return
        start_idx = max(0, min(row, len(paths) - 1))
        if hasattr(self._playback, 'play_queue'):
            self._playback.play_queue(paths, start_idx)
        else:
            self._play_filepaths(paths[start_idx:], play_now=True)

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

    def _show_folders(self, key):
        from sources.folder_source import FolderSource
        roots = self._db.get_library_roots() if self._db else []
        start_dir = roots[0] if roots else os.path.expanduser("~")
        self._search_ctrl.register("folders", FolderSource(start_dir, db=self._db))
        self._search_ctrl.set_active("folders")
        self._show_library_hub_page()
        if self._library_hub_page:
            self._library_hub_page.set_current_section("folders")

    def _show_radio(self, key):
        self._srv_ctrl.show_radio(key)
    def _show_add_server(self, key):
        self._add_server()

    def _show_server(self, key):
        name = key.split(":", 1)[1]
        self._open_server(name)

    def _show_device(self, key):
        mount = key.split(":", 1)[1]
        import shutil
        usage = shutil.disk_usage(mount) if os.path.exists(mount) else None
        device_name = os.path.basename(mount)

        self._section_title.setText(device_name)
        self._section_subtitle.setText("Escaneando dispositivo...")
        self._count.setText("...")
        self._search.hide()
        self._fade_content("library_hub")

        self._model.populate([])
        self._table.setModel(self._model)

        def _on_device_scanned(files: list[str]):
            if not hasattr(self, '_model') or self._current_section_key != "devices":
                return
            refs = [TrackRef(uri=fp, title=os.path.basename(fp), duration=0.0) for fp in files]
            self._model.populate(refs)
            self._current_refs = refs
            if usage:
                total_gb = usage.total / (1024**3)
                free_gb = usage.free / (1024**3)
                used_pct = (1 - usage.free / usage.total) * 100
                self._section_subtitle.setText(
                    f"{free_gb:.1f} GB libre de {total_gb:.1f} GB · "
                    f"{used_pct:.0f}% usado · {len(files)} canciones")
            else:
                self._section_subtitle.setText(f"{len(files)} canciones")
            self._count.setText(f"{len(files)} archivos")
            self._table.setColumnHidden(7, True)
            self._search.show()

        if self._workers:
            from library.devices import scan_device_music
            self._workers.run_task("device_scan", lambda: scan_device_music(mount),
                                   on_done=_on_device_scanned)
        else:
            from library.devices import scan_device_music
            _on_device_scanned(scan_device_music(mount))

    def _show_discover(self, key):
        self._fade_content("discover")

    def _show_smart_mix(self, key):
        self._smart_ctrl.show_smart_mix(key)
    def _show_favs(self, key):
        self._smart_ctrl.show_favs(key)
    def _show_recent(self, key):
        self._smart_ctrl.show_recent(key)
    def _resolve_track_ids(self, track_ids):
        return self._smart_ctrl.resolve_track_ids(track_ids)
    def _show_identifier(self, key):
        self._id_handlers.show(key)
    def _show_home_audio(self, key=None):
        self._home_audio_view.refresh_if_needed()
        self._fade_content("home_audio")

    def _show_assistant(self, key=None):
        if self._assistant_panel is None:
            from ui.ai_assistant_panel import AiAssistantPanel
            from ui.controllers.ai_assistant_controller import AiAssistantController
            self._assistant_panel = AiAssistantPanel()
            self._assistant_ctrl = AiAssistantController(
                db=self._db, worker_manager=self._workers,
                playback=self._playback,
                safe_mode=self._safe_mode,
                parent=self,
            )
            self._assistant_panel.send_requested.connect(
                self._assistant_ctrl.send_message,
            )
            self._assistant_ctrl.state_changed.connect(
                self._on_assistant_state,
            )
            self._assistant_ctrl.response_received.connect(
                self._on_assistant_response,
            )
            self._assistant_ctrl.navigate_to.connect(
                self._on_sidebar_navigate,
            )
            self._assistant_panel.action_confirmed.connect(
                self._assistant_ctrl.confirm_action,
            )
            self._assistant_panel.action_cancelled.connect(
                self._assistant_ctrl.cancel_action,
            )
            available = self._assistant_ctrl.check_health() if self._assistant_ctrl.is_enabled() else False
            self._assistant_panel.set_ollama_status(
                available, self._assistant_ctrl.model() if self._assistant_ctrl.is_enabled() else "",
            )
        if not self._views.widget("assistant"):
            self._views.register("assistant", self._assistant_panel)
        self._fade_content("assistant")

    def _on_assistant_state(self, state: str):
        self._assistant_panel.set_thinking(state == "thinking")

    def _on_assistant_response(self, response):
        if isinstance(response, dict):
            self._assistant_panel.add_response(response)
            data = response.get("data") if isinstance(response, dict) else None
            if data and isinstance(data, dict) and data.get("_navigate"):
                self._on_sidebar_navigate(data["_navigate"])
        else:
            self._assistant_panel.add_message_r(str(response))

    def _show_metadata_review(self, key=None):
        if self._metadata_review_panel is None:
            from ui.metadata_review_panel import MetadataReviewPanel
            from ui.controllers.metadata_review_controller import MetadataReviewController
            self._metadata_review_panel = MetadataReviewPanel()
            self._metadata_review_ctrl = MetadataReviewController(
                db=self._db, parent=self,
            )
            self._metadata_review_panel.review_apply_requested.connect(
                lambda rid, af: self._metadata_review_ctrl.apply_review(rid, af),
            )
            self._metadata_review_panel.review_reject_requested.connect(
                self._metadata_review_ctrl.reject_review,
            )
            self._metadata_review_ctrl.apply_result.connect(
                lambda r: self._toast_svc.show(
                    f"Metadata: {r.get('applied',0)} cambios aplicados, "
                    f"{r.get('skipped',0)} omitidos", "info",
                ) if self._toast_svc else None,
            )
        if not self._views.widget("metadata_review"):
            self._views.register("metadata_review", self._metadata_review_panel)
        self._fade_content("metadata_review")

    def _show_audio_lab(self, key=None):
        if self._audio_lab_page is None:
            from ui.audio_lab.audio_lab_page import AudioLabPage
            self._audio_lab_page = AudioLabPage()
            self._audio_lab_page.navigate_requested.connect(self._on_sidebar_navigate)
        if not self._views.widget("audio_lab"):
            self._views.register("audio_lab", self._audio_lab_page)
        self._fade_content("audio_lab")

    def _show_michi_disc_lab(self, key=None):
        if self._michi_disc_lab_page is None:
            from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
            self._michi_disc_lab_page = MichiDiscLabPage()
        if not self._views.widget("michi_disc_lab"):
            self._views.register("michi_disc_lab", self._michi_disc_lab_page)
        self._fade_content("michi_disc_lab")

    def _show_home_page(self, key=None):
        self._home_ctrl.show()

    def _show_library_hub_page(self, key=None):
        if self._library_hub_page is None:
            from ui.hubs.library_hub_page import LibraryHubPage
            self._library_hub_page = LibraryHubPage(
                db=self._db, window=self,
                songs_widget=self._songs_stack,
                albums_widget=self._albums_stack,
                artists_widget=self._artists_stack,
                genres_widget=self._genres_stack,
                folders_widget=self._folder_browser)
            self._library_hub_page.tab_changed.connect(
                self._on_library_tab_changed)
        if not self._views.widget("library_hub"):
            self._views.register("library_hub", self._library_hub_page)
        self._fade_content("library_hub")

    def _on_library_tab_changed(self, section_key: str, force: bool = False):
        if section_key == getattr(self, '_last_lib_tab', None) and not force:
            return
        self._last_lib_tab = section_key
        self._current_section_key = section_key if section_key in ("library", "albums", "artists", "genres", "folders") else self._current_section_key
        config = _resolve_section_config(section_key, {})
        views = config.get("views", [])
        default = config.get("default", "list")
        self._view_switcher.show()
        self._view_switcher.set_available_modes(views, default, context=section_key)

        # Lazy-load data for the active tab
        if section_key == "albums":
            self._show_album_grid()
        elif section_key == "artists":
            self._artist_repo.clear_current()
            self._artist_repo.build(self._all_items)
            self._artist_grid.set_artists(self._artist_repo.groups)
        elif section_key == "genres":
            self._refresh_genres_data()
        elif section_key == "library":
            self._apply_filters()

    def _show_mix_hub_page(self, key=None):
        if self._mix_hub_page is None:
            from ui.hubs.mix_hub_page import MixHubPage
            self._mix_hub_page = MixHubPage(preview=self._smart_preview)
        if not self._views.widget("mix_hub"):
            self._views.register("mix_hub", self._mix_hub_page)
        self._mix_hub_page.refresh()
        self._fade_content("mix_hub")

    def _show_playback_hub_page(self, key=None):
        if self._playback_hub_page is None:
            from ui.hubs.playback_hub_page import PlaybackHubPage
            self._playback_hub_page = PlaybackHubPage(db=self._db, playback=self._playback)
        if not self._views.widget("playback_hub"):
            self._views.register("playback_hub", self._playback_hub_page)
        self._fade_content("playback_hub")

    def _show_connections_hub_page(self, key=None):
        if self._connections_hub_page is None:
            from ui.hubs.connections_hub_page import ConnectionsHubPage
            self._connections_hub_page = ConnectionsHubPage()
        if not self._views.widget("connections_hub"):
            self._views.register("connections_hub", self._connections_hub_page)
        self._fade_content("connections_hub")

    def _show_settings_hub_page(self, key=None):
        if self._settings_hub_page is None:
            from ui.hubs.settings_hub_page import SettingsHubPage
            self._settings_hub_page = SettingsHubPage()
        if not self._views.widget("settings_hub"):
            self._views.register("settings_hub", self._settings_hub_page)
        self._fade_content("settings_hub")

    def _show_devices_page(self, key=None):
        if self._devices_page is None:
            from ui.devices_page import DevicesPage
            sync_mgr = self._ensure_sync_manager()
            self._devices_page = DevicesPage(db=self._db, sync_manager=sync_mgr)
        if not self._views.widget("devices_page"):
            self._views.register("devices_page", self._devices_page)
        self._fade_content("devices_page")

    def _show_new_playlist(self, key):
        self._create_playlist()

    # ── Michi API Bridge handlers ──

    @staticmethod
    def _state_to_str(state) -> str:
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
    def _delete_playlist(self, pid):
        self._sidebar_menu_ctrl.delete_playlist(pid)
    def _change_playlist_cover(self, pid):
        self._sidebar_menu_ctrl._change_playlist_cover(pid)
    def _remove_playlist_cover(self, pid):
        self._sidebar_menu_ctrl._remove_playlist_cover(pid)
    def _save_playlist_edit(self, pid, name, desc, dlg):
        self._sidebar_menu_ctrl._save_playlist_edit(pid, name, desc, dlg)
    def _add_server(self):
        self._srv_ctrl.add_server()
    def _open_server(self, name: str):
        self._srv_ctrl.open_server(name)
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

    def _add_transmit_device(self):
        self._transmit_ctrl.add_device()

    def _open_file(self):
        self._file_actions.open_files(ALL_EXTS)

    def _import_m3u(self):
        self._playlist_ctrl.import_m3u()

    def _create_playlist(self):
        self._sidebar_menu_ctrl.create_playlist()

    def _on_radio_count(self, visible, total):
        self._srv_ctrl.on_radio_count(visible, total)

    def _play_radio(self, url, name):
        self._srv_ctrl.play_radio(url, name)

    def _on_sidebar_navigate(self, key):
        self._nav_ctrl.dispatch(key)
    def _show_album_grid(self):
        items = self._filtered_album_items()
        self._album_grid.set_items(items, 200,
                                   sort_key=getattr(self, '_album_sort_key', 'title'),
                                   filter_mode=getattr(self, '_album_filter_mode', 'all'))
        from library.album_art import group_by_album
        groups = group_by_album(items)
        self._count.setText(f"{len(groups)} álbumes")

    def _show_song_grid(self):
        items = self._all_items
        if self._search_text:
            q = self._search_text.lower()
            items = [
                i for i in items
                if q in (i.title or "").lower()
                or q in (i.artist or "").lower()
                or q in (i.album or "").lower()
                or q in (i.filepath or "").lower()
            ]
        self._song_grid.set_items(items, card_size=170)
        self._count.setText(f"{len(items)} canciones")

    def _show_album_list(self):
        self._view_router._show_album_list()
    def _show_coverflow(self):
        self._cf_ctrl.show()
    def _on_metadata_saved(self, filepaths: list):
        self._playlist_ctrl.metadata_saved(filepaths)
        self._reload_library_after_change(reason="metadata_saved")

    def _reload_library_after_change(self, reason: str = ""):
        self._lib_ctrl.reload_after_change(reason)

    def _refresh_all_tabs(self, force: bool = False):
        self._lib_ctrl.refresh_all_tabs(force)

    def _refresh_songs_data(self):
        self._lib_ctrl.refresh_songs()

    def _refresh_albums_data(self):
        self._lib_ctrl.refresh_albums()

    def _refresh_artists_data(self):
        self._lib_ctrl.refresh_artists()

    def _refresh_genres_data(self):
        self._lib_ctrl.refresh_genres()

    def _filtered_album_items(self) -> list:
        return self._lib_ctrl.filtered_album_items()

    def _album_items(self) -> list:
        return self._lib_ctrl._album_items()

    def _refresh_active_library_tab(self, force: bool = False):
        self._lib_ctrl.refresh_active_tab(force)
    def _add_folder(self):
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self, "Añadir carpeta", os.path.expanduser("~"))
        if path:
            self._scan_path(path)


    # Extracted to ui/controllers/artist_controller.py — grid + detail logic

    def _show_artists_view(self, mode: str):
        self._artist_ctrl.show_artists_view(mode)
    def _refresh_artist_info(self, artist_key: str):
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group or not hasattr(self, '_artist_enrich'):
            return

        if hasattr(repo, 'mark_enrichment_loading'):
            repo.mark_enrichment_loading(artist_key)

        self._artist_enrich.refresh_artist(artist_key)
        self._artist_enrich.enrich_artist(group, force=True)

        if hasattr(self._artist_grid, 'set_artists'):
            self._artist_grid.set_artists(repo.groups)

        self._toast_svc.show(
            f"Actualizando info de {group.display_name}...", "info")

    def _on_artist_enriched(self, artist_key: str, info):
        repo = self._ctx.artist_repo
        if hasattr(repo, 'apply_external_info'):
            repo.apply_external_info(artist_key, info)

        # Refresh detail if open for this artist
        if (hasattr(self, '_artist_detail') and hasattr(self._artist_detail, '_artist')
                and self._artist_detail._artist
                and self._artist_detail._artist.key == artist_key):
            group = repo.get_group(artist_key)
            if group:
                self._artist_detail.set_artist(group)
            else:
                self._artist_detail.set_external_info(info)

        # Refresh grid
        if hasattr(self._artist_grid, 'set_artists'):
            self._artist_grid.set_artists(repo.groups)

    def _on_artist_image_loaded(self, artist_key: str, local_path: str):
        repo = self._ctx.artist_repo
        # Refresh grid to show new thumb
        if hasattr(self._artist_grid, 'set_artists'):
            self._artist_grid.set_artists(repo.groups)
        # Refresh detail if open for this artist
        if (hasattr(self, '_artist_detail') and hasattr(self._artist_detail, '_artist')
                and self._artist_detail._artist
                and self._artist_detail._artist.key == artist_key):
            group = repo.get_group(artist_key)
            if group:
                self._artist_detail.set_artist(group)

    def _on_artist_enrichment_failed(self, artist_key: str, error: str):
        repo = self._ctx.artist_repo
        if hasattr(repo, 'mark_enrichment_error'):
            repo.mark_enrichment_error(artist_key, error)
        # Refresh grid to show error badge
        if hasattr(self._artist_grid, 'set_artists'):
            self._artist_grid.set_artists(repo.groups)
        self._toast_svc.show(
            f"Enriquecimiento: {error}", "error")

    def _open_metadata_for_files(self, filepaths: list[str]):
        self._artist_ctrl.open_metadata_for_files(filepaths)

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

    # ── FileWatcher handlers ──

    def _on_watcher_files_added(self, paths: list[str]):
        self._file_actions._add_file_list(paths)
        self._reload_library_after_change(reason="watcher_added")
        self._toast_svc.show(f"{len(paths)} archivos nuevos detectados", "info")

    def _on_watcher_files_removed(self, paths: list[str]):
        now = __import__("time").time()
        for fp in paths:
            self._db._conn.execute(
                "UPDATE media_items SET deleted_at=? WHERE filepath=?",
                (now, fp))
        self._db._conn.commit()
        self._reload_library_after_change(reason="watcher_removed")

    def _on_watcher_files_modified(self, paths: list[str]):
        self._file_actions._add_file_list(paths)
        self._reload_library_after_change(reason="watcher_modified")

    def _scan_path(self, path: str):
        self._file_actions.scan_path(path)

    def _show_duplicates(self):
        from ui.dialogs.duplicate_dialog import DuplicateDialog
        dlg = DuplicateDialog(self._db, self)
        dlg.exec()

    # Extracted to core/playback_controller.py — play/pause/queue logic
    def _play_filepaths(self, filepaths: list[str], play_now: bool = True):
        """Centralized playback entry point — ensures all tracks go through _play_trackref."""
        if not filepaths:
            return
        if play_now:
            track = TrackRef(uri=filepaths[0], title=os.path.basename(filepaths[0]))
            self._play_trackref(track)
            for fp in filepaths[1:]:
                self._playback.enqueue([fp], play_now=False)
        else:
            self._playback.enqueue(filepaths, play_now=False)

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
    def _open_eq(self):
        self._playback_ctrl.open_eq()

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

    def _activate_transmit_device(self, device):
        self._transmit_ctrl.activate_device(device)

    def _on_transmit_active_changed(self):
        self._transmit_ctrl.on_active_changed()

    def _show_audio_output_menu(self):
        self._audio_output_ctrl.show_menu()

    def _show_audio_diagnostics(self):
        from ui.builder.inline_dialogs import show_audio_diagnostics
        show_audio_diagnostics(self, self._playback)

    def _open_mini_player(self):
        self._mini_player_ctrl.open()
    def _manage_transmit_devices(self):
        self._transmit_ctrl.manage_devices()

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
