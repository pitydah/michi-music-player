"""MainWindow — 2 panels + nowplaying bar with library, EQ, and streaming."""

import os
import random
import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor, QDragEnterEvent, QDropEvent, QPainter, QLinearGradient, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel,
    QFrame, QHBoxLayout, QLineEdit, QToolButton, QStackedWidget, QTableView, QHeaderView,
    QAbstractItemView, QFileDialog, QInputDialog, QMessageBox, QMenu,
    QDialog, QFormLayout, QPushButton, QDialogButtonBox,
)

from ui.sidebar_widget import SidebarWidget
from ui.view_switcher import SegmentedViewSwitcher
from ui.view_controller import ViewController
from ui.sidebar_controller import SidebarController

from ui.central.central_styles import (
    search_qss as _cs_search_qss,
    count_badge_qss, tool_button_qss, menu_qss as _cs_menu_qss,
    table_qss, scrollbar_qss, section_icon_box_qss,
    section_title_qss, section_subtitle_qss, header_qss,
    table_header_qss, dialog_qss,
)

from ui.icons import get_icon, get_pixmap, get_qicon, app_icon
from ui.nowplaying_bar import NowPlayingBar
from audio.player import PlayerEngine, PlaybackState
from library.library_db import (
    LibraryDB, DB_PATH, MediaItem,
    AUDIO_EXTS, ALL_EXTS, scan_device_music,
)
from ui.folder_browser import FolderBrowserWidget
from ui.search_controller import SearchController
from sources.local_source import LocalSource
from sources.radio_source import RadioSource
from sources.base_source import TrackRef
from library.trackref_model import TrackRefTableModel

from streaming.transmit_manager import TransmitManager

from streaming.subsonic_client import (
    SubsonicClient, load_servers, save_servers,
    SubsonicError, AuthError, ServerNotFoundError,
)
from streaming.server_dialog import ServerDialog
from streaming.remote_browser import RemoteBrowser
from library.coverflow import CoverFlowWidget
from library.album_grid import AlbumGridWidget
from library.song_grid import SongGridWidget
from library.album_art import load_covers_for_albums
from streaming.radio_widget import RadioWidget
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
from ui.home_audio_view import HomeAudioView
from recognition.detection_service import DetectionService


SECTION_CONFIG = {
    "library":    {"title": "Todas las canciones", "subtitle": "Toda tu música local",
                   "icon": "sidebar_library", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "albums":     {"title": "Álbumes", "subtitle": "Carátulas y navegación visual",
                   "icon": "sidebar_albums", "views": ["list", "grid", "coverflow"],
                   "search": True, "default": "grid"},
    "artists":    {"title": "Artistas", "subtitle": "Explora tu biblioteca por artista y álbumes",
                   "icon": "sidebar_artist", "views": ["grid", "list"],
                   "search": True, "default": "grid"},
    "genres":     {"title": "Géneros", "subtitle": "Atlas de estilos de tu biblioteca",
                    "icon": "sidebar_popular", "views": ["grid", "list"],
                    "search": True, "default": "grid"},
    "folders":    {"title": "Carpetas", "subtitle": "Explorador musical local",
                   "icon": "sidebar_folders", "views": ["tree"],
                   "search": True, "default": "tree"},
    "radio":      {"title": "Emisoras", "subtitle": "Radios por URL y mosaicos",
                   "icon": "sidebar_radio", "views": ["grid", "list"],
                   "search": True, "default": "grid"},
    "identifier": {"title": "Identificador", "subtitle": "Detección musical",
                   "icon": "sidebar_identifier", "views": [],
                   "search": False, "default": None},
    "playlists":  {"title": "Playlist", "subtitle": "Colecciones personalizadas",
                   "icon": "sidebar_playlists", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "favs":       {"title": "Favoritos", "subtitle": "Canciones marcadas como favoritas",
                   "icon": "sidebar_popular", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "recent":     {"title": "Recientes", "subtitle": "Reproducidas recientemente",
                   "icon": "sidebar_recent", "views": ["list", "grid"],
                   "search": True, "default": "list"},
    "discover":   {"title": "Descubrir", "subtitle": "Explora y redescubre tu música",
                   "icon": "sidebar_mix", "views": [],
                   "search": False, "default": None},
    "mix_daily":  {"title": "Mix diario", "subtitle": "Selección automática para hoy",
                   "icon": "sidebar_mix", "views": [],
                   "search": False, "default": None},
    "mix_unplayed": {"title": "No escuchadas", "subtitle": "Canciones por descubrir",
                     "icon": "sidebar_unplayed", "views": ["list", "grid"],
                     "search": True, "default": "list"},
    "mix_popular": {"title": "Más escuchadas", "subtitle": "Mayor número de reproducciones",
                    "icon": "sidebar_popular", "views": [],
                    "search": False, "default": None},
    "add_server": {"title": "Añadir servidor", "subtitle": "Conecta Navidrome o Jellyfin",
                   "icon": "sidebar_add", "views": [],
                   "search": False, "default": None},
    "playlist_hub": {"title": "Playlist", "subtitle": "Organiza, mezcla e importa tus listas",
                     "icon": "sidebar_playlists", "views": ["grid"],
                     "search": False, "default": "grid"},
    "metadata_editor": {"title": "Editor de metadatos",
                         "subtitle": "Limpia, completa y normaliza la información de tus archivos",
                         "icon": "metadata_editor", "views": [],
                         "search": False, "default": None},
    "home_audio": {"title": "Home Audio",
                    "subtitle": "Audio multiroom, parlantes y Home Assistant",
                    "icon": "home_audio", "views": [],
                    "search": False, "default": None},
    "new_playlist": {"title": "Nueva playlist", "subtitle": "Crear una playlist vacía",
                     "icon": "sidebar_add", "views": [],
                     "search": False, "default": None},
    "assistant":  {"title": "Asistente",
                    "subtitle": "IA local para explorar tu biblioteca",
                    "icon": "sidebar_mix", "views": [],
                    "search": False, "default": None},
    "metadata_review": {"title": "Revisión de metadata",
                         "subtitle": "Compara y aprueba cambios sugeridos",
                         "icon": "metadata_editor", "views": [],
                         "search": False, "default": None},
    "audio_lab":      {"title": "Audio Lab",
                        "subtitle": "Importa, corrige y enriquece tu colección",
                        "icon": "sidebar_mix", "views": [],
                        "search": False, "default": None},
    "michi_disc_lab": {"title": "Michi Disc Lab",
                       "subtitle": "Importación Hi-Fi y ripeo seguro de CDs",
                       "icon": "sidebar_mix", "views": [],
                       "search": False, "default": None},
    "home":           {"title": "Inicio",
                        "subtitle": "Tu música en un solo lugar",
                        "icon": "sidebar_library", "views": [],
                        "search": False, "default": None},
    "library_hub":    {"title": "Biblioteca",
                        "subtitle": "Música local, servidores y archivos offline",
                        "icon": "sidebar_library", "views": [],
                        "search": False, "default": None},
    "mix_hub":        {"title": "Mix",
                        "subtitle": "Smart mixes, recomendaciones y playlists mixtas",
                        "icon": "sidebar_mix", "views": [],
                        "search": False, "default": None},
    "playback_hub":   {"title": "Reproducción",
                        "subtitle": "Cola, historial, favoritos y radio",
                        "icon": "warm_play", "views": [],
                        "search": False, "default": None},
    "connections_hub":{"title": "Conexiones",
                        "subtitle": "Servidores, Home Audio y dispositivos",
                        "icon": "sidebar_servers", "views": [],
                        "search": False, "default": None},
    "settings_hub":   {"title": "Configuración",
                        "subtitle": "Preferencias de la aplicación",
                        "icon": "warm_settings", "views": [],
                        "search": False, "default": None},
    "devices":        {"title": "Dispositivos",
                        "subtitle": "Unidades y discos externos",
                        "icon": "sidebar_devices", "views": [],
                        "search": False, "default": None},
    "devices_page":   {"title": "Michi Sync Suite",
                        "subtitle": "Sincroniza musica con tus dispositivos",
                        "icon": "sidebar_devices", "views": [],
                        "search": False, "default": None},
}


def _resolve_section_config(key: str, extra: dict = None) -> dict:
    """Resolve section config for static or dynamic keys (pl:, srv:, dev:)."""
    if key in SECTION_CONFIG:
        return SECTION_CONFIG[key]

    if key.startswith("pl:") and extra:
        name = extra.get("name", "Playlist")
        return {"title": name, "subtitle": "Playlist local",
                "icon": "sidebar_playlist_item", "views": ["list", "grid"],
                "search": True, "default": "list"}
    if key.startswith("srv:") and extra:
        name = extra.get("name", "Servidor")
        sv_type = extra.get("type", "")
        icon = "sidebar_navidrome" if sv_type == "navidrome" else "sidebar_jellyfin"
        return {"title": name, "subtitle": "Servidor remoto",
                "icon": icon, "views": [],
                "search": True, "default": None}
    if key.startswith("dev:") and extra:
        name = extra.get("name", os.path.basename(extra.get("mount", "")))
        return {"title": name, "subtitle": "Dispositivo externo",
                "icon": "sidebar_devices", "views": ["list"],
                "search": True, "default": "list"}

    return {"title": key.capitalize(), "subtitle": "",
            "icon": "sidebar_library", "views": ["list", "grid"],
            "search": True, "default": "list"}

# Navigation routes — maps sidebar keys to handler methods
NAV_ROUTES = {
    "library": "_show_library", "albums": "_show_albums",
    "artists": "_show_artists", "genres": "_show_genres",
    "radio": "_show_radio", "home_audio": "_show_home_audio",
    "identifier": "_show_identifier", "discover": "_show_discover",
    "folders": "_show_folders", "playlist_hub": "_show_playlist_hub",
    "metadata_editor": "_show_metadata_editor",
    "favs": "_show_favs", "recent": "_show_recent",
    "new_playlist": "_show_new_playlist", "add_server": "_show_add_server",
    "assistant": "_show_assistant",
    "metadata_review": "_show_metadata_review",
    "audio_lab": "_show_audio_lab",
    "michi_disc_lab": "_show_michi_disc_lab",
    "home": "_show_home_page",
    "library_hub": "_show_library_hub_page",
    "mix_hub": "_show_mix_hub_page",
    "playback_hub": "_show_playback_hub_page",
    "connections_hub": "_show_connections_hub_page",
    "settings_hub": "_show_settings_hub_page",
    "devices_page": "_show_devices_page",
}


class MainWindow(QMainWindow):
    def __init__(self):
        from time import perf_counter
        _t0 = perf_counter()
        _log = logging.getLogger("michi.startup")

        super().__init__()
        self._safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"
        self._view_cache: dict[str, QWidget] = {}
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
        self._nav_history: list[str] = []
        self._nav_history_index: int = -1
        self._nav_restoring: bool = False

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
        self._home_page = None
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
        self._shutdown.register("playback", lambda: self._playback.stop())
        self._shutdown.register("db", lambda: self._db.close())

    def _init_ui(self):
        """Sidebar, header, content stack, nowplaying, views."""
        self._setup_actions()
        self._setup_ui()

    def _init_controllers(self):
        """Required controllers — navigation, playback, playlist, library."""
        # Repos first
        from ui.controllers.artist_repository import ArtistRepository
        self._artist_repo = ArtistRepository()

        # AppContext + AppServices before controllers that use them
        from core.app_context import AppContext
        self._ctx = AppContext(self)
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

    def _load_initial_data(self):
        """Library loading, cleanup, enrichment, tray — after everything is wired."""
        if self._safe_mode:
            self._toast_svc.show(
                "Modo seguro activado — servicios opcionales deshabilitados", "info")
        removed = self._db.cleanup_missing()
        self._load_library()
        if removed:
            self._toast_svc.show(
                f"{removed} archivos eliminados de la biblioteca (ya no existen)",
                "info")

        if (hasattr(self, '_artist_enrich') and self._artist_enrich
                and hasattr(self._artist_repo, 'groups')):
            from core.settings_manager import get_bool
            if get_bool("artist_enrichment/enabled"):
                self._artist_enrich.enrich_visible_artists(
                    self._artist_repo.groups, limit=20)

        self._setup_tray()

    # ── Safe init helper ──

    def _safe_init(self, name: str, factory):
        """Initialize an optional feature. Returns service or None on failure."""
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
        """Lazy-load a view widget. Created once, cached forever."""
        if key not in self._view_cache:
            self._view_cache[key] = factory()
        return self._view_cache[key]

    # ── Optional service factories ──

    def _make_snapserver(self):
        from integrations.snapcast.snapserver_manager import SnapServerManager
        svc = SnapServerManager(self)
        svc.started.connect(self._on_snapserver_started)
        svc.stopped.connect(self._on_snapserver_stopped)
        svc.error_occurred.connect(self._on_snapserver_error)
        self._shutdown.register("snapserver", lambda: svc.stop())
        return svc

    def _make_audio_capture(self):
        from integrations.snapcast.audio_capture import AudioCaptureManager
        svc = AudioCaptureManager(self)
        svc.sink_ready.connect(self._on_audio_sink_ready)
        svc.error_occurred.connect(self._on_snapserver_error)
        self._shutdown.register("audio_capture", lambda: svc.remove_sink()
                                if hasattr(svc, 'remove_sink') else None)
        return svc

    def _make_snap_discovery(self):
        from integrations.snapcast.discovery import SnapClientDiscovery
        svc = SnapClientDiscovery(self)
        svc.clients_found.connect(self._on_snap_clients_found)
        return svc

    def _make_group_manager(self):
        from integrations.snapcast.group_manager import GroupManager
        svc = GroupManager(self)
        svc.groups_changed.connect(self._on_groups_changed)
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
        v = self._home_audio_view
        v.connect_requested.connect(self._on_home_audio_connect)
        v.refresh_requested.connect(self._on_home_audio_refresh)
        v.enable_multiroom_requested.connect(self._on_home_audio_multiroom)
        v.open_settings_requested.connect(self._on_home_audio_settings)
        v.open_receiver_wizard_requested.connect(self._on_home_audio_receiver_wizard)
        v.device_cast_current_requested.connect(self._on_home_audio_cast)
        v.device_play_requested.connect(self._on_home_audio_device_play)
        v.device_pause_requested.connect(self._on_home_audio_device_pause)
        v.device_stop_requested.connect(self._on_home_audio_device_stop)
        v.device_volume_changed.connect(self._on_home_audio_device_volume)
        v.group_selected_requested.connect(self._on_home_audio_group_selected)
        v.create_group_requested.connect(self._on_home_audio_create_group)

    def _wire_identifier_signals(self):
        v = self._identifier_view
        v.toggle_requested.connect(self._toggle_identifier)
        v.clear_requested.connect(self._clear_detected_tracks)
        v.track_selected.connect(self._on_detected_track_selected)
        v.identify_once_requested.connect(
            lambda: self._identifier_ctrl.identify_once()
            if self._identifier_ctrl else None)
        v.settings_requested.connect(self._on_identifier_settings)
        v.play_track_requested.connect(self._on_identifier_play)
        v.search_track_requested.connect(self._on_identifier_search)
        v.delete_track_requested.connect(self._on_identifier_delete)
        if self._detection:
            self._detection.track_detected.connect(self._on_track_detected)
            self._detection.detection_failed.connect(self._on_detection_failed)
        if self._identifier_ctrl:
            self._identifier_ctrl.state_changed.connect(
                self._identifier_view.set_identifier_state)
            self._identifier_ctrl.source_changed.connect(
                self._identifier_view.set_source_status)
            self._identifier_ctrl.provider_changed.connect(
                self._identifier_view.set_provider_status)

    def _setup_actions(self):
        from PySide6.QtGui import QAction

        self._open_file_action = QAction("Abrir archivo...", self)
        self._open_file_action.setShortcut("Ctrl+O")
        self._open_file_action.triggered.connect(self._open_file)
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
        back_action.triggered.connect(self._navigate_back)
        self.addAction(back_action)

        forward_action = QAction(self)
        forward_action.setShortcut("Alt+Right")
        forward_action.triggered.connect(self._navigate_forward)
        self.addAction(forward_action)

        self._add_transmit_device_action = QAction("Añadir dispositivo...", self)
        self._add_transmit_device_action.triggered.connect(self._add_transmit_device)
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

        self._quit_action = QAction("Salir", self)
        self._quit_action.setShortcut("Ctrl+Q")
        self._quit_action.triggered.connect(self.close)
        self.addAction(self._quit_action)

        self.menuBar().hide()

    def _toggle_sync(self):
        if not hasattr(self, '_sync_mgr'):
            from sync.sync_manager import SyncManager
            self._sync_mgr = SyncManager(self._db, self)
            self._sync_mgr.sync_started.connect(
                lambda p: self._sync_action.setText(
                    f"✓ Sincronización activa (puerto {p})"))
            self._sync_mgr.sync_stopped.connect(
                lambda: self._sync_action.setText(
                    "Activar sincronización Android"))
            self._sync_mgr.error_occurred.connect(
                lambda m: self._toast_svc.show(f"Sync error: {m}", "error"))
            self._sync_mgr.client_connected.connect(
                lambda d: self._toast_svc.show(f"Dispositivo conectado: {d}", "info"))

        if self._sync_mgr.is_active:
            self._sync_mgr.stop()
            self._sync_action.setChecked(False)
        else:
            self._sync_mgr.start()
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

    def _build_breadcrumb_subtitle(self, subtitle: str, section_key: str) -> str:
        if not self._nav_history or self._nav_history_index <= 0:
            return subtitle
        prev_key = self._nav_history[self._nav_history_index - 1]
        hub_names = {
            "home": "Inicio", "library_hub": "Biblioteca", "mix_hub": "Mix",
            "playback_hub": "Reproducción", "connections_hub": "Conexiones",
            "radio": "Radio", "audio_lab": "Audio Lab",
            "settings_hub": "Configuración", "home_audio": "Home Audio",
            "library": "Biblioteca", "albums": "Biblioteca",
            "artists": "Biblioteca", "genres": "Biblioteca",
            "folders": "Biblioteca",
        }
        hub = hub_names.get(prev_key, "")
        if hub and section_key not in ("home", "library_hub", "mix_hub",
                                         "playback_hub", "connections_hub",
                                         "settings_hub", "audio_lab"):
            return f"{hub} / {subtitle}" if subtitle else hub
        return subtitle

    def _show_about(self):
        QMessageBox.about(self, "Acerca de",
            "<h2>Michi Music Player</h2><p>Sincronización Android, ecualizador paramétrico, "
            "CoverFlow 3D, streaming Navidrome/Jellyfin.</p>"
            "<p>Python 3 · PySide6 · GStreamer</p>")

    def _setup_ui(self):
        # ── Sidebar ──
        self._sidebar = SidebarWidget()
        self._sidebar.setMinimumWidth(270)
        self._sidebar.setMaximumWidth(380)
        self._sidebar_controller = SidebarController(self._sidebar, self._db)
        self._sidebar_controller.navigation_requested.connect(
            self._on_sidebar_navigate)
        self._sidebar.setContextMenuPolicy(Qt.CustomContextMenu)
        self._sidebar.customContextMenuRequested.connect(self._on_sidebar_menu)

        # ── Header ──
        header = QFrame()
        header.setObjectName("headerBar")
        header.setStyleSheet(header_qss())
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(12)

        # Section icon capsule
        self._section_icon_box = QFrame()
        self._section_icon_box.setObjectName("sectionIconBox")
        self._section_icon_box.setFixedSize(42, 42)
        self._section_icon_box.setStyleSheet(section_icon_box_qss())
        icon_box_inner = QVBoxLayout(self._section_icon_box)
        icon_box_inner.setContentsMargins(0, 0, 0, 0)
        icon_box_inner.setAlignment(Qt.AlignCenter)

        self._section_icon = QLabel()
        self._section_icon.setFixedSize(26, 26)
        self._section_icon.setAlignment(Qt.AlignCenter)
        self._section_icon.setStyleSheet("background: transparent; border: none;")
        icon_box_inner.addWidget(self._section_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self._section_title = QLabel("Todas las canciones")
        self._section_title.setObjectName("sectionTitle")
        self._section_title.setStyleSheet(section_title_qss())
        self._section_subtitle = QLabel("Toda tu música local")
        self._section_subtitle.setObjectName("sectionSubtitle")
        self._section_subtitle.setStyleSheet(section_subtitle_qss())
        title_box.addWidget(self._section_title)
        title_box.addWidget(self._section_subtitle)

        title_wrap = QHBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(6)

        self._back_btn = QToolButton()
        self._back_btn.setText("←")
        self._back_btn.setToolTip("Atrás (Alt+Izquierda)")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setStyleSheet(tool_button_qss("icon"))
        self._back_btn.setFixedSize(36, 36)
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._navigate_back)
        title_wrap.addWidget(self._back_btn)

        self._forward_btn = QToolButton()
        self._forward_btn.setText("→")
        self._forward_btn.setToolTip("Adelante (Alt+Derecha)")
        self._forward_btn.setCursor(Qt.PointingHandCursor)
        self._forward_btn.setStyleSheet(tool_button_qss("icon"))
        self._forward_btn.setFixedSize(36, 36)
        self._forward_btn.setEnabled(False)
        self._forward_btn.clicked.connect(self._navigate_forward)
        title_wrap.addWidget(self._forward_btn)

        title_wrap.addWidget(self._section_icon_box)
        title_wrap.addLayout(title_box)
        hl.addLayout(title_wrap)
        hl.addSpacing(16)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar canciones...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._on_search)
        self._search.setStyleSheet(_cs_search_qss())
        self._count = QLabel("0 elementos")
        self._count.setObjectName("countBadge")
        self._count.setStyleSheet(count_badge_qss())

        # View selector (segmented capsule)
        self._view_switcher = SegmentedViewSwitcher(get_icon)
        self._view_switcher.view_changed.connect(self._on_view_mode_changed)
        self._view_mode = "list"

        self._settings_btn = QToolButton()
        self._settings_btn.setObjectName("settingsButton")
        self._settings_btn.setIcon(get_qicon("warm_settings", size=24))
        self._settings_btn.setIconSize(QSize(24, 24))
        self._settings_btn.setFixedSize(44, 44)
        self._settings_btn.setToolTip("Configuración y acciones")
        self._settings_btn.setPopupMode(QToolButton.InstantPopup)
        self._settings_btn.setStyleSheet(tool_button_qss("icon"))

        settings_menu = QMenu(self)
        settings_menu.setStyleSheet(_cs_menu_qss())
        settings_menu.addAction(self._open_file_action)
        settings_menu.addAction(self._add_folder_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self._import_playlist_action)
        settings_menu.addAction(self._export_playlist_action)
        settings_menu.addSeparator()
        transmit_sub = settings_menu.addMenu("Transmitir")
        transmit_sub.addAction(self._add_transmit_device_action)
        transmit_sub.addAction(self._manage_transmit_devices_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self._sync_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self._preferences_action)
        settings_menu.addAction(self._shortcuts_action)
        settings_menu.addAction(self._about_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self._quit_action)
        self._settings_btn.setMenu(settings_menu)

        # Album sort/filter row (shown only for albums section)
        self._album_sort_btn = QToolButton()
        self._album_sort_btn.setText("Ordenar")
        self._album_sort_btn.setToolTip("Ordenar álbumes")
        self._album_sort_btn.setPopupMode(QToolButton.InstantPopup)
        self._album_sort_btn.setFixedHeight(32)
        self._album_sort_btn.setStyleSheet(tool_button_qss())
        self._setup_album_sort_menu()
        self._album_sort_btn.hide()

        self._album_filter_btn = QToolButton()
        self._album_filter_btn.setText("Filtrar")
        self._album_filter_btn.setToolTip("Filtrar álbumes")
        self._album_filter_btn.setPopupMode(QToolButton.InstantPopup)
        self._album_filter_btn.setFixedHeight(32)
        self._album_filter_btn.setStyleSheet(tool_button_qss())
        self._setup_album_filter_menu()
        self._album_filter_btn.hide()

        # Context actions container
        self._context_actions_box = QHBoxLayout()
        self._context_actions_box.setSpacing(6)
        self._context_actions_box.addWidget(self._album_sort_btn)
        self._context_actions_box.addWidget(self._album_filter_btn)

        hl.addStretch()
        hl.addWidget(self._view_switcher)
        hl.addLayout(self._context_actions_box)
        hl.addWidget(self._search)
        hl.addWidget(self._count)
        hl.addWidget(self._settings_btn)

        # ── Table ──
        self._table = QTableView()
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.horizontalHeader().setSectionsClickable(True)
        self._table.horizontalHeader().setSortIndicatorShown(True)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(30)
        self._table.setColumnHidden(7, True)  # hide URI column
        self._table.setSortingEnabled(True)
        self._table.setStyleSheet(table_qss() + scrollbar_qss())
        self._table.horizontalHeader().setStyleSheet(table_header_qss())
        self._table.doubleClicked.connect(self._on_table_dbl)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_menu)

        placeholder = QLabel()
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.82); font-size: 16px; font-weight: 500;"
            "  background: transparent; border: none; padding: 48px 48px 12px 48px; }")
        placeholder.setText(
            "🎵  Añade música a tu biblioteca\n\n"
            "Abre una carpeta o arrastra archivos para comenzar")

        placeholder_albums = QLabel()
        placeholder_albums.setAlignment(Qt.AlignCenter)
        placeholder_albums.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.82); font-size: 15px;"
            "  background: transparent; border: none; padding: 48px; }")
        placeholder_albums.setText(
            "📀  Sin álbumes en la biblioteca\n\n"
            "Añade carpetas de música para ver carátulas aquí")

        placeholder_expanded = QLabel("")
        placeholder_expanded.setAlignment(Qt.AlignCenter)

        # ── Expanded view (created on demand) ──
        self._expanded = None
        self._coverflow = None
        self._remote_browser = None
        self._remote_placeholder = QLabel("Conecta a un servidor remoto primero")
        self._remote_placeholder.setAlignment(Qt.AlignCenter)
        self._remote_placeholder.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.62); font-size: 15px; font-weight: 500;"
            "  background: transparent; border: none; }")
        self._radio_widget = RadioWidget(self._radio_manager)
        self._radio_widget.station_selected.connect(self._play_radio)
        self._radio_widget.count_changed.connect(self._on_radio_count)

        self._album_grid = AlbumGridWidget()
        self._album_grid.set_worker_manager(self._workers)
        self._album_grid.album_double_clicked.connect(
            lambda fps: self._play_filepaths(fps, play_now=True))
        self._album_grid.queue_requested.connect(
            lambda fps: self._play_filepaths(fps, play_now=False))
        self._album_grid.playlist_requested.connect(
            self._on_album_create_playlist)
        self._album_grid.cover_search_requested.connect(
            self._on_album_search_cover)
        self._album_grid.open_folder_requested.connect(
            self._on_album_open_folder)
        self._album_grid.details_requested.connect(
            self._on_album_show_details)

        self._song_grid = SongGridWidget()
        self._song_grid.song_double_clicked.connect(
            lambda fp: self._play_file(fp))

        self._discover = DiscoverDashboard()
        self._discover.navigate_requested.connect(
            self._on_sidebar_navigate)

        self._playlist_hub = PlaylistHubWidget()
        self._playlist_hub.create_playlist_requested.connect(self._create_playlist)
        self._playlist_hub.import_m3u_requested.connect(self._import_m3u)
        self._playlist_hub.export_playlists_requested.connect(self._export_playlists)
        self._playlist_hub.smart_playlist_requested.connect(self._open_smart_playlist)
        self._playlist_hub.playlist_open_requested.connect(
            lambda pid: self._on_sidebar_navigate(f"pl:{pid}"))
        self._playlist_hub.playlist_play_requested.connect(
            self._on_hub_playlist_play)
        self._playlist_hub.playlist_queue_requested.connect(
            self._on_hub_playlist_queue)
        self._playlist_hub.create_from_folder_requested.connect(
            self._on_hub_create_from_folder)
        self._playlist_hub.create_from_queue_requested.connect(
            self._on_hub_create_from_queue)
        self._playlist_hub.export_text_requested.connect(
            lambda: self._toast_svc.show("Funcionalidad en desarrollo — disponible próximamente", "info"))
        self._playlist_hub.find_duplicates_requested.connect(
            lambda: self._toast_svc.show("Detección de duplicados pendiente de implementación", "info"))
        self._playlist_hub.scan_metadata_requested.connect(
            lambda: self._toast_svc.show("Revisión de metadatos pendiente de implementación", "info"))
        self._playlist_hub.scan_missing_covers_requested.connect(
            lambda: self._toast_svc.show("Búsqueda de carátulas faltantes pendiente de implementación", "info"))
        self._playlist_hub.clean_empty_playlists_requested.connect(
            lambda: self._toast_svc.show("Limpieza de playlists vacías pendiente de implementación", "info"))
        self._playlist_hub.find_lost_files_requested.connect(
            lambda: self._toast_svc.show("Búsqueda de canciones perdidas pendiente de implementación", "info"))

        self._playlist_detail = PlaylistDetailView()
        self._playlist_detail.play_requested.connect(self._on_hub_playlist_play)
        self._playlist_detail.queue_requested.connect(self._on_hub_playlist_queue)
        self._playlist_detail.edit_requested.connect(self._edit_playlist_dialog)
        self._playlist_detail.track_double_clicked.connect(
            lambda fp: self._play_filepaths([fp], play_now=True))

        self._playlist_hub.playlist_edit_requested.connect(self._edit_playlist_dialog)
        self._playlist_hub.create_from_album_requested.connect(
            self._playlist_ctrl.create_from_album)
        self._playlist_hub.create_from_artist_requested.connect(
            self._playlist_ctrl.create_from_artist)
        self._playlist_hub.create_from_genre_requested.connect(
            self._playlist_ctrl.create_from_genre)
        self._playlist_hub.create_from_search_requested.connect(
            self._playlist_ctrl.create_from_search)

        self._metadata_editor = MetadataEditorWidget()
        self._metadata_editor.files_saved.connect(self._on_metadata_saved)
        self._metadata_editor.request_library_refresh.connect(self._refresh_library)

        self._artist_grid = ArtistGridWidget()
        self._artist_detail = ArtistDetailView()
        self._artist_grid.artist_selected.connect(self._open_artist_detail)
        self._artist_grid.artist_play_requested.connect(self._play_artist)
        self._artist_grid.artist_queue_requested.connect(self._queue_artist)
        self._artist_grid.artist_playlist_requested.connect(self._create_playlist_from_artist)
        self._artist_grid.artist_metadata_requested.connect(self._edit_artist_metadata)
        self._artist_grid.artist_enrich_requested.connect(self._refresh_artist_info)
        self._artist_detail.back_requested.connect(self._show_artists_overview)
        self._artist_detail.play_all_requested.connect(self._play_artist)
        self._artist_detail.shuffle_all_requested.connect(self._shuffle_artist)
        self._artist_detail.queue_all_requested.connect(self._queue_artist)
        self._artist_detail.play_album_requested.connect(
            lambda fps: self._play_filepaths(fps, play_now=True))
        self._artist_detail.queue_album_requested.connect(
            lambda fps: self._play_filepaths(fps, play_now=False))
        self._artist_detail.playlist_artist_requested.connect(self._create_playlist_from_artist)
        self._artist_detail.metadata_artist_requested.connect(self._edit_artist_metadata)
        self._artist_detail.metadata_files_requested.connect(self._open_metadata_for_files)
        self._artist_detail.artist_enrich_requested.connect(self._refresh_artist_info)
        self._artist_detail.track_play_requested.connect(
            lambda fp: self._play_filepaths([fp], play_now=True))
        self._artist_detail.track_queue_requested.connect(
            lambda fp: self._play_filepaths([fp], play_now=False))
        self._artist_detail.track_metadata_requested.connect(
            lambda fp: self._open_metadata_for_files([fp]))

        # Genre grid + detail
        self._genre_grid = GenreGridWidget()
        self._genre_detail = GenreDetailView()
        self._genre_grid.genre_selected.connect(self._open_genre_detail)
        self._genre_grid.genre_play_requested.connect(self._play_genre)
        self._genre_grid.genre_shuffle_requested.connect(self._shuffle_genre)
        self._genre_grid.genre_queue_requested.connect(self._queue_genre)
        self._genre_grid.genre_playlist_requested.connect(self._create_playlist_from_genre)
        self._genre_grid.genre_metadata_requested.connect(self._edit_genre_metadata)
        self._genre_grid.genre_normalize_requested.connect(self._normalize_genre)
        self._genre_detail.back_requested.connect(self._genre_ctrl.back_to_overview)
        self._genre_detail.play_requested.connect(self._play_genre)
        self._genre_detail.shuffle_requested.connect(self._shuffle_genre)
        self._genre_detail.queue_requested.connect(self._queue_genre)
        self._genre_detail.playlist_requested.connect(self._create_playlist_from_genre)
        self._genre_detail.metadata_requested.connect(self._edit_genre_metadata)
        self._genre_detail.normalize_requested.connect(self._normalize_genre)
        self._genre_detail.track_play_requested.connect(
            lambda fp: self._play_filepaths([fp], play_now=True))
        self._genre_detail.track_queue_requested.connect(
            lambda fp: self._play_filepaths([fp], play_now=False))

        self._folder_browser = FolderBrowserWidget()
        self._folder_browser.folder_selected.connect(
            lambda fps: self._play_filepaths(fps, play_now=True))
        self._folder_browser.queue_requested.connect(
            lambda fps: self._play_filepaths(fps, play_now=False))
        self._folder_browser.scan_requested.connect(self._scan_path)
        self._folder_browser.create_playlist_requested.connect(
            self._on_folder_create_playlist)

        self._content = QStackedWidget()
        self._content.setMinimumHeight(200)

        self._views = ViewController(self._content, self)
        self._views.register("empty", placeholder)
        self._views.register("library", self._table)
        self._views.register("remote", self._remote_placeholder)
        self._views.register("coverflow", placeholder_albums)
        self._views.register("expanded", placeholder_expanded)
        self._views.register("radio", self._radio_widget)
        self._views.register("album_grid", self._album_grid)
        self._views.register("song_grid", self._song_grid)
        self._views.register("discover", self._discover)
        self._views.register("playlist_hub", self._playlist_hub)
        self._views.register("playlist_detail", self._playlist_detail)
        self._views.register("metadata_editor", self._metadata_editor)
        self._views.register("home_audio", self._home_audio_view)
        self._views.register("artist_grid", self._artist_grid)
        self._views.register("artist_detail", self._artist_detail)
        self._views.register("genre_grid", self._genre_grid)
        self._views.register("genre_detail", self._genre_detail)
        self._views.register("folders", self._folder_browser)
        self._views.register("identifier", self._identifier_view)
        self._views.show("empty")

        from ui.view_navigator import ViewNavigator
        self._nav = ViewNavigator(self._content, self._views, self._views)
        self._nav._widgets = [
            self._content, self._album_grid, self._song_grid,
            self._folder_browser, self._radio_widget,
            self._playlist_hub, self._metadata_editor,
            self._discover, self._identifier_view,
            self._home_audio_view,
        ]
        from core.background_theme_service import BackgroundThemeService
        self._bg_theme = BackgroundThemeService(self._content)
        from core.playback_controller import PlaybackController
        self._playback_ctrl = PlaybackController(self)

        # ── Content wrapper ──
        cw = QWidget()
        cw.setObjectName("contentSurface")
        cw.setStyleSheet(
            "QWidget#contentSurface {"
            "  background: #090B11;"
            "  border-left: 1px solid rgba(255,255,255,0.045);"
            "}")
        self._content.setStyleSheet(
            "QStackedWidget {"
            "  background: #090B11;"
            "  border: none;"
            "}")
        cl = QVBoxLayout(cw)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(header)
        cl.addWidget(self._content)

        # ── Splitter ──
        sp = QSplitter(Qt.Horizontal)
        sp.addWidget(self._sidebar)
        sp.addWidget(cw)
        sp.setCollapsible(0, False)
        sp.setCollapsible(1, False)
        sp.setStretchFactor(0, 0)
        sp.setStretchFactor(1, 1)
        sp.setSizes([320, 900])
        sp.setStyleSheet(
            "QSplitter::handle { background: rgba(255,255,255,0.08); width: 2px; }")

        # ── NowPlaying bar ──
        self._player_bar = NowPlayingBar()
        from ui.controllers.player_bar_controller import PlayerBarController
        self._player_bar_ctrl = PlayerBarController(self._player_bar)

        bar_wrapper = QWidget()
        bar_wrapper.setObjectName("bottomBarArea")
        bar_wrapper.setAttribute(Qt.WA_TranslucentBackground)
        bar_wrapper.setStyleSheet(
            "QWidget#bottomBarArea {"
            "  background: rgba(5,7,10,0.92);"
            "  border-top: 1px solid rgba(255,255,255,0.06);"
            "}")
        wl = QHBoxLayout(bar_wrapper)
        wl.setContentsMargins(24, 10, 24, 12)
        wl.addWidget(self._player_bar)

        cent = QWidget()
        cent.setObjectName("mainRoot")
        cent.setStyleSheet(
            "QWidget#mainRoot {"
            "  background: #090B11;"
            "}")
        layout = QVBoxLayout(cent)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        layout.addWidget(sp, stretch=1)
        layout.addWidget(bar_wrapper, stretch=0)
        self.setCentralWidget(cent)

    def _connect_signals(self):
        pb = self._player_bar
        self._player.position_changed.connect(pb.set_position)
        self._player.duration_changed.connect(pb.set_duration)
        self._player.state_changed.connect(self._on_state)
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
        pb.expanded_requested.connect(self._show_expanded)
        pb.transmit_clicked.connect(self._show_transmit_menu)
        pb.audio_output_clicked.connect(self._show_audio_output_menu)
        pb.mini_player_clicked.connect(self._open_mini_player)
        pb.cover_loaded.connect(self._bg_theme.apply)
        pb._quality_badge.clicked_details.connect(self._show_audio_diagnostics)

    def _setup_tray(self):
        from ui.controllers.tray_controller import TrayController
        self._tray_ctrl = TrayController(self)
        self._tray_ctrl.setup()
        self._tray = self._tray_ctrl._icon

    def _notify_track(self, title: str, artist: str):
        if hasattr(self, '_tray_ctrl'):
            self._tray_ctrl.notify(title, artist)

    def _import_playlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar playlist", os.path.expanduser("~"),
            "Playlists (*.m3u *.m3u8 *.pls);;Todos (*)")
        if not path:
            return
        from ui.playlist_io import import_playlist
        files = import_playlist(path)
        if not files:
            QMessageBox.information(
                self, "Importar", "No se encontraron archivos válidos.")
            return

        added = 0
        missing = 0
        for fp in files:
            if os.path.isfile(fp):
                self._db.add_file(fp)
                added += 1
            else:
                missing += 1

        self._load_library()
        if added:
            self._playback.enqueue(files[:added], play_now=False)
        self._player_bar_ctrl.set_track(
                f"Importados {added} temas", "Playlist")

        summary = f"<p><b>{added}</b> archivos añadidos a la biblioteca.</p>"
        if missing:
            summary += f"<p><b>{missing}</b> archivos no encontrados en disco.</p>"
        summary += f"<p>Total entradas en playlist: <b>{len(files)}</b></p>"
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
        self._all_items = self._db.get_all()
        self._items_index = {i.filepath: i for i in self._all_items}
        self._search_ctrl.set_active("local")
        self._apply_filters()
        self._rebuild_sidebar()

    def _apply_filters(self):
        self._search_ctrl.search(self._search_text)

    # ── Sidebar ──

    def _rebuild_sidebar(self):
        self._sidebar_controller.rebuild(load_servers())

        # Sidebar shadow
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setXOffset(3)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self._sidebar.setGraphicsEffect(shadow)

    def _on_sidebar_navigate(self, key: str):
        self._restore_central_opacity()
        self._current_playlist = None

        # Configure header based on section
        section_key = key.split(":")[0] if ":" in key else key
        if section_key == "srv":
            section_key = "servers"
        elif section_key == "dev":
            section_key = "devices"
        elif key.startswith("pl:"):
            section_key = "playlists"
        self._configure_header_for_section(section_key)
        if not self._nav_restoring:
            self._push_nav(key)

        # Dynamic pattern routes
        if key and key.startswith("pl:"):
            self._show_playlist_detail(key)
            return
        if key and key.startswith("srv:"):
            self._show_server(key)
            return
        if key and key.startswith("dev:"):
            self._show_device(key)
            return
        if key and key.startswith("mix_"):
            self._show_smart_mix(key)
            return

        # Static route dispatch
        method = NAV_ROUTES.get(key)
        if method and hasattr(self, method):
            getattr(self, method)(key)

    def _push_nav(self, key: str):
        if self._nav_history and self._nav_history[self._nav_history_index] == key:
            return
        if self._nav_history_index < len(self._nav_history) - 1:
            self._nav_history = self._nav_history[:self._nav_history_index + 1]
        self._nav_history.append(key)
        self._nav_history_index = len(self._nav_history) - 1
        self._update_nav_buttons()

    def _navigate_back(self):
        if self._nav_history_index > 0:
            self._nav_history_index -= 1
            self._nav_restoring = True
            try:
                key = self._nav_history[self._nav_history_index]
                self._on_sidebar_navigate(key)
            finally:
                self._nav_restoring = False
            self._update_nav_buttons()

    def _navigate_forward(self):
        if self._nav_history_index < len(self._nav_history) - 1:
            self._nav_history_index += 1
            self._nav_restoring = True
            try:
                key = self._nav_history[self._nav_history_index]
                self._on_sidebar_navigate(key)
            finally:
                self._nav_restoring = False
            self._update_nav_buttons()

    def _update_nav_buttons(self):
        if hasattr(self, '_back_btn'):
            self._back_btn.setEnabled(self._nav_history_index > 0)
        if hasattr(self, '_forward_btn'):
            self._forward_btn.setEnabled(
                self._nav_history_index < len(self._nav_history) - 1)

    # ── Static route handlers ──

    def _show_library(self, key):
        self._kind_filter = None
        self._search_ctrl.set_active("local")
        self._apply_filters()
        self._view_mode = "list"
        self._view_switcher.set_view("list", emit=False)

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

    def _show_artists(self, key):
        if not self._all_items and self._db:
            self._load_library()
        self._artist_repo.clear_current()
        self._artist_repo.build(self._all_items)
        self._artist_grid.set_artists(self._artist_repo.groups)
        if hasattr(self, '_artist_enrich'):
            from core.settings_manager import get_bool
            if get_bool("artist_enrichment/preload_visible"):
                self._artist_enrich.enrich_visible_artists(
                    self._artist_repo.groups, limit=12)
        if self._view_mode not in ("grid", "list"):
            self._view_mode = "grid"
            self._view_switcher.set_view("grid", emit=False)
        self._show_artists_view(self._view_mode)
        self._count.setText(f"{self._artist_repo.count} artistas")
        self._search.show()

    def _show_albums(self, key):
        self._section_title.setText("Álbumes")
        self._show_album_grid()
        self._search.show()

    def _show_genres(self, key):
        if not self._all_items and self._db:
            self._load_library()
        self._genre_ctrl.show_genres_overview(self._view_mode)

    def _show_folders(self, key):
        self._section_title.setText("Carpetas")
        from sources.folder_source import FolderSource
        self._search_ctrl.register("folders", FolderSource(os.path.expanduser("~")))
        self._search_ctrl.set_active("folders")
        self._views.show("folders")
        self._search.show()

    def _show_radio(self, key):
        self._search_ctrl.set_active("radio")
        self._current_section_key = "radio"
        self._radio_widget.reload()
        self._fade_content("radio")

    def _show_add_server(self, key):
        self._add_server()

    def _show_server(self, key):
        name = key.split(":", 1)[1]
        self._open_server(name)

    def _show_device(self, key):
        mount = key.split(":", 1)[1]
        import shutil
        usage = shutil.disk_usage(mount) if os.path.exists(mount) else None
        files = scan_device_music(mount)
        refs = [TrackRef(uri=fp, title=os.path.basename(fp), duration=0.0) for fp in files]
        self._model.populate(refs)
        device_name = os.path.basename(mount)
        if usage:
            total_gb = usage.total / (1024**3)
            free_gb = usage.free / (1024**3)
            used_pct = (1 - usage.free / usage.total) * 100
            self._section_title.setText(device_name)
            self._section_subtitle.setText(
                f"{free_gb:.1f} GB libre de {total_gb:.1f} GB · "
                f"{used_pct:.0f}% usado · {len(files)} canciones")
        else:
            self._section_title.setText(device_name)
            self._section_subtitle.setText(f"{len(files)} canciones")
        self._count.setText(f"{len(files)} archivos")
        self._views.show("library")
        self._table.setModel(self._model)
        self._search.show()

    def _show_discover(self, key):
        self._views.show("discover")

    def _show_smart_mix(self, key):
        from library.smart_mixes import (get_daily_mix, get_unplayed,
                                        get_popular, get_favorites_recent)
        self._section_title.setText({
            "mix_daily": "Mix diario", "mix_unplayed": "No escuchadas",
            "mix_popular": "Más escuchadas",
            "mix_favorites": "Favoritos recientes",
        }.get(key, "Mix"))
        mixes = {"mix_daily": get_daily_mix, "mix_unplayed": get_unplayed,
                "mix_popular": get_popular, "mix_favorites": get_favorites_recent}
        fn = mixes.get(key)
        if fn:
            files = fn()
            files = [f for f in files
                     if isinstance(f, str) and (f.startswith("http") or os.path.isfile(f))]
            if key in ("mix_unplayed", "mix_favorites"):
                items = [self._items_index.get(f) for f in files]
                items = [i for i in items if i]
                refs = [TrackRef(uri=i.filepath, title=i.title or os.path.basename(i.filepath),
                                 artist=i.artist, album=i.album, duration=i.duration,
                                 year=i.year, genre=i.genre) for i in items]
                self._model.populate(refs)
                self._current_refs = refs
                self._count.setText(f"{len(refs)} canciones")
                self._playlist_refs = refs
                if refs:
                    self._views.show("library")
                    self._table.setModel(self._model)
                    self._table.setColumnWidth(0, 72)
                    self._table.setColumnWidth(1, 260)
                    self._table.setColumnWidth(2, 170)
                    self._table.setColumnWidth(3, 170)
                    self._table.setColumnWidth(4, 55)
                    self._table.setColumnWidth(5, 110)
                    self._table.setColumnWidth(6, 75)
                else:
                    self._views.show("empty")
            elif files:
                self._play_filepaths(files, play_now=True)
                self._show_expanded()
            else:
                self._toast_svc.warning("El mix no contiene archivos disponibles")

    def _show_favs(self, key):
        favs = self._db.get_favorites()
        items = [self._items_index.get(fp) for fp in favs if self._items_index.get(fp)]
        refs = [TrackRef(uri=i.filepath, title=i.title or os.path.basename(i.filepath),
                         artist=i.artist, album=i.album, duration=i.duration,
                         year=i.year, genre=i.genre) for i in items]
        self._model.populate(refs)
        self._current_refs = refs
        self._count.setText(f"{len(refs)} canciones")
        if refs:
            self._views.show("library")
            self._table.setModel(self._model)
            self._table.setColumnWidth(0, 72)
            self._table.setColumnWidth(1, 260)
            self._table.setColumnWidth(2, 170)
            self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(4, 55)
            self._table.setColumnWidth(5, 110)
            self._table.setColumnWidth(6, 75)
        else:
            self._views.show("empty")
        self._search.show()

    def _show_recent(self, key):
        history = self._db.get_play_history()
        items = [self._items_index.get(h.get("track_id", ""))
                 for h in history[:50] if self._items_index.get(h.get("track_id", ""))]
        refs = [TrackRef(uri=i.filepath, title=i.title or os.path.basename(i.filepath),
                         artist=i.artist, album=i.album, duration=i.duration,
                         year=i.year, genre=i.genre) for i in items]
        self._model.populate(refs)
        self._current_refs = refs
        self._count.setText(f"{len(refs)} canciones")
        if refs:
            self._views.show("library")
            self._table.setModel(self._model)
            self._table.setColumnWidth(0, 72)
            self._table.setColumnWidth(1, 260)
            self._table.setColumnWidth(2, 170)
            self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(4, 55)
            self._table.setColumnWidth(5, 110)
            self._table.setColumnWidth(6, 75)
        else:
            self._views.show("empty")
        self._search.show()

    def _show_identifier(self, key):
        self._identifier_view.set_detected_tracks(
            self._db.get_detected_tracks(100))
        self._fade_content("identifier")

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
        if self._home_page is None:
            from ui.hubs.home_page import HomePage
            self._home_page = HomePage(db=self._db, playback=self._playback)
        if not self._views.widget("home"):
            self._views.register("home", self._home_page)
        self._fade_content("home")

    def _show_library_hub_page(self, key=None):
        if self._library_hub_page is None:
            from ui.hubs.library_hub_page import LibraryHubPage
            self._library_hub_page = LibraryHubPage(db=self._db, window=self)
        if not self._views.widget("library_hub"):
            self._views.register("library_hub", self._library_hub_page)
        if not self._views.widget("library_hub"):
            self._views.register("library_hub", self._library_hub_page)
        self._fade_content("library_hub")

    def _show_mix_hub_page(self, key=None):
        if self._mix_hub_page is None:
            from ui.hubs.mix_hub_page import MixHubPage
            self._mix_hub_page = MixHubPage()
        if not self._views.widget("mix_hub"):
            self._views.register("mix_hub", self._mix_hub_page)
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
            sync_mgr = getattr(self, '_sync_mgr', None)
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

    def _on_sidebar_menu(self, pos):
        widget = self._sidebar.childAt(pos)
        from ui.sidebar.sidebar_item import SidebarItem
        item = None
        while widget:
            if isinstance(widget, SidebarItem):
                item = widget
                break
            widget = widget.parentWidget()
        if not item:
            return
        key = item.key
        menu = QMenu(self)

        if key and key.startswith("pl:"):
            pid = int(key.split(":", 1)[1])
            menu.addAction("Eliminar playlist", lambda: self._delete_playlist(pid))

        elif key and key.startswith("srv:"):
            name = key.split(":", 1)[1]
            menu.addAction("Eliminar servidor", lambda: self._remove_server(name))

        if not menu.isEmpty():
            menu.exec(self._sidebar._container.mapToGlobal(pos))

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "Nueva playlist", "Nombre:")
        if ok and name.strip():
            self._db.create_playlist(name.strip())
            self._rebuild_sidebar()

    def _delete_playlist(self, pid):
        self._db.delete_playlist(pid)
        self._rebuild_sidebar()
        self._load_library()

    def _edit_playlist_dialog(self, pid: int):
        pl = next((p for p in self._db.get_playlists() if p["id"] == pid), None)
        if not pl:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Editar playlist — {pl['name']}")
        dlg.setMinimumWidth(400)
        layout = QFormLayout(dlg)

        name_edit = QLineEdit(pl.get("name", ""))
        layout.addRow("Nombre:", name_edit)

        desc_edit = QLineEdit(pl.get("description", ""))
        layout.addRow("Descripción:", desc_edit)

        cover_btn = QPushButton("Cambiar portada")
        cover_btn.clicked.connect(lambda: self._change_playlist_cover(pid))
        layout.addRow("Portada:", cover_btn)

        remove_btn = QPushButton("Quitar portada")
        remove_btn.clicked.connect(lambda: self._remove_playlist_cover(pid))
        layout.addRow("", remove_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self._save_playlist_edit(pid, name_edit.text(), desc_edit.text(), dlg))
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)

        dlg.exec()

    def _change_playlist_cover(self, pid: int):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar portada", "",
            "Imágenes (*.jpg *.jpeg *.png);;Todos (*)")
        if path:
            from ui.services.playlist_cover_service import copy_custom_cover
            cover_path = copy_custom_cover(pid, path)
            self._db.update_playlist(pid, cover_path=cover_path, cover_type="custom")
            self._toast_svc.show("Portada actualizada", "success")

    def _remove_playlist_cover(self, pid: int):
        from ui.services.playlist_cover_service import remove_custom_cover
        remove_custom_cover(pid)
        self._db.update_playlist(pid, cover_path="", cover_type="mosaic")
        self._toast_svc.show("Portada eliminada — se usará mosaico automático", "info")

    def _save_playlist_edit(self, pid: int, name: str, desc: str, dlg):
        self._db.update_playlist(pid, name=name, description=desc)
        self._rebuild_sidebar()
        self._toast_svc.show("Playlist actualizada", "success")
        dlg.accept()

    # ── Navidrome / Jellyfin ──

    def _add_server(self):
        dlg = ServerDialog(self)
        if dlg.exec() and dlg.server:
            servers = load_servers()
            servers.append(dlg.server)
            save_servers(servers)
            self._rebuild_sidebar()

    def _open_server(self, name: str):
        servers = load_servers()
        srv_data = next((s for s in servers if s.name == name), None)
        if not srv_data:
            QMessageBox.warning(self, "Error", f"Servidor '{name}' no encontrado.")
            return

        try:
            client = SubsonicClient(srv_data)
            self._remote_browser = RemoteBrowser(client, name)
            self._remote_browser._workers = self._workers
            self._remote_browser.track_selected.connect(self._play_stream)
            self._views.replace("remote", self._remote_browser)
            self._views.show("remote")

            self._remote_browser.load_artists()
            self._section_title.setText(name)
            from sources.subsonic_source import SubsonicSource
            srv_key = f"srv:{name}"
            self._search_ctrl.register(srv_key, SubsonicSource(client))
            self._search_ctrl.set_active(srv_key)
            self._search.show()
        except AuthError as e:
            QMessageBox.warning(self, "Error de autenticación",
                f"No se pudo autenticar con '{name}':\n{e}")
        except ServerNotFoundError as e:
            QMessageBox.warning(self, "Servidor no encontrado",
                f"No se puede conectar a '{name}':\n{e}")
        except SubsonicError as e:
            QMessageBox.warning(self, "Error de conexión",
                f"No se pudo conectar a '{name}':\n{e}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo conectar:\n{e}")

    def _remove_server(self, name: str):
        if QMessageBox.question(self, "Eliminar",
            f"¿Eliminar servidor '{name}'?") == QMessageBox.Yes:
            servers = [s for s in load_servers() if s.name != name]
            save_servers(servers)
            self._rebuild_sidebar()
            self._load_library()

    def _play_stream(self, url: str, title: str, artist: str, album: str = ""):
        self._play_trackref(TrackRef(
            uri=url, title=title, artist=artist, album=album,
            source_type="remote_stream", source_label="Servidor remoto"))

    def _play_radio(self, url: str, name: str):
        self._play_trackref(TrackRef(
            uri=url, title=name, artist="Radio",
            source_type="radio", source_label=name))

    def _on_radio_count(self, visible: int, total: int):
        if self._current_section_key == "radio":
            if visible != total:
                self._count.setText(f"{visible} de {total} emisoras")
            else:
                self._count.setText(f"{total} emisoras")

    # ── Search ──

    def _on_search(self, text: str):
        self._search_text = text.strip()
        if self._current_section_key == "artists" and not self._artist_repo.current_key:
            query = self._search_text.lower()
            if not query:
                filtered = self._artist_repo.groups
            else:
                filtered = [
                    g for g in self._artist_repo.groups
                    if query in g.display_name.lower()
                    or any(query in a.title.lower() for a in g.albums)
                    or any(query in (t.title or "").lower() for t in g.all_tracks)
                    or any(query in g.lower() for g in g.genres)
                ]
            self._artist_grid.set_artists(filtered)
            self._count.setText(f"{len(filtered)} artistas")
            return
        if self._current_section_key == "radio":
            self._radio_widget.set_filter(self._search_text)
            return
        self._apply_filters()

    def _on_search_results(self, results: list):
        self._model.populate(results)
        n = len(results)
        self._count.setText(f"{n} elementos" if n else "0 elementos")
        if n:
            self._views.show("library")
            self._table.setModel(self._model)
            self._table.setColumnWidth(0, 72)
            self._table.setColumnWidth(1, 260)
            self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(4, 55)
            self._table.setColumnWidth(5, 110)
            self._table.setColumnWidth(6, 75)
        else:
            self._views.show("empty")

    # ── View Mode Router ──

    def _on_view_mode_changed(self, mode: str):
        self._restore_central_opacity()
        available = self._current_available_views()
        if mode not in available:
            return
        if mode == "coverflow" and self._current_section_key != "albums":
            return
        self._view_mode = mode
        self._show_current_section_view(mode)
        self._restore_central_opacity()

    def _current_available_views(self) -> list[str]:
        config = _resolve_section_config(self._current_section_key, {})
        return config.get("views", [])

    def _show_current_section_view(self, mode: str):
        section = self._current_section_key

        if section == "library":
            if mode == "list":
                self._apply_filters()
                self._fade_content("library")
            elif mode == "grid":
                self._show_song_grid()
                self._fade_content("song_grid")

        elif section == "albums":
            if mode == "list":
                self._show_album_list()
                self._fade_content("library")
            elif mode == "grid":
                self._show_album_grid()
                self._fade_content("album_grid")
            elif mode == "coverflow":
                self._show_coverflow()
                self._fade_content("coverflow")

        elif section == "artists":
            self._show_artists_view(mode)

        elif section == "playlists":
            if not self._playlist_refs:
                self._views.show("empty")
                return
            if mode == "list":
                self._model.populate(self._playlist_refs)
                self._table.setModel(self._model)
                self._fade_content("library")
            elif mode == "grid":
                self._song_grid.set_items(self._playlist_refs, card_size=170)
                self._fade_content("song_grid")

        elif section == "folders":
            self._fade_content("folders")

        elif section == "radio":
            self._fade_content("radio")

        elif section == "playlist_hub":
            self._playlist_hub.set_playlists(self._db.get_playlists())
            self._fade_content("playlist_hub")

        elif section in ("favs", "recent", "mix_unplayed"):
            refs = getattr(self, "_current_refs", [])
            if not refs:
                self._views.show("empty")
                return
            if mode == "list":
                self._model.populate(refs)
                self._table.setModel(self._model)
                self._fade_content("library")
            elif mode == "grid":
                self._song_grid.set_items(refs, card_size=170)
                self._fade_content("song_grid")

    def _show_album_list(self):
        from library.album_art import group_by_album
        groups = group_by_album(self._all_items)
        refs = []
        for album, artist, tracks in groups:
            dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
            year = tracks[0].year if tracks else ""
            refs.append(TrackRef(
                uri=album, title=album,
                artist=artist, album=album,
                duration=float(dur),
                genre=f"{len(tracks)} canciones",
                year=year,
                cover_path="",
            ))
        self._model.populate(refs)
        self._table.setModel(self._model)
        self._table.setColumnWidth(0, 72)
        self._table.setColumnWidth(1, 240)
        self._table.setColumnWidth(2, 170)
        self._table.setColumnWidth(3, 170)
        self._table.setColumnWidth(4, 55)
        self._table.setColumnWidth(5, 110)
        self._table.setColumnWidth(6, 75)
        self._count.setText(f"{len(groups)} álbumes")

    def _configure_header_for_section(self, section_key: str):
        self._current_section_key = section_key
        config = _resolve_section_config(section_key)
        title = config.get("title", "Todas las canciones")
        subtitle = config.get("subtitle", "")
        icon_name = config.get("icon", "sidebar_library")
        views = config.get("views", ["list", "grid"])
        search = config.get("search", True)
        default = config.get("default", "list")

        self._section_title.setText(title)
        subtitle = self._build_breadcrumb_subtitle(subtitle, section_key)
        self._section_subtitle.setText(subtitle)

        # Set section icon
        pix = get_pixmap(icon_name, size=26)
        if not pix.isNull():
            self._section_icon.setPixmap(pix)
        else:
            self._section_icon.clear()

        # Search placeholder contextual
        searchers = {
            "library": "Buscar canciones...", "albums": "Buscar álbumes...",
            "artists": "Buscar artistas...", "playlists": "Buscar en playlist...",
            "folders": "Buscar carpeta...", "radio": "Buscar emisoras...",
            "playlist_hub": "Buscar playlists...", "favs": "Buscar favoritos...",
            "recent": "Buscar recientes...", "mix_unplayed": "Buscar canciones...",
            "discover": "", "identifier": "", "metadata_editor": "",
            "home_audio": "",
            "assistant": "",
            "metadata_review": "",
            "audio_lab": "",
            "michi_disc_lab": "",
            "home": "",
            "library_hub": "",
            "mix_hub": "",
            "playback_hub": "",
            "connections_hub": "",
            "settings_hub": "",
            "devices_page": "",
            "devices": "",
        }
        self._search.setPlaceholderText(searchers.get(section_key, "Buscar..."))
        self._search.setVisible(search)

        self._view_switcher.set_available_modes(views, default, context=section_key)
        self._view_switcher.update_for_width(self.width())

        if self._view_mode not in views and default:
            self._view_mode = default
            self._view_switcher.set_view(default, emit=False)

        if not search:
            self._search.hide()

        # Show/hide album controls
        show_album_ctrl = (section_key == "albums")
        self._album_sort_btn.setVisible(show_album_ctrl)
        self._album_filter_btn.setVisible(show_album_ctrl)

    def _setup_album_sort_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(22,24,31,0.97);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                padding: 6px 4px;
                color: rgba(255,255,255,0.88); font-size: 12.5px;
            }
            QMenu::item {
                padding: 7px 32px 7px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(255,255,255,0.09);
            }
        """)

        sort_opts = [
            ("Título", "title"),
            ("Artista", "artist"),
            ("Año", "year"),
            ("Duración", "duration"),
            ("Canciones", "tracks"),
        ]
        for label, key in sort_opts:
            action = menu.addAction(label)
            action.setData(key)
            action.triggered.connect(
                lambda checked=False, k=key: self._on_album_sort(k))
        self._album_sort_btn.setMenu(menu)

    def _setup_album_filter_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(22,24,31,0.97);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                padding: 6px 4px;
                color: rgba(255,255,255,0.88); font-size: 12.5px;
            }
            QMenu::item {
                padding: 7px 32px 7px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(255,255,255,0.09);
            }
        """)

        filter_opts = [
            ("Todos", "all"),
            ("Sin carátula", "no_cover"),
            ("Incompletos", "incomplete"),
            ("FLAC", "flac"),
            ("MP3", "mp3"),
        ]
        for label, key in filter_opts:
            action = menu.addAction(label)
            action.setData(key)
            action.triggered.connect(
                lambda checked=False, k=key: self._on_album_filter(k))
        self._album_filter_btn.setMenu(menu)

    def _on_album_sort(self, key: str):
        self._album_sort_key = key
        self._coverflow_cache_key = None
        if self._current_section_key == "albums" and self._view_mode == "grid":
            self._show_album_grid()

    def _on_album_filter(self, key: str):
        self._album_filter_mode = key
        self._coverflow_cache_key = None
        if self._current_section_key == "albums" and self._view_mode == "grid":
            self._show_album_grid()

    def _fade_content(self, target: str):
        self._nav.show(target)

    def _restore_central_opacity(self):
        self._nav.restore_opacity()

    def _show_list_view(self):
        self._view_switcher.set_view("list", emit=False)
        self._on_view_mode_changed("list")

    def _show_grid_view(self):
        self._view_switcher.set_view("grid", emit=False)
        self._on_view_mode_changed("grid")

    def _show_album_grid(self):
        self._album_grid.set_items(self._all_items, 200,
                                   sort_key=getattr(self, '_album_sort_key', 'title'),
                                   filter_mode=getattr(self, '_album_filter_mode', 'all'))
        from library.album_art import group_by_album
        groups = group_by_album(self._all_items)
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

    def _show_coverflow_view(self):
        self._view_switcher.set_view("coverflow", emit=False)
        self._on_view_mode_changed("coverflow")

    def _show_coverflow(self):
        items = self._all_items
        if self._kind_filter:
            items = [i for i in items if i.kind == self._kind_filter]

        # Cache key — skip rebuild if nothing changed
        cache_key = (len(items), self._album_sort_key, self._album_filter_mode, self._search_text)
        if self._coverflow is not None and cache_key == self._coverflow_cache_key:
            self._views.show("coverflow")
            self._count.setText(f"{len(self._coverflow._items)} álbumes")
            self._coverflow.setFocus()
            return
        self._coverflow_cache_key = cache_key

        covers = load_covers_for_albums(items, 260, lazy=True)

        if not covers:
            self._views.show("empty")
            self._count.setText("0 álbumes")
            return

        if self._coverflow is None:
            self._coverflow = CoverFlowWidget()
            self._coverflow.double_clicked.connect(self._on_coverflow_dbl)
            self._coverflow.cover_snapped.connect(self._on_coverflow_snap)
            self._coverflow.request_cover.connect(self._on_coverflow_cover_request)
            self._coverflow.play_album_requested.connect(self._on_coverflow_play_album)
            self._coverflow.queue_album_requested.connect(self._on_coverflow_queue_album)
            self._coverflow.playlist_album_requested.connect(self._on_coverflow_playlist_album)
            self._coverflow.metadata_album_requested.connect(self._on_coverflow_metadata_album)
            self._coverflow.details_album_requested.connect(self._on_coverflow_details_album)
            self._coverflow.cover_search_requested.connect(self._on_coverflow_search_cover)
            self._coverflow.open_folder_requested.connect(self._on_coverflow_open_folder)

            # AlbumInfoBanner below CoverFlow
            from ui.album_info_banner import AlbumInfoBanner
            self._album_banner = AlbumInfoBanner()
            self._album_banner.play_requested.connect(self._on_banner_play)
            self._album_banner.queue_requested.connect(self._on_banner_queue)
            self._album_banner.details_requested.connect(self._on_banner_details)

            coverflow_page = QWidget()
            coverflow_page.setStyleSheet("background: #090B11;")
            cv_layout = QVBoxLayout(coverflow_page)
            cv_layout.setContentsMargins(0, 0, 0, 0)
            cv_layout.setSpacing(8)
            cv_layout.addWidget(self._coverflow, stretch=1)
            cv_layout.addWidget(self._album_banner, stretch=0)
            self._views.register("coverflow", coverflow_page)

        self._coverflow.set_items(covers)
        self._views.show("coverflow")
        self._count.setText(f"{len(covers)} álbumes")
        self._coverflow.setFocus()

    def _on_coverflow_dbl(self, index: int):
        if not self._coverflow or index >= len(self._coverflow._items):
            return
        item = self._coverflow._items[index]
        data = item.data or {}
        tracks = data.get("tracks", [])
        if tracks:
            filepaths = [t.filepath for t in tracks]
            self._play_filepaths(filepaths, play_now=True)
            self._show_expanded()

    def _on_coverflow_snap(self, index: int):
        if not self._coverflow or index >= len(self._coverflow._items):
            return

        # Update album info banner using repository
        if hasattr(self, '_album_banner') and hasattr(self, '_album_repo'):
            item = self._coverflow._items[index]
            tracks = item.data.get("tracks", []) if item.data else []
            key = _album_key(item, tracks)
            summary = self._album_repo.get_summary(key, fallback_data=tracks)
            if summary:
                self._album_banner.set_album_summary(summary)

            # Trigger MusicBrainz album enrichment for external metadata
            self._enrich_album_background(key, item, tracks)

            # Trigger artist enrichment for CoverFlow-navigated artist
            if hasattr(self, '_artist_enrich') and item and item.subtitle:
                from library.artist_grouping import normalize_artist_name
                artist_key = normalize_artist_name(item.subtitle)
                self._artist_enrich.enrich_artist_by_key(artist_key, item.subtitle)

            # Precarga vecinos ±2
            for off in (-2, -1, 1, 2):
                ni = index + off
                if 0 <= ni < len(self._coverflow._items):
                    n_item = self._coverflow._items[ni]
                    n_tracks = n_item.data.get("tracks", []) if n_item.data else []
                    n_key = _album_key(n_item, n_tracks)
                    if n_key not in self._album_repo._lru:
                        self._album_repo.get_summary(n_key, fallback_data=n_tracks)

    def _coverflow_album_tracks(self, idx: int) -> list:
        item = self._coverflow.item_at(idx) if self._coverflow else None
        if not item:
            return []
        return item.data.get("tracks", [])

    def _on_coverflow_play_album(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._play_filepaths(fps, play_now=True)

    def _on_coverflow_queue_album(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._playback.enqueue(fps, play_now=False)

    def _on_coverflow_playlist_album(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        if not tracks:
            return
        album_name = tracks[0].album or "Álbum"
        pid = self._db.create_playlist(album_name)
        for t in tracks:
            if os.path.isfile(t.filepath):
                self._db.add_to_playlist(pid, t.filepath)
        self._rebuild_sidebar()
        self._toast_svc.show(f"Playlist creada: {album_name}", "success")

    def _on_coverflow_metadata_album(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._open_metadata_for_files(fps)

    def _enrich_album_background(self, key: str, item, tracks):
        """Trigger MusicBrainz album enrichment for CoverFlow-navigated albums."""
        if not key or not tracks:
            return
        try:
            from integrations.artist_metadata.album_enrichment_service import AlbumEnrichmentService
            from library.album_key import make_artist_key
            if not hasattr(self, '_album_enrich'):
                self._album_enrich = AlbumEnrichmentService()
                self._album_enrich.album_enriched.connect(self._on_album_enriched)
            album_name = getattr(tracks[0], 'album', '') if tracks else ''
            artist_name = item.subtitle if item and item.subtitle else (
                getattr(tracks[0], 'albumartist', '') or getattr(tracks[0], 'artist', ''))
            if album_name and artist_name:
                artist_key = make_artist_key(artist_name)
                self._album_enrich.enrich_album(key, album_name, artist_key, artist_name)
        except Exception:
            pass

    def _on_album_enriched(self, album_key: str, data: dict):
        """Handle MusicBrainz album enrichment result — update banner if visible."""
        if not hasattr(self, '_album_repo') or not data:
            return
        self._album_repo.update_enrichment(album_key, data)
        if hasattr(self, '_album_banner') and self._album_banner:
            summary = self._album_repo.get_cached(album_key)
            if summary:
                self._album_banner.set_album_summary(summary)

    def _on_coverflow_details_album(self, idx: int):
        item = self._coverflow.item_at(idx) if self._coverflow else None
        if not item:
            return
        tracks = item.data.get("tracks", [])
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur > 0 else "—"
        exts = set((getattr(t, 'ext', '') or '').upper().lstrip(".") for t in tracks if getattr(t, 'ext', ''))
        fmt_str = ", ".join(sorted(exts)) or "—"
        msg = (f"Álbum: {item.title}\nArtista: {item.subtitle or '—'}\n"
               f"Canciones: {count}\nDuración: {dur_str}\nFormatos: {fmt_str}")
        QMessageBox.information(self, "Detalles del álbum", msg)

    def _on_coverflow_search_cover(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        if tracks:
            d = os.path.dirname(tracks[0].filepath) if tracks else ""
            self._toast_svc.show(f"Buscar carátula en: {d}", "info")

    def _on_coverflow_open_folder(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        if tracks:
            d = os.path.dirname(tracks[0].filepath)
            import subprocess
            subprocess.Popen(["xdg-open", d])

    def _on_banner_play(self, album_key: str = ""):
        idx = int(album_key) if album_key.isdigit() else self._coverflow.current_index()
        self._on_coverflow_play_album(idx)

    def _on_banner_queue(self, album_key: str = ""):
        idx = int(album_key) if album_key.isdigit() else self._coverflow.current_index()
        self._on_coverflow_queue_album(idx)

    def _on_banner_details(self, album_key: str = ""):
        idx = int(album_key) if album_key.isdigit() else self._coverflow.current_index()
        self._on_coverflow_details_album(idx)

    def _on_coverflow_cover_request(self, idx: int, item):
        """Lazy-load cover art for a CoverFlow item."""
        from library.album_art import load_cover_pixmap
        tracks = item.data.get("tracks", []) if item.data else []
        if tracks:
            pix = load_cover_pixmap(tracks[0].filepath, self._coverflow._cover_w)
            if pix and not pix.isNull():
                self._coverflow._on_cover_loaded(idx, pix)

    # Extracted to ui/controllers/album_controller.py — album grid + detail actions

    def _on_album_create_playlist(self, fps: list):
        self._album_ctrl.create_playlist(fps)

    def _on_album_search_cover(self, group):
        self._album_ctrl.search_cover(group)

    def _on_album_open_folder(self, folder: str):
        self._album_ctrl.open_folder(folder)

    def _on_album_show_details(self, group):
        self._album_ctrl.show_details(group)

    # Extracted to ui/controllers/playlist_controller.py — Hub + import/export

    def _import_m3u(self):
        self._playlist_ctrl.import_m3u()

    def _export_playlists(self):
        self._playlist_ctrl.export_playlists()

    def _open_smart_playlist(self, key: str):
        self._playlist_ctrl.open_smart_playlist(key)

    def _on_hub_playlist_play(self, pid: int):
        self._playlist_ctrl.hub_playlist_play(pid)

    def _on_hub_playlist_queue(self, pid: int):
        self._playlist_ctrl.hub_playlist_queue(pid)

    def _on_hub_create_from_folder(self):
        self._playlist_ctrl.hub_create_from_folder()

    def _on_hub_create_from_queue(self):
        self._playlist_ctrl.hub_create_from_queue()

    def _on_metadata_saved(self, filepaths: list):
        self._playlist_ctrl.metadata_saved(filepaths)

    def _refresh_library(self):
        self._playlist_ctrl.refresh_library()

    # Extracted to ui/controllers/artist_controller.py — grid + detail logic

    def _show_artists_view(self, mode: str):
        self._artist_ctrl.show_artists_view(mode)

    def _open_artist_detail(self, artist_key: str):
        self._artist_ctrl.open_artist_detail(artist_key)
        # Trigger enrichment for this artist
        if hasattr(self, '_artist_enrich'):
            repo = self._ctx.artist_repo
            group = repo.get_group(artist_key)
            if group:
                self._artist_enrich.enrich_artist(group)

    def _show_artists_overview(self):
        self._artist_ctrl.show_artists_overview()

    def _artist_filepaths(self, artist_key: str) -> list[str]:
        return self._artist_ctrl.artist_filepaths(artist_key)

    def _play_artist(self, artist_key: str):
        self._artist_ctrl.play_artist(artist_key)

    def _shuffle_artist(self, artist_key: str):
        self._artist_ctrl.play_artist(artist_key, shuffle=True)

    def _queue_artist(self, artist_key: str):
        self._artist_ctrl.queue_artist(artist_key)

    def _create_playlist_from_artist(self, artist_key: str):
        self._artist_ctrl.create_playlist_from_artist(artist_key)

    def _edit_artist_metadata(self, artist_key: str):
        self._artist_ctrl.edit_artist_metadata(artist_key)

    # ── Genre handlers ──

    def _open_genre_detail(self, genre_key: str):
        self._genre_ctrl.open_genre_detail(genre_key)

    def _play_genre(self, genre_key: str):
        self._genre_ctrl.play_genre(genre_key)

    def _shuffle_genre(self, genre_key: str):
        self._genre_ctrl.play_genre(genre_key, shuffle=True)

    def _queue_genre(self, genre_key: str):
        self._genre_ctrl.queue_genre(genre_key)

    def _create_playlist_from_genre(self, genre_key: str):
        self._genre_ctrl.create_playlist_from_genre(genre_key)

    def _edit_genre_metadata(self, genre_key: str):
        self._genre_ctrl.edit_genre_metadata(genre_key)

    def _normalize_genre(self, genre_key: str):
        self._genre_ctrl.normalize_genre(genre_key)

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
        """Show cover art in a premium popup — does NOT replace central content."""
        from PySide6.QtWidgets import QDialog
        current = self._playback.current
        cover_path = ""
        if current:
            from library.cover_art_service import CoverArtService
            cover_path = CoverArtService.find_cover(current)
        dlg = QDialog(self)
        dlg.setWindowTitle("Carátula")
        dlg.setFixedSize(460, 460)
        dlg.setStyleSheet(dialog_qss())
        from PySide6.QtWidgets import QVBoxLayout, QLabel
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        if cover_path:
            pix = QPixmap(cover_path)
            if not pix.isNull():
                lbl.setPixmap(pix.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(lbl)
        dlg.exec()

    def _show_nowplaying_details(self):
        """Show track details in a premium popover menu — does NOT replace central content."""
        from PySide6.QtWidgets import QMenu
        from ui.premium_menus import premium_menu_qss
        menu = QMenu(self)
        menu.setStyleSheet(premium_menu_qss())
        current = self._playback.current
        name = os.path.basename(current) if current else "Sin reproducción"
        ref = self._current_ref
        artist = ref.artist if ref else ""
        album = ref.album if ref else ""

        menu.addAction(f"Título: {name}").setEnabled(False)
        if artist:
            menu.addAction(f"Artista: {artist}").setEnabled(False)
        if album:
            menu.addAction(f"Álbum: {album}").setEnabled(False)
        menu.addSeparator()
        if current and not current.startswith("http"):
            menu.addAction("Abrir carpeta", lambda: self._on_album_open_folder(os.path.dirname(current)))
            menu.addAction("Editar metadatos", lambda: self._open_metadata_for_files([current]))

        btn = self._player_bar._cover
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _show_expanded(self):
        self._expanded_ctrl.show_expanded()

    def _on_expanded_back(self):
        self._expanded_ctrl.back()

    def _on_expanded_prev(self):
        self._expanded_ctrl.prev()

    def _on_expanded_next(self):
        self._expanded_ctrl.next()

    def _on_queue_track(self, filepath: str):
        self._expanded_ctrl.queue_track(filepath)

    # Extracted to core/file_actions.py — open/scan/drop logic

    def _open_file(self):
        self._file_actions.open_files(ALL_EXTS)

    def _add_folder(self):
        self._file_actions.add_folder()

    def _on_folder_create_playlist(self, name: str, filepaths: list):
        self._file_actions.folder_create_playlist(name, filepaths)

    def _scan_path(self, path: str):
        self._file_actions.scan_path(path)

    # Extracted to core/playback_controller.py — play/pause/queue logic

    def _on_table_menu(self, pos):
        self._playback_ctrl.on_table_menu(pos)

    def _edit_tags(self, filepath: str):
        self._playback_ctrl.edit_tags(filepath)

    def _on_table_dbl(self, idx):
        self._playback_ctrl.on_table_dbl(idx)

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
        if hasattr(self, '_identifier_ctrl'):
            self._identifier_ctrl.set_current_track(
                source_type=track.source_type,
                source_label=track.source_label,
                uri=track.uri,
                title=track.title,
                artist=track.artist)
        self._playback_ctrl.play_trackref(track)

    def _play_file(self, filepath: str, add_to_queue: bool = False):
        self._playback_ctrl.play_file(filepath, add_to_queue)

    def _on_state(self, state: PlaybackState):
        self._playback_ctrl.on_state(state)

    def _on_stop(self):
        self._playback_ctrl.on_stop()

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
        """Show audio route diagnostics dialog."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
        dlg = QDialog(self)
        dlg.setWindowTitle("Diagnostico de ruta de audio")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(
            "QDialog { background: rgba(15,17,22,0.96);"
            " border: 1px solid rgba(255,255,255,0.07);"
            " border-radius: 16px; }"
            "QLabel { background: transparent; }")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        try:
            diag = self._playback.get_audio_diagnostics()
            lines = diag.to_tooltip().split("\n") if diag else ["Sin diagnóstico"]
        except Exception:
            lines = ["Diagnostico no disponible"]

        title = QLabel("Ruta de audio activa")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 740; color: rgba(255,255,255,0.92);")
        layout.addWidget(title)
        layout.addSpacing(8)

        for line in lines:
            lbl = QLabel(line)
            lbl.setStyleSheet(
                "font-size: 12px; color: rgba(255,255,255,0.62);"
                "font-family: monospace;")
            layout.addWidget(lbl)

        layout.addSpacing(12)
        close_btn = QLabel("Clic para cerrar")
        close_btn.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.32);")
        close_btn.setAlignment(Qt.AlignCenter)
        layout.addWidget(close_btn)
        dlg.mousePressEvent = lambda e: dlg.accept()
        dlg.exec()

    def _open_mini_player(self):
        self._mini_player_ctrl.open()

    def _add_transmit_device(self):
        self._transmit_ctrl.add_device()

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

    def _on_home_audio_connect(self):
        from core.settings_manager import get_bool, get_str
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox)
        dlg = QDialog(self)
        dlg.setWindowTitle("Conectar Home Assistant")
        dlg.setMinimumWidth(440)
        layout = QFormLayout(dlg)
        layout.setSpacing(10)

        saved_url = get_str("home_audio/ha_base_url") or ""
        saved_token = get_str("home_audio/ha_token") or ""

        url_edit = QLineEdit(saved_url)
        url_edit.setPlaceholderText("http://homeassistant.local:8123")
        token_edit = QLineEdit(saved_token)
        token_edit.setEchoMode(QLineEdit.Password)
        token_edit.setPlaceholderText("Token de acceso de larga duracion")
        verify_cb = QCheckBox("Verificar SSL")
        verify_cb.setChecked(get_bool("home_audio/ha_verify_ssl"))
        verify_cb.setStyleSheet("color: rgba(255,255,255,0.72);")

        layout.addRow("URL:", url_edit)
        layout.addRow("Token:", token_edit)
        layout.addRow("", verify_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self._try_ha_connection(
            url_edit.text().strip(), token_edit.text().strip(), dlg, verify_cb.isChecked()))
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        dlg.exec()

    def _try_ha_connection(self, url: str, token: str, dialog, verify_ssl: bool = True):
        from core.settings_manager import set_ as sset, get_bool
        sset("home_audio/ha_base_url", url)
        sset("home_audio/ha_token", token)
        sset("home_audio/ha_verify_ssl", verify_ssl)
        dialog.accept()

        if not hasattr(self, '_ha_client'):
            from integrations.home_assistant.client import HomeAssistantClient
            self._ha_client = HomeAssistantClient(self)
            self._ha_client.connection_tested.connect(
                self._on_ha_connection_result)
            self._ha_client.entities_loaded.connect(
                self._on_ha_entities_loaded)
            self._ha_client.error_occurred.connect(self._on_ha_error)

        self._toast_svc.show("Probando conexion con Home Assistant...", "info")
        self._ha_client.configure(
            url, token, get_bool("home_audio/ha_verify_ssl"))
        self._ha_client.test_connection()

    def _on_ha_connection_result(self, ok: bool, msg: str):
        if ok:
            self._ha_connected = True
            self._home_audio_view.set_data(
                ha_connected=True, multiroom_active=False,
                snapserver_running=False, devices=[], groups=[])
            self._ha_client.get_media_players()
            self._toast_svc.show(f"Home Assistant: {msg}", "success")
        else:
            self._ha_connected = False
            self._toast_svc.show(f"Error: {msg}", "error")

    def _on_ha_entities_loaded(self, entities: list):
        from integrations.home_assistant.client import entity_to_device
        devices = [entity_to_device(e) for e in entities]
        self._home_audio_view.set_data(
            ha_connected=True, multiroom_active=False,
            snapserver_running=False, devices=devices, groups=[])
        n = len([d for d in devices if d.get("available")])
        self._toast_svc.show(
            f"Home Assistant: {n} media_player disponibles", "info")

    def _on_ha_error(self, msg: str):
        self._toast_svc.show(f"Home Assistant: {msg}", "error")

    def _on_home_audio_refresh(self):
        if hasattr(self, '_snap_discovery'):
            self._snap_discovery.refresh()
        if hasattr(self, '_ha_client') and getattr(self, '_ha_connected', False):
            self._ha_client.get_media_players()
        else:
            self._refresh_home_audio_state()

    def _on_home_audio_multiroom(self, enable: bool):
        from core.settings_manager import get_int
        if enable:
            # Start Michi API
            if not self._michi_api.is_running:
                self._michi_api.start()
            # Start local media server
            if not self._local_media.is_running:
                self._local_media.configure(get_int("home_audio/local_media_server_port"))
                self._local_media.start()
            # Start mDNS
            if not self._mdns.is_running and self._mdns.is_available:
                self._mdns.configure(port=self._michi_api.port)
                self._mdns.start()

            if not self._snapserver.is_binary_available():
                self._toast_svc.show(
                    "snapserver no encontrado. Instala snapcast para usar multiroom.",
                    "error")
                self._home_audio_view.set_data(
                    ha_connected=getattr(self, '_ha_connected', False),
                    multiroom_active=False,
                    snapserver_running=False,
                    devices=self._home_audio_view._devices,
                    groups=self._group_mgr.groups())
                return
            self._snapserver.configure(
                tcp=get_int("home_audio/snapserver_tcp_port"),
                ctrl=get_int("home_audio/snapserver_control_port"),
                http=get_int("home_audio/snapserver_http_port"))
            self._audio_capture.create_sink()
        else:
            self._snapserver.stop()
            self._audio_capture.remove_sink()
            self._mdns.stop()
            self._michi_api.stop()
            self._local_media.stop()

    def _on_home_audio_settings(self):
        self._show_preferences("home_audio")

    def _on_home_audio_receiver_wizard(self):
        from integrations.snapcast.receivers import ReceiverWizard
        dlg = ReceiverWizard(self)
        dlg.exec()

    def _on_home_audio_cast(self, device: dict):
        if hasattr(self, '_ha_ctrl'):
            self._ha_ctrl.cast_current(device)
        else:
            self._toast_svc.show("Controlador Home Audio no disponible", "error")

    def _on_home_audio_device_play(self, device: dict):
        if not hasattr(self, '_ha_client'):
            self._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._ha_client.media_play(device.get("entity_id", ""))

    def _on_home_audio_device_pause(self, device: dict):
        if not hasattr(self, '_ha_client'):
            self._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._ha_client.media_pause(device.get("entity_id", ""))

    def _on_home_audio_device_stop(self, device: dict):
        if not hasattr(self, '_ha_client'):
            self._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._ha_client.media_stop(device.get("entity_id", ""))

    def _on_home_audio_device_volume(self, device: dict, volume: int):
        if not hasattr(self, '_ha_client'):
            self._toast_svc.show("No conectado a Home Assistant", "error")
            return
        self._ha_client.set_volume(device.get("entity_id", ""), volume / 100.0)

    def _on_home_audio_group_selected(self, group: dict):
        gid = group.get("id", "")
        if hasattr(self, '_group_mgr'):
            self._group_mgr.activate_group(gid)
            name = group.get("name", gid)
            self._ctx.player_bar.set_transmit_active(True, name)
            self._toast_svc.show(f"Zona activada: {name}", "success")
            self._refresh_home_audio_state()

    def _on_home_audio_create_group(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Crear grupo", "Nombre del grupo o zona:")
        if ok and name.strip() and hasattr(self, '_group_mgr'):
            self._group_mgr.add_group(name.strip())
            self._toast_svc.show(f"Grupo creado: {name.strip()}", "success")
            self._refresh_home_audio_state()

    # ── Snapcast handlers ──

    def _on_snapserver_started(self):
        self._toast_svc.show("Snapserver iniciado", "success")
        self._snap_discovery.refresh()
        self._refresh_home_audio_state()

    def _on_snapserver_stopped(self):
        self._toast_svc.show("Snapserver detenido", "info")
        self._refresh_home_audio_state()

    def _on_snapserver_error(self, msg: str):
        self._toast_svc.show(f"Snapcast: {msg}", "error")

    def _on_audio_sink_ready(self, monitor: str):
        self._snapserver.configure(
            tcp=self._snapserver.tcp_port,
            ctrl=self._snapserver.control_port,
            http=self._snapserver.http_port)
        self._snapserver.start()

    def _on_snap_clients_found(self, clients: list):
        self._refresh_home_audio_state()

    def _on_groups_changed(self, groups: list):
        self._refresh_home_audio_state()

    def _refresh_home_audio_state(self):
        snap_clients = self._snap_discovery.clients() if hasattr(
            self, '_snap_discovery') else []
        snap_devices = [
            {"id": c["id"], "name": c.get("name", c.get("host", "")),
             "entity_id": c.get("id", ""), "state": "idle",
             "area": "", "device_type": "snapclient",
             "backend": c.get("backend", "snapcast"),
             "available": c.get("available", True)}
            for c in snap_clients]

        ha_devices = self._home_audio_view._devices if hasattr(
            self, '_home_audio_view') else []
        all_devices = ha_devices + snap_devices

        groups = self._group_mgr.groups() if hasattr(
            self, '_group_mgr') else []

        api_running = self._michi_api.is_running if hasattr(
            self, '_michi_api') else False
        mdns_running = self._mdns.is_running if hasattr(
            self, '_mdns') else False
        snap_running = self._snapserver.is_running if hasattr(
            self, '_snapserver') else False
        local_media_running = self._local_media.is_running if hasattr(
            self, '_local_media') else False

        tx_active = False
        tx_name = ""
        if hasattr(self, '_ctx') and hasattr(self._ctx, 'transmit_mgr'):
            tx_dev = self._ctx.transmit_mgr.get_active()
            if tx_dev:
                tx_active = True
                tx_name = tx_dev.name

        self._home_audio_view.set_data(
            ha_connected=getattr(self, '_ha_connected', False),
            multiroom_active=snap_running,
            snapserver_running=snap_running,
            devices=all_devices,
            groups=groups,
            transmit_active=tx_active,
            transmit_device_name=tx_name,
            snap_ctrl_port=self._snapserver.control_port if hasattr(self, '_snapserver') else 1705,
            api_running=api_running,
            mdns_running=mdns_running,
            local_media_running=local_media_running)

        self._home_audio_view.set_diagnostics({
            "Home Assistant": "Conectado" if getattr(self, '_ha_connected', False) else "No conectado",
            "API Michi": "Activa" if api_running else "No activa",
            "mDNS": "Activo" if mdns_running else (
                "No disponible" if not (hasattr(self, '_mdns') and self._mdns.is_available) else "No activo"),
            "Snapserver": "Activo" if snap_running else "Detenido",
            "Servidor local": "Activo" if local_media_running else "No activo",
            "Ultimo error": (getattr(self._snapserver, 'last_error', "") or "—")[:40] if hasattr(self, '_snapserver') else "—",
            "IP local": getattr(self, '_local_ip', "—"),
            "Firewall": "Acepta tráfico local" if (api_running or local_media_running or mdns_running) else "—",
        })

    # ── Identifier ──

    def _toggle_identifier(self, enabled: bool):
        self._identifier_ctrl.enabled = enabled
        self._identifier_view.set_identifier_enabled(enabled)
        if not enabled:
            self._identifier_ctrl.stop()

    def _clear_detected_tracks(self):
        self._db.clear_detected_tracks()
        self._identifier_view.set_detected_tracks([])

    def _on_track_detected(self, track):
        self._identifier_view.set_detected_tracks(
            self._db.get_detected_tracks(100))

    def _on_detection_failed(self, message: str):
        self._identifier_view.set_status_message(message)

    def _on_detected_track_selected(self, track: dict):
        filepath = track.get("filepath")
        if filepath and os.path.exists(filepath):
            self._play_file(filepath)
        else:
            title = track.get("title", "")
            artist = track.get("artist", "")
            if title or artist:
                self._search.setText(f"{title} {artist}")
                self._search_ctrl.set_active("local")
                self._search_ctrl.search(f"{title} {artist}")

    def _on_identifier_settings(self):
        self._show_preferences("identifier")

    def _on_identifier_play(self, track: dict):
        fp = track.get("matched_filepath") or track.get("filepath", "")
        if fp and os.path.isfile(fp):
            self._play_file(fp)
        else:
            self._toast_svc.show("Archivo no encontrado en biblioteca", "info")

    def _on_identifier_search(self, track: dict):
        title = track.get("title", "")
        artist = track.get("artist", "")
        if title or artist:
            self._search.setText(f"{title} {artist}")
            self._search_ctrl.set_active("local")
            self._search_ctrl.search(f"{title} {artist}")

    def _on_identifier_delete(self, track: dict):
        idx = track.get("id", 0)
        if hasattr(self._db, 'delete_detected_track'):
            self._db.delete_detected_track(idx)
            self._identifier_view.set_detected_tracks(
                self._db.get_detected_tracks(100))

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
        # Save queue state before shutdown
        try:
            engine = self._playback.engine
            if engine._queue and self._db:
                self._db.save_queue(engine._queue, engine._queue_index)
        except Exception:
            pass
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
        files = []
        dirs = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                dirs.append(path)
            elif os.path.splitext(path)[1].lower() in AUDIO_EXTS:
                files.append(path)

        if dirs:
            for d in dirs:
                self._scan_path(d)
        if files:
            for fp in files:
                self._db.add_file(fp)
            self._load_library()
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
