"""MainWindow — 2 panels + nowplaying bar with library, EQ, and streaming."""

import os
import random
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
    table_header_qss,
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
    "genres":     {"title": "Géneros", "subtitle": "Explora por estilo musical",
                   "icon": "sidebar_popular", "views": ["list", "grid"],
                   "search": True, "default": "list"},
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
    "new_playlist": {"title": "Nueva playlist", "subtitle": "Crea una lista personalizada",
                     "icon": "sidebar_add", "views": [],
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Astra Music Player")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)
        self.setAcceptDrops(True)

        icon = app_icon()
        if icon:
            self.setWindowIcon(QIcon(icon))

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
        from core.toast_service import ToastService
        self._toast_svc = ToastService(self)
        self._player_bar_ctrl = None  # initialized after _setup_ui creates _player_bar
        self._current_ref = None
        from ui.controllers.playlist_controller import PlaylistController
        self._playlist_ctrl = PlaylistController(self)
        from core.file_actions import FileActions
        self._file_actions = FileActions(self)
        from ui.controllers.album_controller import AlbumController
        self._album_ctrl = AlbumController(self, refresh_grid=self._show_album_grid)
        from ui.controllers.transmit_controller import TransmitController
        self._transmit_ctrl = TransmitController(self)
        from ui.controllers.audio_output_controller import AudioOutputController
        self._audio_output_ctrl = AudioOutputController(self)
        from ui.controllers.snapcast_controller import SnapcastController
        self._snapcast_ctrl = SnapcastController(self, self)
        from ui.controllers.home_audio_controller import HomeAudioController
        self._ha_ctrl = HomeAudioController(self, self)
        from ui.controllers.cast_controller import CastController
        self._cast_ctrl = CastController(self)
        from ui.controllers.local_media_server_controller import LocalMediaServerController
        self._local_media_ctrl = LocalMediaServerController(self, self)
        from ui.controllers.mini_player_controller import MiniPlayerController
        self._mini_player_ctrl = MiniPlayerController(self, self)
        from ui.controllers.expanded_controller import ExpandedController
        self._expanded_ctrl = ExpandedController(self)
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

        # ── Music Identifier (must exist before _setup_ui) ──
        self._detection = DetectionService(self._db, parent=self)
        self._identifier_view = MusicIdentifierView()
        from recognition.identifier_controller import IdentifierController
        self._identifier_ctrl = IdentifierController(self._db, self._detection, self)

        self._home_audio_view = HomeAudioView()
        self._home_audio_view.connect_requested.connect(self._on_home_audio_connect)
        self._home_audio_view.refresh_requested.connect(self._on_home_audio_refresh)
        self._home_audio_view.enable_multiroom_requested.connect(
            self._on_home_audio_multiroom)
        self._home_audio_view.open_settings_requested.connect(
            self._on_home_audio_settings)
        self._home_audio_view.open_receiver_wizard_requested.connect(
            self._on_home_audio_receiver_wizard)
        self._home_audio_view.device_cast_current_requested.connect(
            self._on_home_audio_cast)
        self._home_audio_view.device_play_requested.connect(
            self._on_home_audio_device_play)
        self._home_audio_view.device_pause_requested.connect(
            self._on_home_audio_device_pause)
        self._home_audio_view.device_stop_requested.connect(
            self._on_home_audio_device_stop)
        self._home_audio_view.device_volume_changed.connect(
            self._on_home_audio_device_volume)
        self._home_audio_view.group_selected_requested.connect(
            self._on_home_audio_group_selected)

        # Snapcast integration
        from integrations.snapcast.snapserver_manager import SnapServerManager
        self._snapserver = SnapServerManager(self)
        self._snapserver.started.connect(self._on_snapserver_started)
        self._snapserver.stopped.connect(self._on_snapserver_stopped)
        self._snapserver.error_occurred.connect(self._on_snapserver_error)

        from integrations.snapcast.audio_capture import AudioCaptureManager
        self._audio_capture = AudioCaptureManager(self)
        self._audio_capture.sink_ready.connect(self._on_audio_sink_ready)
        self._audio_capture.error_occurred.connect(self._on_snapserver_error)

        from integrations.snapcast.discovery import SnapClientDiscovery
        self._snap_discovery = SnapClientDiscovery(self)
        self._snap_discovery.clients_found.connect(self._on_snap_clients_found)

        from integrations.snapcast.group_manager import GroupManager
        self._group_mgr = GroupManager(self)
        self._group_mgr.groups_changed.connect(self._on_groups_changed)

        # Astra API + mDNS
        from integrations.astra_api.http_api import AstraHttpApi
        self._astra_api = AstraHttpApi(self)
        self._astra_api.configure()

        from integrations.astra_api.mdns_advertiser import MDNSAdvertiser
        self._mdns = MDNSAdvertiser(self)
        self._mdns.configure()

        # Local media server for file streaming to HA
        from integrations.home_assistant.local_media_server import (
            LocalMediaServer)
        self._local_media = LocalMediaServer(self)

        # Artist enrichment via TheAudioDB
        from integrations.theaudiodb.artist_enrichment_service import (
            ArtistEnrichmentService)
        from core.settings_manager import get as sget
        self._artist_enrich = ArtistEnrichmentService(self)
        self._artist_enrich.configure(
            api_key=sget("artist_enrichment/api_key") or "2",
            enabled=sget("artist_enrichment/enabled") is not False)

        # Album info repository + enrichment
        from metadata.album_info_repository import AlbumInfoRepository
        self._album_repo = AlbumInfoRepository()

        self._setup_actions()
        self._setup_ui()
        self._connect_signals()

        # AppContext — created after _setup_ui but before shortcuts/controllers use it
        from core.app_context import AppContext
        self._ctx = AppContext(self)

        self._setup_shortcuts()
        self._load_library()

        self._setup_tray()

        # ── Music Identifier signal connections ──
        self._identifier_view.toggle_requested.connect(self._toggle_identifier)
        self._identifier_view.clear_requested.connect(self._clear_detected_tracks)
        self._identifier_view.track_selected.connect(self._on_detected_track_selected)
        self._identifier_view.identify_once_requested.connect(
            lambda: self._identifier_ctrl.identify_once() if hasattr(self, '_identifier_ctrl') else None)
        self._identifier_view.settings_requested.connect(self._on_identifier_settings)
        self._identifier_view.play_track_requested.connect(self._on_identifier_play)
        self._identifier_view.search_track_requested.connect(self._on_identifier_search)
        self._identifier_view.delete_track_requested.connect(self._on_identifier_delete)
        self._detection.track_detected.connect(self._on_track_detected)
        self._detection.detection_failed.connect(self._on_detection_failed)

        self._identifier_ctrl.state_changed.connect(self._identifier_view.set_identifier_state)
        self._identifier_ctrl.source_changed.connect(self._identifier_view.set_source_status)
        self._identifier_ctrl.pause_reason_changed.connect(
            lambda r: self._identifier_view.set_source_status(
                self._identifier_ctrl.current_source_type,
                self._identifier_ctrl.current_source_label, r))
        self._identifier_ctrl.provider_changed.connect(
            self._identifier_view.set_provider_status)

        from ui.controllers.mpris_controller import MPRISController
        self._mpris_ctrl = MPRISController(self)
        self._mpris_ctrl.init()
        self._mpris = self._mpris_ctrl.adapter  # backward compatibility

        self._transmit_mgr = TransmitManager(self)
        self._transmit_mgr.active_changed.connect(self._on_transmit_active_changed)

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
                lambda m: print(f"Sync error: {m}"))
            self._sync_mgr.client_connected.connect(
                lambda d: print(f"Device connected: {d}"))

        if self._sync_mgr.is_active:
            self._sync_mgr.stop()
            self._sync_action.setChecked(False)
        else:
            self._sync_mgr.start()
            self._sync_action.setChecked(True)

    def _show_preferences(self):
        from ui.preferences_window import PreferencesWindow
        dlg = PreferencesWindow(self)
        dlg.exec()

    def _show_shortcuts(self):
        shortcuts = [
            ("Ctrl+O", "Abrir archivo"),
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

    def _show_about(self):
        QMessageBox.about(self, "Acerca de",
            "<h2>Astra Music Player</h2><p>Sincronización Android, ecualizador paramétrico, "
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
        title_wrap.setSpacing(10)
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
        self._remote_placeholder = QWidget()
        self._radio_widget = RadioWidget(self._radio_manager)
        self._radio_widget.station_selected.connect(self._play_radio)
        self._radio_widget.count_changed.connect(self._on_radio_count)

        self._album_grid = AlbumGridWidget()
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

        # Enrichment service signals
        self._artist_enrich.artist_enriched.connect(self._on_artist_enriched)
        self._artist_enrich.artist_image_loaded.connect(self._on_artist_image_loaded)

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
        from ui.controllers.artist_repository import ArtistRepository
        self._artist_repo = ArtistRepository()
        from ui.controllers.artist_controller import ArtistController
        self._artist_ctrl = ArtistController(self)
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
        self._player.error_occurred.connect(lambda m: print(f"Error: {m}"))
        pb.play_clicked.connect(self._playback.toggle)
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
        # Normalize some section keys
        if section_key == "srv":
            section_key = "servers"
        elif section_key == "dev":
            section_key = "devices"
        elif key.startswith("pl:"):
            section_key = "playlists"
        self._configure_header_for_section(section_key)

        if key == "library":
            self._kind_filter = None
            self._search_ctrl.set_active("local")
            self._apply_filters()
            self._view_mode = "list"
            self._view_switcher.set_view("list", emit=False)

        elif key == "playlist_hub":
            pls = self._db.get_playlists()
            self._playlist_hub.set_playlists(pls)
            self._fade_content("playlist_hub")

        elif key == "metadata_editor":
            self._fade_content("metadata_editor")

        elif key and key.startswith("pl:"):
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

        elif key == "artists":
            if not self._all_items and self._db:
                self._load_library()
            self._artist_repo.clear_current()
            self._artist_repo.build(self._all_items)
            self._artist_grid.set_artists(self._artist_repo.groups)
            if hasattr(self, '_artist_enrich'):
                from core.settings_manager import get as sget
                if sget("artist_enrichment/preload_visible") is not False:
                    self._artist_enrich.enrich_visible_artists(
                        self._artist_repo.groups, limit=12)
            if self._view_mode not in ("grid", "list"):
                self._view_mode = "grid"
                self._view_switcher.set_view("grid", emit=False)
            self._show_artists_view(self._view_mode)
            # Force switching to artist_grid in the stacked widget
            self._content.setCurrentWidget(self._artist_grid)
            self._artist_grid.show()
            self._count.setText(f"{self._artist_repo.count} artistas")
            self._search.show()

        elif key == "albums":
            self._section_title.setText("Álbumes")
            # Use default view from SECTION_CONFIG
            self._configure_header_for_section(key)
            self._show_album_grid()
            self._search.show()

        elif key == "genres":
            self._section_title.setText("Géneros")
            self._section_subtitle.setText("Explora por estilo musical")
            items = self._db.get_all(group_by="genre")
            refs = [TrackRef(uri=i.filepath, title=i.genre or "Sin género",
                             duration=i.duration, genre=i.genre or "Sin género")
                    for i in items if i.genre]
            self._model.populate(refs)
            self._count.setText(f"{len(refs)} géneros")
            if refs:
                self._views.show("library")
                self._table.setModel(self._model)
                self._table.setColumnWidth(0, 72)
                self._table.setColumnWidth(1, 240)
                self._table.setColumnWidth(2, 170)
                self._table.setColumnWidth(3, 170)
                self._table.setColumnWidth(4, 55)
                self._table.setColumnWidth(5, 110)
                self._table.setColumnWidth(6, 75)
            else:
                self._views.show("empty")
            self._search.show()

        elif key == "folders":
            self._section_title.setText("Carpetas")
            from sources.folder_source import FolderSource
            self._search_ctrl.register("folders", FolderSource(os.path.expanduser("~")))
            self._search_ctrl.set_active("folders")
            self._views.show("folders")
            self._search.show()

        elif key == "new_playlist":
            self._create_playlist()

        elif key == "radio":
            self._configure_header_for_section(key)
            self._search_ctrl.set_active("radio")
            self._current_section_key = "radio"
            self._radio_widget.reload()
            self._fade_content("radio")

        elif key == "add_server":
            self._add_server()

        elif key and key.startswith("srv:"):
            name = key.split(":", 1)[1]
            self._open_server(name)

        elif key and key.startswith("dev:"):
            mount = key.split(":", 1)[1]
            import shutil
            # Device info
            usage = shutil.disk_usage(mount) if os.path.exists(mount) else None
            files = scan_device_music(mount)
            refs = [TrackRef(
                uri=fp, title=os.path.basename(fp),
            duration=0.0,
        ) for fp in files]
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

        elif key == "discover":
            self._configure_header_for_section(key)
            self._views.show("discover")

        elif key and key.startswith("mix_"):
            from library.smart_mixes import (get_daily_mix, get_unplayed,
                                            get_popular)
            self._section_title.setText({
                "mix_daily": "Mix diario", "mix_unplayed": "No escuchadas",
                "mix_popular": "Más escuchadas",
            }.get(key, "Mix"))
            mixes = {"mix_daily": get_daily_mix, "mix_unplayed": get_unplayed,
                    "mix_popular": get_popular}
            fn = mixes.get(key)
            if fn:
                files = fn()
                files = [f for f in files
                         if isinstance(f, str) and (f.startswith("http") or os.path.isfile(f))]
                if key == "mix_unplayed":
                    # Show table view instead of auto-play
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
                    self._toast_svc.warning(
                        "El mix no contiene archivos disponibles")

        elif key == "favs":
            self._configure_header_for_section(key)
            favs = self._db.get_favorites()
            items = []
            for fp in favs:
                item = self._items_index.get(fp)
                if item:
                    items.append(item)
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

        elif key == "recent":
            self._configure_header_for_section(key)
            history = self._db.get_play_history()
            items = []
            for h in history[:50]:
                fp = h.get("track_id", "")
                item = self._items_index.get(fp)
                if item:
                    items.append(item)
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
            self._table.setColumnWidth(2, 170)
            self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(4, 55)
            self._table.setColumnWidth(5, 110)
            self._table.setColumnWidth(6, 75)
            self._search.show()

        elif key == "identifier":
            self._configure_header_for_section(key)
            self._identifier_view.set_detected_tracks(
                self._db.get_detected_tracks(100))
            self._views.show("identifier")

        elif key == "home_audio":
            self._configure_header_for_section("home_audio")
            self._home_audio_view.refresh_if_needed()
            self._views.show("home_audio")

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

            # Trigger TheAudioDB album enrichment for external metadata
            self._enrich_album_background(key, item, tracks)

            # Trigger artist enrichment for CoverFlow-navigated artist
            if hasattr(self, '_artist_enrich') and item and item.subtitle:
                self._artist_enrich.enrich_artist(item.subtitle)

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
        """Trigger TheAudioDB album enrichment for CoverFlow-navigated albums."""
        if not key or not tracks:
            return
        try:
            from integrations.theaudiodb.album_enrichment_service import AlbumEnrichmentService
            from library.album_key import make_artist_key
            if not hasattr(self, '_album_enrich'):
                self._album_enrich = AlbumEnrichmentService()
                self._album_enrich.album_enriched.connect(self._on_album_enriched)
                # Configure with API key from settings if available
                try:
                    import core.settings_manager as sm
                    api_key = sm.get("integrations/theaudiodb_api_key")
                    if api_key:
                        self._album_enrich._client.api_key = api_key
                except Exception:
                    pass
            album_name = getattr(tracks[0], 'album', '') if tracks else ''
            artist_name = item.subtitle if item and item.subtitle else (
                getattr(tracks[0], 'albumartist', '') or getattr(tracks[0], 'artist', ''))
            if album_name and artist_name:
                artist_key = make_artist_key(artist_name)
                self._album_enrich.enrich_album(key, album_name, artist_key, artist_name)
        except Exception:
            pass

    def _on_album_enriched(self, album_key: str, data: dict):
        """Handle TheAudioDB album enrichment result — update banner if visible."""
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
        # Refresh grid to show new thumb
        if hasattr(self._artist_grid, 'set_artists'):
            repo = self._ctx.artist_repo
            self._artist_grid.set_artists(repo.groups)

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
        dlg.setStyleSheet("QDialog { background: rgba(9,11,17,0.97); border-radius: 18px; }")
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
        self._file_actions.open_file(ALL_EXTS)

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
            lines = diag.to_tooltip().split("\n") if diag else ["Sin diagnostico"]
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

    def _on_home_audio_connect(self):
        from core.settings_manager import get as sget
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox)
        dlg = QDialog(self)
        dlg.setWindowTitle("Conectar Home Assistant")
        dlg.setMinimumWidth(440)
        layout = QFormLayout(dlg)
        layout.setSpacing(10)

        saved_url = sget("home_audio/ha_base_url") or ""
        saved_token = sget("home_audio/ha_token") or ""

        url_edit = QLineEdit(saved_url)
        url_edit.setPlaceholderText("http://homeassistant.local:8123")
        token_edit = QLineEdit(saved_token)
        token_edit.setEchoMode(QLineEdit.Password)
        token_edit.setPlaceholderText("Token de acceso de larga duracion")
        verify_cb = QCheckBox("Verificar SSL")
        verify_cb.setChecked(sget("home_audio/ha_verify_ssl") is not False)
        verify_cb.setStyleSheet("color: rgba(255,255,255,0.72);")

        layout.addRow("URL:", url_edit)
        layout.addRow("Token:", token_edit)
        layout.addRow("", verify_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self._try_ha_connection(
            url_edit.text().strip(), token_edit.text().strip(), dlg))
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        dlg.exec()

    def _try_ha_connection(self, url: str, token: str, dialog):
        from core.settings_manager import get as sget, set_ as sset
        sset("home_audio/ha_base_url", url)
        sset("home_audio/ha_token", token)
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
            url, token, sget("home_audio/ha_verify_ssl"))
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
        if enable:
            # Start Astra API
            if not self._astra_api.is_running:
                self._astra_api.start()
            # Start local media server
            if not self._local_media.is_running:
                self._local_media.configure(8125)
                self._local_media.start()
            # Start mDNS
            if not self._mdns.is_running and self._mdns.is_available:
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
            self._audio_capture.create_sink()
        else:
            self._snapserver.stop()
            self._audio_capture.remove_sink()
            self._mdns.stop()
            self._astra_api.stop()
            self._local_media.stop()

    def _on_home_audio_settings(self):
        from core.settings_manager import get as sget
        self._toast_svc.show(
            "Preferencias Home Audio — "
            f"HA: {sget('home_audio/ha_base_url') or 'no configurado'}",
            "info")

    def _on_home_audio_receiver_wizard(self):
        from integrations.snapcast.receivers import ReceiverWizard
        dlg = ReceiverWizard(self)
        dlg.exec()

    def _stream_local_to_ha(self, filepath: str, entity_id: str, device_name: str):
        if not hasattr(self, '_local_media') or not self._local_media.is_running:
            # Try to auto-start
            if hasattr(self, '_local_media'):
                self._local_media.configure(8125)
                self._local_media.start()
            else:
                self._toast_svc.show(
                    "Servidor local de medios no disponible", "error")
                return
        try:
            url = self._local_media.register_file(filepath)
            self._ha_client.play_media(entity_id, url, "music")
            self._ctx.player_bar.set_transmit_active(True, device_name)
            self._toast_svc.show(
                f"Enviando a {device_name}", "success")
        except ValueError as e:
            self._toast_svc.show(
                f"No se pudo servir el archivo: {e}", "error")

    def _on_home_audio_cast(self, device: dict):
        if not hasattr(self, '_ha_client') or not getattr(self, '_ha_connected', False):
            self._toast_svc.show("No conectado a Home Assistant", "error")
            return
        current = self._playback.current
        if not current:
            self._toast_svc.show("No hay reproduccion activa", "info")
            return
        entity_id = device.get("entity_id", "")
        device_name = device.get("name", "Dispositivo")
        if current.startswith("http"):
            self._ha_client.play_media(entity_id, current, "music")
            self._ctx.player_bar.set_transmit_active(True, device_name)
            self._toast_svc.show(
                f"Enviando a {device_name}", "success")
        else:
            self._stream_local_to_ha(current, entity_id, device_name)

    def _on_home_audio_device_play(self, device: dict):
        if not hasattr(self, '_ha_client'):
            return
        self._ha_client.media_play(device.get("entity_id", ""))

    def _on_home_audio_device_pause(self, device: dict):
        if not hasattr(self, '_ha_client'):
            return
        self._ha_client.media_pause(device.get("entity_id", ""))

    def _on_home_audio_device_stop(self, device: dict):
        if not hasattr(self, '_ha_client'):
            return
        self._ha_client.media_stop(device.get("entity_id", ""))

    def _on_home_audio_device_volume(self, device: dict, volume: int):
        if not hasattr(self, '_ha_client'):
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

        api_running = self._astra_api.is_running if hasattr(
            self, '_astra_api') else False
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
            transmit_device_name=tx_name)

        self._home_audio_view.set_diagnostics({
            "API Astra": "Activa" if api_running else "No activa",
            "mDNS": "Activo" if mdns_running else (
                "No disponible" if not (hasattr(self, '_mdns') and self._mdns.is_available) else "No activo"),
            "Snapserver": "Activo" if snap_running else "Detenido",
            "Servidor local": "Activo" if local_media_running else "No activo",
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
        self._toast_svc.show("Preferencias del identificador: proximamente en ajustes", "info")

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
        try:
            if hasattr(self, '_sync_mgr') and self._sync_mgr.is_active:
                self._sync_mgr.stop()
            engine = self._playback.engine
            if engine._queue and self._db:
                self._db.save_queue(engine._queue, engine._queue_index)
        except Exception:
            import logging
            logging.getLogger("astra").debug("Error saving queue on shutdown")
        self._playback.stop()
        self._db.close()
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
