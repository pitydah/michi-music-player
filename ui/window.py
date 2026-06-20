"""MainWindow — 2 panels + nowplaying bar with library, EQ, and streaming."""

import os
import random
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QIcon, QPixmap, QColor, QDragEnterEvent, QDropEvent, QPainter, QLinearGradient, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel,
    QFrame, QHBoxLayout, QLineEdit, QPushButton, QToolButton, QListWidget, QComboBox,
    QListWidgetItem, QStackedWidget, QTableView, QHeaderView,
    QAbstractItemView, QFileDialog, QInputDialog, QMessageBox, QMenu, QDialog, QFormLayout,
    QDialogButtonBox, QGraphicsOpacityEffect, QSystemTrayIcon,
)
from PySide6.QtWidgets import QApplication

from ui.sidebar_widget import SidebarWidget
from ui.view_switcher import SegmentedViewSwitcher
from ui.view_controller import ViewController
from ui.sidebar_controller import SidebarController

from ui.icons import get_icon, app_icon
from ui.nowplaying_bar import NowPlayingBar
from audio.player import PlayerEngine, PlaybackState
from audio.audio_chain import get_quality_label
from library.library_db import (
    LibraryDB, DB_PATH, ScannerWorker, MediaItem,
    AUDIO_EXTS, ALL_EXTS, scan_device_music,
)
from ui.folder_browser import FolderBrowserWidget
from ui.loading_overlay import LoadingOverlay
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
from library.artist_grouping import build_artist_groups, ArtistGroup
from ui.expanded_view import ExpandedNowPlaying
from streaming.radio_widget import RadioWidget
from streaming.radio_manager import RadioManager
from ui.music_identifier_view import MusicIdentifierView
from ui.discover_dashboard import DiscoverDashboard
from ui.playlist_hub import PlaylistHubWidget
from ui.metadata_editor import MetadataEditorWidget
from ui.artist_grid import ArtistGridWidget
from ui.artist_detail_view import ArtistDetailView
from recognition.detection_service import DetectionService
from recognition.null_recognizer import NullRecognizer


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
        self._search_ctrl = SearchController(self)
        self._search_ctrl.register("local", LocalSource(self._db))
        self._search_ctrl.register("radio", RadioSource(RadioManager()))
        self._search_ctrl.results_ready.connect(self._on_search_results)
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
        self._fade_anim = None
        self._artist_groups: list[ArtistGroup] = []
        self._current_artist_key: str | None = None
        self._coverflow_cache_key: tuple | None = None

        # ── Music Identifier (must exist before _setup_ui) ──
        self._detection = DetectionService(self._db, NullRecognizer(), self)
        self._identifier_view = MusicIdentifierView()

        self._setup_actions()
        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._load_library()

        self._setup_tray()

        # ── Music Identifier signal connections ──
        self._identifier_view.toggle_requested.connect(self._toggle_identifier)
        self._identifier_view.clear_requested.connect(self._clear_detected_tracks)
        self._identifier_view.track_selected.connect(self._on_detected_track_selected)
        self._detection.status_changed.connect(self._identifier_view.set_identifier_state)
        self._detection.track_detected.connect(self._on_track_detected)
        self._detection.detection_failed.connect(self._on_detection_failed)

        self._mpris = None
        try:
            from adapters.mpris import MPRISAdapter
            self._mpris = MPRISAdapter(self)
            self._mpris.player.set_engine(self._player)
        except Exception:
            import logging
            logging.getLogger("astra").debug("MPRIS integration not available (no dbus)")

        self._transmit_mgr = TransmitManager(self)
        self._transmit_mgr.device_changed.connect(self._on_transmit_devices_changed)
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
        text += "<tr><th style='text-align:left;padding:4px 12px;color:#FF7A00'>Atajo</th>" \
                "<th style='text-align:left;padding:4px 12px;color:#FF7A00'>Acción</th></tr>"
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
        header.setStyleSheet("""
            QFrame#headerBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255,255,255,0.070),
                    stop:0.48 rgba(255,255,255,0.045),
                    stop:1 rgba(255,255,255,0.030)
                );
                border: 1px solid rgba(255,255,255,0.080);
                border-radius: 18px;
            }
        """)
        hl = QHBoxLayout(header); hl.setContentsMargins(14, 10, 14, 10); hl.setSpacing(12)

        # Section icon capsule
        self._section_icon_box = QFrame()
        self._section_icon_box.setObjectName("sectionIconBox")
        self._section_icon_box.setFixedSize(42, 42)
        self._section_icon_box.setStyleSheet("""
            QFrame#sectionIconBox {
                background: rgba(255,255,255,0.060);
                border: 1px solid rgba(255,255,255,0.090);
                border-radius: 13px;
            }
        """)
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
        self._section_title.setStyleSheet("""
            QLabel#sectionTitle {
                color: #FFFFFF;
                font-size: 17px; font-weight: 800;
                background: transparent; border: none;
            }
        """)
        self._section_subtitle = QLabel("Toda tu música local")
        self._section_subtitle.setObjectName("sectionSubtitle")
        self._section_subtitle.setStyleSheet("""
            QLabel#sectionSubtitle {
                color: rgba(255,255,255,0.72);
                font-size: 12px; font-weight: 540;
                background: transparent; border: none;
            }
        """)
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
        self._search.setPlaceholderText("Buscar canciones..."); self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(240); self._search.textChanged.connect(self._on_search)
        self._search.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.060);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 12.5px;
                selection-background-color: rgba(255,255,255,0.18);
                selection-color: #FFFFFF;
            }
            QLineEdit:hover {
                background: rgba(255,255,255,0.080);
                border: 1px solid rgba(255,255,255,0.14);
            }
            QLineEdit:focus {
                background: rgba(255,255,255,0.095);
                border: 1px solid rgba(255,255,255,0.18);
            }
        """)
        self._count = QLabel("0 elementos")
        self._count.setObjectName("countBadge")
        self._count.setStyleSheet("""
            QLabel#countBadge {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.080);
                border-radius: 12px;
                padding: 7px 11px;
                color: rgba(255,255,255,0.78);
                font-size: 11.5px;
                font-weight: 660;
            }
        """)

        # View selector (segmented capsule)
        self._view_switcher = SegmentedViewSwitcher(get_icon)
        self._view_switcher.view_changed.connect(self._on_view_mode_changed)
        self._view_mode = "list"

        self._settings_btn = QToolButton()
        self._settings_btn.setObjectName("settingsButton")
        self._settings_btn.setIcon(QIcon(get_icon("warm_settings")))
        self._settings_btn.setIconSize(QSize(24, 24))
        self._settings_btn.setFixedSize(44, 44)
        self._settings_btn.setToolTip("Configuración y acciones")
        self._settings_btn.setPopupMode(QToolButton.InstantPopup)
        self._settings_btn.setStyleSheet("""
            QToolButton#settingsButton {
                background: rgba(255,255,255,0.065);
                border: 1px solid rgba(255,255,255,0.100);
                border-radius: 14px;
            }
            QToolButton#settingsButton:hover {
                background: rgba(255,255,255,0.095);
                border: 1px solid rgba(255,255,255,0.150);
            }
            QToolButton#settingsButton:pressed {
                background: rgba(255,255,255,0.135);
                border: 1px solid rgba(255,255,255,0.20);
            }
            QToolButton#settingsButton::menu-indicator {
                image: none;
                width: 0px;
            }
        """)

        settings_menu = QMenu(self)
        settings_menu.setStyleSheet("""
            QMenu {
                background: rgba(18,20,28,0.98);
                color: rgba(255,255,255,0.88);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 12px;
                padding: 7px 4px;
            }
            QMenu::item {
                padding: 8px 30px 8px 14px;
                border-radius: 8px;
                font-size: 12.5px;
            }
            QMenu::item:selected {
                background: rgba(255,255,255,0.095);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.08);
                margin: 5px 8px;
            }
        """)
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

        hl.addSpacing(16)
        hl.addWidget(self._view_switcher)

        # Album sort/filter row (shown only for albums section)
        self._album_sort_btn = QToolButton()
        self._album_sort_btn.setText("Ordenar")
        self._album_sort_btn.setToolTip("Ordenar álbumes")
        self._album_sort_btn.setPopupMode(QToolButton.InstantPopup)
        self._album_sort_btn.setFixedHeight(32)
        self._album_sort_btn.setStyleSheet("""
            QToolButton {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                color: rgba(255,255,255,0.78); font-size: 11.5px;
                padding: 0 11px;
            }
            QToolButton:hover {
                background: rgba(255,255,255,0.085);
                border: 1px solid rgba(255,255,255,0.14);
            }
        """)
        self._setup_album_sort_menu()
        self._album_sort_btn.hide()

        self._album_filter_btn = QToolButton()
        self._album_filter_btn.setText("Filtrar")
        self._album_filter_btn.setToolTip("Filtrar álbumes")
        self._album_filter_btn.setPopupMode(QToolButton.InstantPopup)
        self._album_filter_btn.setFixedHeight(32)
        self._album_filter_btn.setStyleSheet("""
            QToolButton {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                color: rgba(255,255,255,0.78); font-size: 11.5px;
                padding: 0 11px;
            }
            QToolButton:hover {
                background: rgba(255,255,255,0.085);
                border: 1px solid rgba(255,255,255,0.14);
            }
        """)
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
        self._table.setStyleSheet("""
            QTableView {
                background: #090B11;
                alternate-background-color: #0E1118;
                color: #FFFFFF;
                gridline-color: rgba(255,255,255,0.05);
                border: none;
                selection-background-color: rgba(255,255,255,0.115);
                selection-color: #FFFFFF;
                outline: 0;
            }
            QTableView::item {
                min-height: 28px;
                padding: 4px 8px;
                border: none;
            }
            QTableView::item:hover {
                background: rgba(255,255,255,0.055);
            }
            QHeaderView {
                background: #10131A;
                border: none;
            }
            QHeaderView::section {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #181C25,
                    stop:1 #10131A
                );
                color: rgba(255,255,255,0.82);
                font-size: 12px;
                font-weight: 650;
                padding: 7px 10px;
                border: none;
                border-right: 1px solid rgba(255,255,255,0.06);
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }
            QHeaderView::section:hover {
                background: rgba(255,255,255,0.08);
                color: #FFFFFF;
            }
            QHeaderView::section:checked {
                background: rgba(255,255,255,0.115);
                color: #FFFFFF;
            }
            QTableCornerButton::section {
                background: #10131A;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.025);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                min-height: 40px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,122,0,0.42);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }
            QScrollBar:horizontal {
                background: rgba(255,255,255,0.025);
                height: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255,255,255,0.18);
                min-width: 40px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(255,122,0,0.42);
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
            }
            QScrollBar::add-page,
            QScrollBar::sub-page {
                background: transparent;
            }
        """)
        self._table.doubleClicked.connect(self._on_table_dbl)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_menu)

        placeholder = QLabel()
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.68); font-size: 16px;"
            "  background: transparent; border: none; padding: 48px; }")
        placeholder.setText(
            "Añade música a tu biblioteca\n"
            "Abre una carpeta o arrastra archivos para comenzar")

        placeholder_albums = QLabel()
        placeholder_albums.setAlignment(Qt.AlignCenter)
        placeholder_albums.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.62); font-size: 15px;"
            "  background: transparent; border: none; padding: 48px; }")
        placeholder_albums.setText(
            "Sin álbumes en la biblioteca\n"
            "Añade carpetas de música para ver carátulas aquí")

        placeholder_expanded = QLabel("")
        placeholder_expanded.setAlignment(Qt.AlignCenter)

        # ── Expanded view (created on demand) ──
        self._expanded = None
        self._coverflow = None
        self._remote_browser = None
        self._remote_placeholder = QWidget()
        self._radio_widget = RadioWidget()
        self._radio_widget.station_selected.connect(self._play_radio)

        self._album_grid = AlbumGridWidget()
        self._album_grid.album_double_clicked.connect(
            lambda fps: self._playback.enqueue(fps, play_now=True))
        self._album_grid.queue_requested.connect(
            lambda fps: self._playback.enqueue(fps, play_now=False))
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
        self._playlist_hub.create_from_album_requested.connect(
            self._on_stub_action)
        self._playlist_hub.create_from_artist_requested.connect(
            self._on_stub_action)
        self._playlist_hub.create_from_genre_requested.connect(
            self._on_stub_action)
        self._playlist_hub.create_from_search_requested.connect(
            self._on_stub_action)

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
        self._artist_detail.back_requested.connect(self._show_artists_overview)
        self._artist_detail.play_all_requested.connect(self._play_artist)
        self._artist_detail.queue_all_requested.connect(self._queue_artist)
        self._artist_detail.play_album_requested.connect(
            lambda fps: self._playback.enqueue(fps, play_now=True))
        self._artist_detail.queue_album_requested.connect(
            lambda fps: self._playback.enqueue(fps, play_now=False))
        self._artist_detail.playlist_artist_requested.connect(self._create_playlist_from_artist)
        self._artist_detail.metadata_artist_requested.connect(self._edit_artist_metadata)
        self._artist_detail.metadata_files_requested.connect(self._open_metadata_for_files)

        self._folder_browser = FolderBrowserWidget()
        self._folder_browser.folder_selected.connect(
            lambda fps: self._playback.enqueue(fps, play_now=True))
        self._folder_browser.queue_requested.connect(
            lambda fps: self._playback.enqueue(fps, play_now=False))
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
        self._views.register("metadata_editor", self._metadata_editor)
        self._views.register("artist_grid", self._artist_grid)
        self._views.register("artist_detail", self._artist_detail)
        self._views.register("folders", self._folder_browser)
        self._views.register("identifier", self._identifier_view)
        self._views.show("empty")

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
        cl = QVBoxLayout(cw); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
        cl.addWidget(header); cl.addWidget(self._content)

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
        layout = QVBoxLayout(cent); layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(0)
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
        pb.cover_clicked.connect(self._show_expanded)
        pb.transmit_clicked.connect(self._show_transmit_menu)
        pb.audio_output_clicked.connect(self._show_audio_output_menu)
        pb.mini_player_clicked.connect(self._open_mini_player)
        pb.cover_loaded.connect(self._apply_adaptive_background)

    def _setup_tray(self):
        tray_pix = QPixmap(get_icon("tray_icon"))
        if not tray_pix.isNull():
            tray_pix = tray_pix.scaled(64, 64, Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation)
        self._tray = QSystemTrayIcon(QIcon(tray_pix), self)
        self._tray.setToolTip("Astra Music Player")
        tray_menu = QMenu()
        tray_menu.addAction("Mostrar", self.show)
        tray_menu.addAction("Reproducir/Pausa", self._playback.toggle)
        tray_menu.addAction("Siguiente", self._playback.play_next)
        tray_menu.addAction("Anterior", self._playback.play_prev)
        tray_menu.addSeparator()
        tray_menu.addAction("Salir", self.close)
        self._tray.setContextMenu(tray_menu)
        self._tray.show()

    def _notify_track(self, title: str, artist: str):
        if hasattr(self, '_tray') and self._tray and self._tray.isVisible():
            self._tray.showMessage(
                "Astra", f"{title} — {artist}",
                QSystemTrayIcon.NoIcon, 3000)

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
            self._player_bar.set_track(
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
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Space"), self, self._playback.toggle)
        QShortcut(QKeySequence("Ctrl+Right"), self, self._playback.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self, self._playback.play_prev)
        QShortcut(QKeySequence("Ctrl+Up"), self,
                  lambda: self._player_bar.volume_changed.emit(
                      min(100, self._player_bar._vol.value() + 5)))
        QShortcut(QKeySequence("Ctrl+Down"), self,
                  lambda: self._player_bar.volume_changed.emit(
                      max(0, self._player_bar._vol.value() - 5)))
        QShortcut(QKeySequence("Ctrl+M"), self,
                  lambda: self._player_bar.volume_changed.emit(0))
        QShortcut(QKeySequence("Ctrl+F"), self,
                  lambda: self._search.setFocus())

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
        shadow.setBlurRadius(18); shadow.setXOffset(3); shadow.setYOffset(0)
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
            refs = [TrackRef(
                uri=i.filepath, title=i.title, artist=i.artist,
                album=i.album, duration=i.duration,
                cover_path=i.filepath, track_number=i.track_number,
                year=i.year, genre=i.genre,
            ) for i in items]
            self._model.populate(refs)
            self._playlist_refs = refs

            # Check for missing files
            missing = sum(1 for r in refs if not os.path.exists(r.uri))
            count_text = f"{len(items)} temas"
            if missing:
                count_text += f" ({missing} no encontrados)"

            self._count.setText(count_text)
            self._views.show("library"); self._table.setModel(self._model)
            self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 260); self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(3, 170); self._table.setColumnWidth(4, 55)
            self._table.setColumnWidth(5, 110); self._table.setColumnWidth(6, 75)
            name = next((p["name"] for p in self._db.get_playlists() if p["id"] == pid), "")
            total_dur = int(sum(r.duration for r in refs))
            h = total_dur // 3600
            m = (total_dur % 3600) // 60
            dur_str = f"{h} h {m} min" if h > 0 else f"{m} min" if m > 0 else ""
            subtitle = f"{len(refs)} canciones"
            if dur_str:
                subtitle += f" · {dur_str}"
            self._section_title.setText(name)
            self._section_subtitle.setText(subtitle)
            self._search.show()

        elif key == "artists":
            self._current_artist_key = None
            self._artist_groups = build_artist_groups(self._all_items)
            self._artist_grid.set_artists(self._artist_groups)
            if self._view_mode not in ("grid", "list"):
                self._view_mode = "grid"
                self._view_switcher.set_view("grid", emit=False)
            self._show_artists_view(self._view_mode)
            self._count.setText(f"{len(self._artist_groups)} artistas")
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
                self._views.show("library"); self._table.setModel(self._model)
                self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 240)
                self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
                self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110)
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
            self._section_title.setText("Radio")
            self._search_ctrl.set_active("radio")
            self._apply_filters()
            self._search.show()

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
                duration=0.0, cover_path=fp,
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
            self._views.show("library"); self._table.setModel(self._model)
            self._search.show()

        elif key == "discover":
            self._section_title.setText("Descubrir")
            self._section_subtitle.setText("Explora y redescubre tu música")
            self._views.show("discover")
            self._search.hide()

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
                        self._views.show("library"); self._table.setModel(self._model)
                        self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 260)
                        self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
                        self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110)
                        self._table.setColumnWidth(6, 75)
                    else:
                        self._views.show("empty")
                elif files:
                    self._playback.enqueue(files, play_now=True)
                    self._show_expanded()
                else:
                    from ui.toast_notification import ToastNotification
                    ToastNotification.warning(
                        "El mix no contiene archivos disponibles", self)

        elif key == "favs":
            self._section_title.setText("Favoritos")
            self._section_subtitle.setText("Canciones marcadas como favoritas")
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
                self._views.show("library"); self._table.setModel(self._model)
                self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 260)
                self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
                self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110)
                self._table.setColumnWidth(6, 75)
            else:
                self._views.show("empty")
            self._search.show()

        elif key == "recent":
            self._section_title.setText("Recientes")
            self._section_subtitle.setText("Reproducidas recientemente")
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
                self._views.show("library"); self._table.setModel(self._model)
                self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 260)
                self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
                self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110)
                self._table.setColumnWidth(6, 75)
            else:
                self._views.show("empty")
            self._search.show()
            self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110)
            self._table.setColumnWidth(6, 75)
            self._search.show()

        elif key == "identifier":
            self._section_title.setText("Identificador")
            self._identifier_view.set_detected_tracks(
                self._db.get_detected_tracks(100))
            self._views.show("identifier")
            self._search.hide()

    def _on_sidebar_menu(self, pos):
        widget = self._sidebar.childAt(pos)
        from ui.sidebar_widget import _Item
        item = None
        while widget:
            if isinstance(widget, _Item):
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
        self._rebuild_sidebar(); self._load_library()

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
            uri=url, title=title, artist=artist, album=album))

    def _play_radio(self, url: str, name: str):
        self._play_trackref(TrackRef(
            uri=url, title=name, artist="Radio"))

    # ── Search ──

    def _on_search(self, text: str):
        self._search_text = text.strip()
        if self._current_section_key == "artists" and not self._current_artist_key:
            query = self._search_text.lower()
            if not query:
                filtered = self._artist_groups
            else:
                filtered = [
                    g for g in self._artist_groups
                    if query in g.display_name.lower()
                    or any(query in a.title.lower() for a in g.albums)
                    or any(query in (t.title or "").lower() for t in g.all_tracks)
                    or any(query in g.lower() for g in g.genres)
                ]
            self._artist_grid.set_artists(filtered)
            self._count.setText(f"{len(filtered)} artistas")
            return
        self._apply_filters()

    def _on_search_results(self, results: list):
        self._model.populate(results)
        n = len(results)
        self._count.setText(f"{n} elementos" if n else "0 elementos")
        if n:
            self._views.show("library")
            self._table.setModel(self._model)
            self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 260); self._table.setColumnWidth(3, 170)
            self._table.setColumnWidth(3, 170); self._table.setColumnWidth(4, 55)
            self._table.setColumnWidth(5, 110); self._table.setColumnWidth(6, 75)
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
                cover_path=tracks[0].filepath if tracks else "",
            ))
        self._model.populate(refs)
        self._table.setModel(self._model)
        self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 240)
        self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
        self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110); self._table.setColumnWidth(6, 75)
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
        icon_path = get_icon(icon_name)
        if icon_path:
            pix = QPixmap(icon_path)
            if not pix.isNull():
                self._section_icon.setPixmap(
                    pix.scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self._section_icon.clear()

        # Search placeholder contextual
        searchers = {
            "library": "Buscar canciones...", "albums": "Buscar álbumes...",
            "artists": "Buscar artistas...", "playlists": "Buscar en playlist...",
            "folders": "Buscar carpeta...", "radio": "Buscar emisoras...",
            "playlist_hub": "Buscar playlist...",
        }
        self._search.setPlaceholderText(searchers.get(section_key, "Buscar..."))
        self._search.setVisible(search)

        self._view_switcher.set_available_modes(views, default)

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
        if self._views.current() == target:
            return

        # Stop any running animation
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        # Always restore full opacity before changing view
        self._restore_central_opacity()

        self._views.show(target)

        # Subtle fade-in: 0.88 → 1.0, 100ms (barely visible, won't look broken if skipped)
        effect = QGraphicsOpacityEffect(self._content)
        effect.setOpacity(0.88)
        self._content.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(100)
        anim.setStartValue(0.88)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim = anim

        def _finish():
            effect.setOpacity(1.0)
            self._content.setGraphicsEffect(None)
            self._fade_anim = None

        anim.finished.connect(_finish)
        anim.start()

    def _restore_central_opacity(self):
        """Force full opacity on the central content stack and all child views."""
        # Stop any running fade
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        # Restore content stack
        for w in [self._content, self._album_grid, self._song_grid,
                  self._folder_browser, self._radio_widget,
                  self._playlist_hub, self._metadata_editor,
                  self._discover, self._identifier_view]:
            if w is None:
                continue
            try:
                eff = w.graphicsEffect()
                if isinstance(eff, QGraphicsOpacityEffect):
                    eff.setOpacity(1.0)
                    w.setGraphicsEffect(None)
                w.setEnabled(True)
            except Exception:
                import logging
                logging.getLogger("astra").debug("Opacity restore failed on a child widget")

        # Also check the QStackedWidget itself
        try:
            cw = self._content.parentWidget()
            if cw:
                eff = cw.graphicsEffect()
                if isinstance(eff, QGraphicsOpacityEffect):
                    eff.setOpacity(1.0)
                    cw.setGraphicsEffect(None)
                cw.setEnabled(True)
        except Exception:
            import logging
            logging.getLogger("astra").debug("Central opacity restore failed")

        # Debug if ASTRA_UI_DEBUG=1
        if os.getenv("ASTRA_UI_DEBUG") == "1":
            self._debug_central_visual_state()

    def _debug_central_visual_state(self):
        widgets = [
            ("content_stack", self._content),
            ("album_grid", self._album_grid),
            ("song_grid", self._song_grid),
            ("folder_browser", self._folder_browser),
            ("radio_widget", getattr(self, '_radio_widget', None)),
            ("playlist_hub", getattr(self, '_playlist_hub', None)),
            ("metadata_editor", getattr(self, '_metadata_editor', None)),
            ("discover", getattr(self, '_discover', None)),
        ]
        for name, w in widgets:
            if w is None:
                continue
            eff = w.graphicsEffect()
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            opacity = eff.opacity() if isinstance(eff, QGraphicsOpacityEffect) else None
            print(
                f"[ASTRA UI DEBUG] {name}: "
                f"enabled={w.isEnabled()} "
                f"visible={w.isVisible()} "
                f"effect={type(eff).__name__ if eff else 'None'} "
                f"opacity={opacity}"
            )

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
            self._coverflow.play_album_requested.connect(self._on_coverflow_play_album)
            self._coverflow.queue_album_requested.connect(self._on_coverflow_queue_album)
            self._coverflow.playlist_album_requested.connect(self._on_coverflow_playlist_album)
            self._coverflow.metadata_album_requested.connect(self._on_coverflow_metadata_album)
            self._coverflow.details_album_requested.connect(self._on_coverflow_details_album)
            self._coverflow.cover_search_requested.connect(self._on_coverflow_search_cover)
            self._coverflow.open_folder_requested.connect(self._on_coverflow_open_folder)
            self._views.replace("coverflow", self._coverflow)

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
            self._playback.enqueue(filepaths, play_now=True)
            self._show_expanded()

    def _on_coverflow_snap(self, index: int):
        if not self._coverflow or index >= len(self._coverflow._items):
            return
        item = self._coverflow._items[index]
        if item and item.pixmap and not item.pixmap.isNull():
            self._apply_adaptive_background(item.pixmap)

    def _coverflow_album_tracks(self, idx: int) -> list:
        item = self._coverflow.item_at(idx) if self._coverflow else None
        if not item:
            return []
        return item.data.get("tracks", [])

    def _on_coverflow_play_album(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._playback.enqueue(fps, play_now=True)

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
        self._toast.show(f"Playlist creada: {album_name}", "success")

    def _on_coverflow_metadata_album(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._open_metadata_for_files(fps)

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
            self._toast.show(f"Buscar carátula en: {d}", "info")

    def _on_coverflow_open_folder(self, idx: int):
        tracks = self._coverflow_album_tracks(idx)
        if tracks:
            d = os.path.dirname(tracks[0].filepath)
            import subprocess
            subprocess.Popen(["xdg-open", d])

    # TODO(astra): extract to ui/album_controller.py — album grid + detail actions

    def _on_album_create_playlist(self, fps: list):
        tracks = self._playback.to_trackrefs(fps) or fps
        self._playback.enqueue(tracks, play_now=False)
        self._toast.show("Álbum añadido a la cola", "success")

    def _on_album_search_cover(self, group):
        tracks = group.data.get("tracks", []) if group.data else []
        if tracks:
            d = os.path.dirname(tracks[0].filepath)
            from library.album_art import fetch_cover_online, cache_cover
            try:
                album_name = group.title
                artist = getattr(tracks[0], 'artist', '') or ''
                fetched = fetch_cover_online(album_name, artist)
                if fetched:
                    # Save to cover path
                    cover_path = os.path.join(d, "cover.jpg")
                    fetched.save(cover_path)
                    cache_cover(cover_path, None, "large")
                    self._toast.show("Carátula descargada", "success")
                    self._show_album_grid()
                else:
                    self._toast.show("No se encontró carátula", "warning")
            except Exception as e:
                self._toast.show(f"Error al buscar carátula: {e}", "error")

    def _on_album_open_folder(self, folder: str):
        import subprocess
        subprocess.Popen(["xdg-open", folder])

    def _on_album_show_details(self, group):
        tracks = group.data.get("tracks", []) if group.data else []
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = f"{dur//60}:{int(dur%60):02d}" if dur > 0 else "—"
        exts = set(
            (getattr(t, 'ext', '') or '').upper().lstrip(".")
            for t in tracks if getattr(t, 'ext', ''))
        fmt_str = ", ".join(sorted(exts)) or "—"
        msg = (
            f"Álbum: {group.title}\n"
            f"Artista: {group.subtitle or '—'}\n"
            f"Canciones: {count}\n"
            f"Duración: {dur_str}\n"
            f"Formato: {fmt_str}"
        )
        QMessageBox.information(self, "Detalles del álbum", msg)

    # TODO(astra): extract to ui/playlist_controller.py — Hub + import/export

    def _import_m3u(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar M3U", "", "Playlist M3U (*.m3u *.m3u8);;Todos (*.*)")
        if path:
            self._toast.show(f"Importador M3U pendiente de implementar: {os.path.basename(path)}", "info")

    def _export_playlists(self):
        self._toast.show("Exportador de playlists pendiente de implementar", "info")

    def _open_smart_playlist(self, key: str):
        self._on_sidebar_navigate(f"mix_{key}" if not key.startswith("mix_") else key)

    def _on_hub_playlist_play(self, pid: int):
        items = self._db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._playback.enqueue(fps, play_now=True)
        self._toast.show("Reproduciendo playlist", "success")

    def _on_hub_playlist_queue(self, pid: int):
        items = self._db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._playback.enqueue(fps, play_now=False)
        self._toast.show("Playlist añadida a la cola", "success")

    def _on_hub_create_from_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta musical")
        if folder:
            self._toast.show(f"Crear playlist desde carpeta pendiente: {folder}", "info")

    def _on_hub_create_from_queue(self):
        self._toast.show("Crear playlist desde cola pendiente de implementar", "info")

    def _on_stub_action(self):
        self._toast.show("Acción pendiente de implementar", "info")

    def _on_metadata_saved(self, filepaths: list):
        self._toast.show(f"Metadatos guardados en {len(filepaths)} archivos", "success")

    def _refresh_library(self):
        self._load_library()

    # TODO(astra): extract to ui/artist_controller.py — grid + detail logic

    def _show_artists_view(self, mode: str):
        self._artist_grid.set_view_mode(mode)
        self._fade_content("artist_grid")

    def _open_artist_detail(self, artist_key: str):
        group = next((g for g in self._artist_groups if g.key == artist_key), None)
        if not group:
            return
        self._current_artist_key = artist_key
        self._artist_detail.set_artist(group)

        self._section_title.setText(group.display_name)
        parts = [f"{group.album_count} álbumes", f"{group.track_count} canciones"]
        if group.total_duration:
            s = int(group.total_duration)
            parts.append(f"{s // 3600} h {(s % 3600) // 60} min" if s >= 3600 else f"{s // 60} min")
        self._section_subtitle.setText(" · ".join(parts))
        self._view_switcher.set_available_modes([])
        self._fade_content("artist_detail")

    def _show_artists_overview(self):
        self._current_artist_key = None
        self._configure_header_for_section("artists")
        self._show_artists_view(self._view_mode)

    def _artist_filepaths(self, artist_key: str) -> list[str]:
        group = next((g for g in self._artist_groups if g.key == artist_key), None)
        if not group:
            return []
        return [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]

    def _play_artist(self, artist_key: str):
        fps = self._artist_filepaths(artist_key)
        if fps:
            self._playback.enqueue(fps, play_now=True)

    def _queue_artist(self, artist_key: str):
        fps = self._artist_filepaths(artist_key)
        if fps:
            self._playback.enqueue(fps, play_now=False)

    def _create_playlist_from_artist(self, artist_key: str):
        group = next((g for g in self._artist_groups if g.key == artist_key), None)
        if not group:
            return
        pid = self._db.create_playlist(group.display_name)
        for fp in [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]:
            self._db.add_to_playlist(pid, fp)
        self._rebuild_sidebar()
        self._toast.show(f"Playlist creada: {group.display_name}", "success")

    def _edit_artist_metadata(self, artist_key: str):
        fps = self._artist_filepaths(artist_key)
        if fps:
            self._open_metadata_for_files(fps)

    def _open_metadata_for_files(self, filepaths: list[str]):
        self._metadata_editor.load_files(filepaths)
        self._configure_header_for_section("metadata_editor")
        self._fade_content("metadata_editor")

    # TODO(astra): extract to ui/expanded_controller.py — now playing expanded

    def _show_expanded(self):
        if not self._playback.current:
            return

        if self._expanded is None:
            self._expanded = ExpandedNowPlaying()
            self._expanded.go_back.connect(self._on_expanded_back)
            self._expanded.play_clicked.connect(self._playback.toggle)
            self._expanded.prev_clicked.connect(self._on_expanded_prev)
            self._expanded.next_clicked.connect(self._on_expanded_next)
            self._expanded.seek_requested.connect(self._playback.seek)
            self._expanded.volume_changed.connect(self._playback.set_volume)
            self._expanded.track_from_queue.connect(self._on_queue_track)
            self._expanded.queue_reordered.connect(self._playback.reorder_queue)

            # Sync position/duration
            self._player.position_changed.connect(self._expanded.set_position)
            self._player.duration_changed.connect(self._expanded.set_duration)
            self._player.state_changed.connect(
                lambda s: self._expanded.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

            self._views.replace("expanded", self._expanded)

        # Update track info — prioritize _current_ref, fallback to _all_items
        current = self._playback.current
        name = os.path.basename(current) if current else ""
        qual, _ = get_quality_label(current) if current else ("", "")
        artist = ""
        album = ""
        dur = 0.0
        cover_path = ""

        if self._current_ref and self._current_ref.uri == current:
            ref = self._current_ref
            name = ref.title or name
            artist = ref.artist
            album = ref.album
            dur = ref.duration
            cover_path = ref.cover_path
            title = ref.title or name
        else:
            title = name
            item = self._items_index.get(current)
            if item:
                artist = item.artist
                album = item.album
                dur = item.duration
                title = item.title or name

        if not cover_path:
            from library.album_art import find_cover_in_dir
            cover = find_cover_in_dir(os.path.dirname(current))
            if cover:
                cover_path = cover

        self._expanded.set_track(title, artist, album, qual, cover_path)
        self._expanded.load_lyrics(title, artist, album, dur)

        self._expanded.set_state(
            "playing" if self._playback.state == PlaybackState.PLAYING else "paused")
        self._expanded.set_queue(self._playback.get_queue())
        self._section_title.setText("Reproduciendo")

        self._views.show("expanded")

    def _on_expanded_back(self):
        self._views.show("library")
        self._section_title.setText("Biblioteca")

    def _on_expanded_prev(self):
        self._playback.play_prev()
        self._show_expanded()

    def _on_expanded_next(self):
        self._playback.play_next()
        self._show_expanded()

    def _on_queue_track(self, filepath: str):
        self._playback.play(filepath)
        self._show_expanded()

    # TODO(astra): extract to core/file_actions.py — open/scan/drop logic

    def _open_file(self):
        exts = " ".join(f"*{e}" for e in sorted(ALL_EXTS))
        fp, _ = QFileDialog.getOpenFileName(
            self, "Abrir archivo", os.path.expanduser("~"),
            f"Multimedia ({exts});;Todos (*)")
        if fp:
            self._db.add_file(fp)
            self._load_library()
            self._play_file(fp)

    def _add_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Añadir carpeta", os.path.expanduser("~"))
        if not path:
            return
        self._scan_path(path)

    def _on_folder_create_playlist(self, name: str, filepaths: list):
        pid = self._db.create_playlist(name)
        if pid:
            for fp in filepaths:
                self._db.add_playlist_item(pid, fp)
            self._rebuild_sidebar()
            from ui.toast_notification import ToastNotification
            ToastNotification.success(
                f"Playlist \"{name}\" creada con {len(filepaths)} canciones", self)

    def _scan_path(self, path: str):
        from PySide6.QtCore import QThread
        worker = ScannerWorker(self._db, path)
        thread = QThread()

        overlay = LoadingOverlay(self._content)
        overlay.set_text("Escaneando...")
        overlay.show(delay_ms=100)

        worker.progress.connect(
            lambda c, t, f: overlay.set_text(
                f"Escaneando [{c}/{t}]\n{os.path.basename(f)[:60]}"))

        def _on_done(added):
            overlay.hide()
            overlay.deleteLater()
            self._load_library()
            from ui.toast_notification import ToastNotification
            ToastNotification.success(
                f"Escaneo completado: {added} archivos añadidos", self)

        worker.moveToThread(thread)
        worker.finished.connect(lambda a: _on_done(a))
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_scan_done(self, added, progress, thread):
        progress.close()
        self._load_library()

    # TODO(astra): extract to core/playback_controller.py — play/pause/queue logic

    def _on_table_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        fp = self._model.index(idx.row(), TrackRefTableModel.COL_URI)
        fp = self._model.data(fp, Qt.DisplayRole)
        if not fp:
            return
        is_remote = fp.startswith("http://") or fp.startswith("https://")
        menu = QMenu(self)
        menu.addAction("Reproducir", lambda: self._play_file(fp))
        menu.addAction("Añadir a cola", lambda: self._playback.enqueue([fp], play_now=False))
        menu.addSeparator()
        if is_remote:
            menu.addAction("Copiar URL", lambda: QApplication.clipboard().setText(fp))
        else:
            menu.addAction("Editar metadatos...", lambda: self._edit_tags(fp))
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _edit_tags(self, filepath: str):
        from library.tag_editor import TagEditorDialog
        dlg = TagEditorDialog(filepath, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._db.add_file(filepath)
            self._load_library()

    def _on_table_dbl(self, idx):
        if self._current_section_key == "artists":
            # Show all tracks by this artist
            artist_name = self._model.data(
                self._model.index(idx.row(), TrackRefTableModel.COL_TITLE),
                Qt.DisplayRole)
            if artist_name:
                items = self._db.get_all(search=artist_name)
                refs = [TrackRef(uri=i.filepath,
                                 title=i.title or os.path.basename(i.filepath),
                                 artist=i.artist, album=i.album,
                                 duration=i.duration, year=i.year, genre=i.genre)
                        for i in items]
                self._model.populate(refs)
                self._section_subtitle.setText(f"Todas las canciones de: {artist_name}")
                self._count.setText(f"{len(refs)} canciones")
                self._views.show("library"); self._table.setModel(self._model)
                self._table.setColumnWidth(0, 72); self._table.setColumnWidth(1, 260)
                self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 170)
                self._table.setColumnWidth(4, 55); self._table.setColumnWidth(5, 110)
                self._table.setColumnWidth(6, 75)
            return

        track = self._model.get_trackref(idx.row())
        if track:
            self._play_trackref(track)

    def _play_trackref(self, track: TrackRef):
        self._current_ref = track

        if track.uri.startswith("http"):
            self._playback.play_url(track.uri, track.title, track.artist)
        else:
            self._playback.enqueue([track.uri], play_now=True)

        name = track.title or os.path.basename(track.uri)
        artist = track.artist or ""
        quality_str = ""
        album = track.album or ""

        # Fallback: enrich with MediaItem for local files
        item = self._items_index.get(track.uri)
        if item:
            artist = item.artist or artist
            album = item.album or album
            ext = item.ext.upper().lstrip(".")
            if item.sample_rate:
                quality_str = (
                    f"{ext} · {item.sample_rate/1000:.1f}kHz"
                    if item.sample_rate >= 1000
                    else f"{ext} · {item.sample_rate}Hz")
            elif item.bitrate and item.bitrate >= 1000:
                quality_str = f"{ext} · {item.bitrate//1000}kbps"
            elif item.ext:
                quality_str = ext

        if not quality_str:
            qual, _ = get_quality_label(track.uri)
            quality_str = qual

        self._player_bar.set_track(name, artist)
        self._player_bar.set_quality(quality_str)

        # Cover art
        if track.uri.startswith("http") and track.cover_path:
            pix = QPixmap(track.cover_path)
            if not pix.isNull():
                self._apply_adaptive_background(pix)
        else:
            from library.album_art import find_cover_in_dir
            cover = find_cover_in_dir(os.path.dirname(track.uri))
            if cover:
                pix = QPixmap(cover)
                if not pix.isNull():
                    self._apply_adaptive_background(pix)
                else:
                    self._reset_background()
            else:
                self._reset_background()

        # MPRIS
        if self._mpris:
            dur = int(track.duration)
            if dur <= 0:
                idx_item = self._items_index.get(track.uri)
                if idx_item:
                    dur = int(idx_item.duration)
            self._mpris.player.set_metadata(
                title=name, artist=artist or "",
                album=album, duration=dur)

        self._notify_track(name, artist)
        self.setWindowTitle(f"Astra Music Player — {name}")

    def _play_file(self, filepath: str, add_to_queue: bool = False):
        track = TrackRef(uri=filepath, title=os.path.basename(filepath))
        if filepath.startswith("http"):
            self._play_trackref(track)
        else:
            self._play_trackref(track)

    def _on_state(self, state: PlaybackState):
        s = "playing" if state == PlaybackState.PLAYING else \
            "paused" if state == PlaybackState.PAUSED else "stopped"
        self._player_bar.set_state(s)
        if state == PlaybackState.STOPPED:
            self._player_bar.set_position(0)

    def _on_stop(self):
        self._playback.stop()
        self._player_bar.set_state("stopped"); self._player_bar.set_position(0)
        self._player_bar.set_duration(0)
        self._player_bar.set_track("Sin reproducción", "Añade música a la biblioteca")
        self._reset_background()
        self.setWindowTitle("Astra Music Player")

    def _extract_colors(self, pixmap):
        img = pixmap.toImage().scaled(1, 1, Qt.IgnoreAspectRatio,
                                      Qt.SmoothTransformation)
        avg = img.pixelColor(0, 0)
        return avg.name(), avg.darker(150).name()

    def _apply_adaptive_background(self, pixmap):
        if pixmap is None or pixmap.isNull():
            self._reset_background()
            return
        c1, _ = self._extract_colors(pixmap)
        c1_color = QColor(c1)

        if not hasattr(self, '_last_bg_color'):
            self._last_bg_color = QColor("#1a1a1e")

        anim = QVariantAnimation(self)
        anim.setDuration(800)
        anim.setStartValue(self._last_bg_color)
        anim.setEndValue(c1_color)
        anim.valueChanged.connect(
            lambda v: self._content.setStyleSheet(
                f"QStackedWidget {{"
                f"  background: qlineargradient(y1:0, y2:1, stop:0 {v.name()}, stop:1 {v.name()});"
                f"  border-radius: 12px;"
                f"}}"))
        anim.start()
        self._last_bg_color = c1_color
        # Keep reference to prevent GC
        self._bg_fade_anim = anim

    def _reset_background(self):
        self._content.setStyleSheet(
            "QStackedWidget {"
            "  background: rgba(255,255,255,0.04);"
            "  border-radius: 12px;"
            "}")

    def _open_eq(self):
        from ui.eq_panel import EqDialog
        dlg = EqDialog(self)
        dlg.eq_bands_graphic_changed.connect(
            lambda bands: self._player.set_eq_graphic(bands))
        dlg.eq_bands_parametric_changed.connect(
            lambda bands: self._player.set_eq_parametric(bands))
        dlg.preamp_changed.connect(
            lambda db: self._player.set_eq_preamp(db))
        dlg.eq_bypass_changed.connect(
            lambda bypass: self._player.set_eq_bypass(bypass))
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self._eq_dlg = dlg  # keep reference to prevent GC

    # TODO(astra): extract to ui/transmit_controller.py — streaming + snapcast

    def _show_transmit_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: rgba(28,28,30,230); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 32px 6px 12px; border-radius: 6px; color: rgba(255,255,255,0.8); }
            QMenu::item:selected { background: rgba(255,122,0,0.20); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.06); margin: 3px 8px; }
        """)

        local = menu.addAction("🔊 Local (sin transmitir)")
        local.setCheckable(True)
        active = self._transmit_mgr.get_active()
        local.setChecked(active is None)
        local.triggered.connect(lambda: self._activate_transmit_device(None))

        devices = self._transmit_mgr.get_devices()
        if devices:
            menu.addSeparator()
            for dev in devices:
                action = menu.addAction(f"📡 {dev.name}")
                action.setCheckable(True)
                action.setChecked(active is not None and active.name == dev.name)
                action.triggered.connect(
                    lambda checked, d=dev: self._activate_transmit_device(d))

        menu.addSeparator()
        menu.addAction("Añadir dispositivo...", self._add_transmit_device)
        menu.exec(self._player_bar._transmit_btn.mapToGlobal(
            self._player_bar._transmit_btn.rect().bottomLeft()))

    def _activate_transmit_device(self, device):
        if device is None:
            self._transmit_mgr.set_active(None)
            self._playback.set_output_device(None)
            self._player_bar._transmit_btn.setStyleSheet("")
        else:
            self._transmit_mgr.set_active(device)
            self._playback.set_output_device(device)
            self._player_bar._transmit_btn.setStyleSheet(
                "QPushButton { color: #FF7A00; }")

    def _on_transmit_devices_changed(self):
        pass

    def _on_transmit_active_changed(self):
        device = self._transmit_mgr.get_active()
        if device:
            self._player_bar._transmit_btn.setStyleSheet(
                "QPushButton { color: #FF7A00; }")
            self._player_bar._transmit_btn.setToolTip(
                f"Transmitiendo a: {device.name}")
        else:
            self._player_bar._transmit_btn.setStyleSheet("")
            self._player_bar._transmit_btn.setToolTip("Transmitir a dispositivo")

    def _show_audio_output_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: rgba(28,28,30,230); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 32px 6px 12px; border-radius: 6px; color: rgba(255,255,255,0.8); }
            QMenu::item:selected { background: rgba(255,122,0,0.20); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.06); margin: 3px 8px; }
        """)

        action_system = menu.addAction("Salida predeterminada del sistema")
        action_system.triggered.connect(
            lambda: self._playback.set_output_device(None))

        menu.addSeparator()

        # Detect real audio sinks via GStreamer
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            monitor = Gst.DeviceMonitor()
            monitor.add_filter("Audio/Sink", None)
            monitor.start()
            devices = monitor.get_devices()
            monitor.stop()
            if devices:
                for dev in devices:
                    name = dev.get_display_name() or dev.get_device_class() or "Audio device"
                    action = menu.addAction(name)
                    action.triggered.connect(
                        lambda checked=False, d=dev: self._playback.set_output_device(d))
            else:
                # Fallback: check for pipewire/pulse directly
                pass
        except Exception:
            import logging
            logging.getLogger("astra").debug("Central opacity restore failed")

        menu.addSeparator()
        action_pipewire = menu.addAction("PipeWire (sistema)")
        action_pipewire.triggered.connect(lambda: self._playback.set_output_device(None))
        action_pipewire.setEnabled(True)

        from PySide6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def _open_mini_player(self):
        from ui.mini_player import MiniPlayer
        if not hasattr(self, '_mini_player'):
            self._mini_player = MiniPlayer(self._playback, self)
            self._mini_player.play_clicked.connect(self._playback.toggle)
            self._mini_player.prev_clicked.connect(self._playback.play_prev)
            self._mini_player.next_clicked.connect(self._playback.play_next)
            self._mini_player.seek_requested.connect(self._playback.seek)
            # Sync from engine
            self._player.position_changed.connect(
                lambda s: self._mini_player.set_position(
                    s, getattr(self._player, '_duration', 0)))
            self._player.state_changed.connect(
                lambda s: self._mini_player.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))
        # Update track info
        from audio.audio_chain import get_quality_label
        current = self._playback.current
        name = os.path.basename(current) if current else ""
        artist = ""
        if current:
            qual, _ = get_quality_label(current)
            item = self._items_index.get(current)
            if item:
                artist = item.artist or qual or ""
                title = item.title or name
            else:
                title = name
        else:
            title = "Sin reproducción"
        self._mini_player.set_track(title, artist)
        self._mini_player.show()
        self._mini_player.raise_()
        self._mini_player.activateWindow()

    def _add_transmit_device(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Añadir dispositivo")
        dlg.setMinimumWidth(380)
        from ui.theme import apply_dialog_shadow
        apply_dialog_shadow(dlg)

        layout = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("ej: Altavoz Salón")
        stype = QComboBox()
        stype.addItem("HTTP Stream (servidor TCP)", "http")
        stype.addItem("Snapcast", "snapcast")
        addr = QLineEdit()
        addr.setPlaceholderText("192.168.1.10")
        port = QLineEdit()
        port.setPlaceholderText("8554")

        layout.addRow("Nombre:", name)
        layout.addRow("Tipo:", stype)
        layout.addRow("IP / URL:", addr)
        layout.addRow("Puerto:", port)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted and name.text().strip():
            try:
                port_val = int(port.text()) if port.text().strip() else 0
            except ValueError:
                port_val = 0
            self._transmit_mgr.add_device(
                name.text().strip(), stype.currentData(),
                addr.text().strip(), port_val)

    def _manage_transmit_devices(self):
        devices = self._transmit_mgr.get_devices()
        if not devices:
            QMessageBox.information(self, "Dispositivos",
                                    "No hay dispositivos configurados.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Administrar dispositivos")
        dlg.setMinimumWidth(400)
        from ui.theme import apply_dialog_shadow
        apply_dialog_shadow(dlg)

        layout = QVBoxLayout(dlg)
        lst = QListWidget()
        for dev in devices:
            item = QListWidgetItem(
                f"{dev.name}  ·  {dev.stype.upper()}  ·  "
                f"{dev.address}:{dev.port or '-'}")
            lst.addItem(item)
        layout.addWidget(lst)

        btn_row = QHBoxLayout()

        def _do_delete():
            sel = lst.currentItem()
            if sel:
                name = sel.text().split("  ·  ")[0]
                self._transmit_mgr.remove_device(name)
                dlg.accept()
                self._manage_transmit_devices()

        def _do_activate():
            sel = lst.currentItem()
            if sel:
                name = sel.text().split("  ·  ")[0]
                dev = next((d for d in self._transmit_mgr.get_devices()
                           if d.name == name), None)
                if dev:
                    self._activate_transmit_device(dev)
                    dlg.accept()

        del_btn = QPushButton("Eliminar")
        del_btn.clicked.connect(_do_delete)
        act_btn = QPushButton("Activar")
        act_btn.clicked.connect(_do_activate)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(dlg.accept)

        btn_row.addWidget(act_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dlg.exec()

    # ── Identifier ──

    def _toggle_identifier(self, enabled: bool):
        current = getattr(self._playback, 'current', None)
        source = "stream" if current and current.startswith("http") else "local"
        if enabled:
            self._detection.start(source=source, filepath=current)
            self._identifier_view.set_identifier_enabled(True)
        else:
            self._detection.stop()
            self._identifier_view.set_identifier_enabled(False)

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
            self._playback.enqueue([filepath], play_now=True)
        else:
            title = track.get("title", "")
            artist = track.get("artist", "")
            if title or artist:
                self._search.setText(f"{title} {artist}")
                self._search_ctrl.set_active("local")
                self._search_ctrl.search(f"{title} {artist}")

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
                self._playback.enqueue(files, play_now=True)
