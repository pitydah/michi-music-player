"""MainWindow — 2 panels + nowplaying bar with library, EQ, and streaming."""

import os
import random
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QIcon, QPixmap, QStandardItemModel, QStandardItem, QBrush, QColor, QDragEnterEvent, QDropEvent, QPainter, QLinearGradient, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel,
    QFrame, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QComboBox,
    QListWidgetItem, QStackedWidget, QTableView, QHeaderView,
    QAbstractItemView, QFileDialog, QProgressDialog,
    QInputDialog, QMessageBox, QMenu, QDialog, QFormLayout,
    QDialogButtonBox, QGraphicsOpacityEffect, QSystemTrayIcon,
)

from ui.sidebar_widget import SidebarWidget
from ui.view_switcher import SegmentedViewSwitcher
from ui.view_controller import ViewController

from ui.icons import get_icon, app_icon
from ui.nowplaying_bar import NowPlayingBar
from audio.player import PlayerEngine, PlaybackState
from audio.audio_chain import DacConfig, get_quality_label
from library.library_db import (
    LibraryDB, DB_PATH, ScannerWorker, MediaItem,
    AUDIO_EXTS, ALL_EXTS, media_kind, get_mounted_devices, scan_device_music,
)
from ui.folder_browser import FolderBrowserWidget

from streaming.transmit_manager import TransmitManager

from streaming.subsonic_client import (
    SubsonicClient, ServerConfig, load_servers, save_servers,
    SubsonicError, AuthError, ServerNotFoundError,
)
from streaming.server_dialog import ServerDialog
from streaming.remote_browser import RemoteBrowser
from library.coverflow import CoverFlowWidget
from library.album_grid import AlbumGridWidget
from library.album_art import load_covers_for_albums
from ui.expanded_view import ExpandedNowPlaying
from streaming.radio_widget import RadioWidget


class MediaTableModel(QStandardItemModel):
    COL_TITLE = 0; COL_ARTIST = 1; COL_ALBUM = 2
    COL_YEAR = 3; COL_GENRE = 4; COL_DURATION = 5; COL_FILEPATH = 6

    def __init__(self, parent=None):
        super().__init__(0, 7, parent)
        self.setHorizontalHeaderLabels(
            ["Título", "Artista", "Álbum", "Año", "Género", "Duración", ""])

    def populate(self, items: list[MediaItem]):
        self.removeRows(0, self.rowCount())
        for item in items:
            t = QStandardItem(item.title or item.filename)
            t.setEditable(False); t.setToolTip(item.filepath)
            a = QStandardItem(item.artist); a.setEditable(False)
            al = QStandardItem(item.album); al.setEditable(False)
            y = QStandardItem(str(item.year) if item.year else ""); y.setEditable(False)
            y.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            y.setForeground(QBrush(QColor("#8e8e93")))
            g = QStandardItem(item.genre); g.setEditable(False)
            d = QStandardItem(item.duration_str); d.setEditable(False)
            d.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            d.setForeground(QBrush(QColor("#8e8e93")))
            fp = QStandardItem(item.filepath); fp.setEditable(False)
            self.appendRow([t, a, al, y, g, d, fp])


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
        self._player.set_volume(70)
        self._player.set_library_db(self._db)
        self._model = MediaTableModel(self)
        self._all_items: list[MediaItem] = []
        self._kind_filter: str | None = None
        self._search_text = ""
        self._current_playlist: int | None = None

        self._setup_menu()
        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._load_library()

        self._setup_tray()

        self._mpris = None
        try:
            from adapters.mpris import MPRISAdapter
            self._mpris = MPRISAdapter(self)
            self._mpris.player.set_engine(self._player)
        except Exception:
            pass

        self._transmit_mgr = TransmitManager(self)
        self._transmit_mgr.device_changed.connect(self._on_transmit_devices_changed)
        self._transmit_mgr.active_changed.connect(self._on_transmit_active_changed)

    def _setup_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("&Archivo")
        fm.addAction("Abrir archivo...", self._open_file, "Ctrl+O")
        fm.addAction("Añadir carpeta...", self._add_folder, "Ctrl+D")
        fm.addSeparator()
        fm.addAction("Importar playlist...", self._import_playlist)
        fm.addAction("Exportar playlist...", self._export_playlist)
        fm.addSeparator()
        self._sync_action = fm.addAction("Activar sincronización Android")
        self._sync_action.setCheckable(True)
        self._sync_action.triggered.connect(self._toggle_sync)
        fm.addSeparator()
        fm.addAction("Salir", self.close, "Ctrl+Q")

        em = mb.addMenu("&Editar")
        em.addAction("Preferencias...", self._show_preferences, "Ctrl+P")

        tm = mb.addMenu("&Transmitir")
        tm.addAction("Añadir dispositivo...", self._add_transmit_device)
        tm.addAction("Administrar dispositivos...", self._manage_transmit_devices)

        hm = mb.addMenu("A&yuda")
        hm.addAction("Acerca de", self._show_about)

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

    def _show_about(self):
        QMessageBox.about(self, "Acerca de",
            "<h2>Astra Music Player</h2><p>Sincronización Android, ecualizador paramétrico, "
            "CoverFlow 3D, streaming Navidrome/Jellyfin.</p>"
            "<p>Python 3 · PySide6 · GStreamer</p>")

    def _setup_ui(self):
        # ── Sidebar ──
        self._sidebar = SidebarWidget()
        self._sidebar.setMinimumWidth(240)
        self._sidebar.setMaximumWidth(270)
        self._sidebar.item_clicked.connect(self._on_sidebar_click)
        self._sidebar.setContextMenuPolicy(Qt.CustomContextMenu)
        self._sidebar.customContextMenuRequested.connect(self._on_sidebar_menu)

        # ── Header ──
        header = QFrame()
        header.setStyleSheet("""
            QFrame { background: rgba(255,255,255,0.03); padding: 8px 16px;
                     border-bottom: 1px solid rgba(255,255,255,0.04); }
        """)
        hl = QHBoxLayout(header); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(10)
        self._section_title = QLabel("Biblioteca")
        self._section_title.setStyleSheet("font-size: 16px; font-weight: bold; color: rgba(255,255,255,0.85);")
        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar..."); self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(200); self._search.textChanged.connect(self._on_search)
        self._count = QLabel("0 elementos")
        self._count.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 12px;")

        # View selector (segmented capsule)
        self._view_switcher = SegmentedViewSwitcher(get_icon)
        self._view_switcher.view_changed.connect(self._on_view_mode_changed)
        self._view_mode = "list"

        self._settings_btn = QPushButton(QIcon(get_icon("warm_settings")), "")
        self._settings_btn.setFlat(True)
        self._settings_btn.setFixedSize(34, 34)
        self._settings_btn.setIconSize(QSize(20, 20))
        self._settings_btn.setToolTip("Preferencias")
        self._settings_btn.clicked.connect(self._show_preferences)

        hl.addWidget(self._section_title)
        hl.addSpacing(16)
        hl.addWidget(self._view_switcher)
        hl.addStretch()
        hl.addWidget(self._search)
        hl.addWidget(self._count)
        hl.addWidget(self._settings_btn)

        # ── Table ──
        self._table = QTableView()
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnHidden(6, True)
        self._table.doubleClicked.connect(self._on_table_dbl)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_menu)

        placeholder = QLabel("Añade una carpeta o abre un archivo")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 16px;")

        placeholder_albums = QLabel("Sin álbumes en la biblioteca")
        placeholder_albums.setAlignment(Qt.AlignCenter)
        placeholder_albums.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 16px;")

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
            lambda fps: self._player.enqueue(fps, play_now=True))

        self._folder_browser = FolderBrowserWidget()
        self._folder_browser.folder_selected.connect(
            lambda fps: self._player.enqueue(fps, play_now=True))

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
        self._views.register("folders", self._folder_browser)
        self._views.show("empty")

        # ── Content wrapper ──
        cw = QWidget()
        cl = QVBoxLayout(cw); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
        cl.addWidget(header); cl.addWidget(self._content)

        # ── Splitter ──
        sidebar_shell = QWidget()
        sidebar_shell.setObjectName("sidebarShell")
        sidebar_shell.setStyleSheet("background: transparent;")
        ss_layout = QVBoxLayout(sidebar_shell)
        ss_layout.setContentsMargins(10, 10, 6, 10)
        ss_layout.setSpacing(0)
        ss_layout.addWidget(self._sidebar)

        sp = QSplitter(Qt.Horizontal)
        sp.addWidget(sidebar_shell)
        sp.addWidget(cw)
        sp.setStretchFactor(0, 1); sp.setStretchFactor(1, 3); sp.setSizes([280, 820])
        sp.setStyleSheet("QSplitter::handle { background: rgba(0,0,0,0.06); width: 1px; }")

        # ── NowPlaying bar ──
        self._player_bar = NowPlayingBar()

        bar_wrapper = QWidget()
        bar_wrapper.setAttribute(Qt.WA_TranslucentBackground)
        wl = QHBoxLayout(bar_wrapper)
        wl.setContentsMargins(24, 0, 24, 12)
        wl.addWidget(self._player_bar)

        cent = QWidget()
        cent.setStyleSheet("background: transparent;")
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
        pb.play_clicked.connect(self._player.toggle)
        pb.shuffle_clicked.connect(self._player.toggle_shuffle)
        pb.repeat_clicked.connect(self._player.toggle_repeat)
        pb.seek_requested.connect(self._player.seek)
        pb.volume_changed.connect(self._player.set_volume)
        pb.eq_clicked.connect(self._open_eq)
        pb.cover_clicked.connect(self._show_expanded)
        pb.transmit_clicked.connect(self._show_transmit_menu)
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
        tray_menu.addAction("Reproducir/Pausa", self._player.toggle)
        tray_menu.addAction("Siguiente", self._player.play_next)
        tray_menu.addAction("Anterior", self._player.play_prev)
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
        if files:
            for fp in files:
                self._db.add_file(fp)
            self._load_library()
            self._player.enqueue(files, play_now=False)
            self._player_bar.set_track(
                f"Importados {len(files)} temas", "Playlist")
        else:
            QMessageBox.information(
                self, "Importar", "No se encontraron archivos válidos.")

    def _export_playlist(self):
        if not self._player._queue:
            QMessageBox.information(
                self, "Exportar", "La cola de reproducción está vacía.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar playlist", "playlist.m3u",
            "M3U (*.m3u);;Todos (*)")
        if not path:
            return
        from ui.playlist_io import export_m3u
        export_m3u(path, self._player._queue)
        QMessageBox.information(
            self, "Exportar", f"Playlist exportada a {path}")

    def _setup_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Space"), self, self._player.toggle)
        QShortcut(QKeySequence("Ctrl+Right"), self, self._player.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self, self._player.play_prev)
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
        QShortcut(QKeySequence("Ctrl+Right"), self, self._player.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self, self._player.play_prev)
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
        self._apply_filters()
        self._rebuild_sidebar()

    def _apply_filters(self):
        items = self._all_items
        if self._kind_filter:
            items = [i for i in items if i.kind == self._kind_filter]
        if self._search_text:
            q = self._search_text.lower()
            items = [i for i in items if q in i.title.lower() or q in i.artist.lower()
                     or q in i.album.lower() or q in i.filename.lower()]
        self._model.populate(items)
        self._count.setText(f"{len(items)} elementos" if items else "0 elementos")
        if items:
            self._views.show("library")
            self._table.setModel(self._model)
            self._table.setColumnWidth(0, 280); self._table.setColumnWidth(1, 170)
            self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 55)
            self._table.setColumnWidth(4, 110); self._table.setColumnWidth(5, 75)
        else:
            self._views.show("empty")

    # ── Sidebar ──

    def _rebuild_sidebar(self):
        self._sidebar._clear()

        # Biblioteca
        self._sidebar.add_section("lib", "Biblioteca", "sidebar_library")
        self._sidebar.add_item("lib", "library", "Todas las canciones",
                               "sidebar_library")
        self._sidebar.add_item("lib", "albums", "Álbumes", "sidebar_albums")
        self._sidebar.add_item("lib", "folders", "Carpetas", "add")

        # Playlists
        self._sidebar.add_section("pl", "Playlist", "sidebar_playlists")
        for p in self._db.get_playlists():
            self._sidebar.add_item("pl", f"pl:{p['id']}", p['name'],
                                   "sidebar_playlist_item")
        self._sidebar.add_item("pl", "new_playlist", "+ Nueva playlist", "add")

        # Smart Mixes
        self._sidebar.add_section("mix", "Descubrir", "sidebar_playlists")
        self._sidebar.add_item("mix", "mix_daily", "Mix diario", "add")
        self._sidebar.add_item("mix", "mix_unplayed", "No escuchadas", "add")
        self._sidebar.add_item("mix", "mix_popular", "Más escuchadas", "add")

        # Radio
        self._sidebar.add_section("rad", "Radio", "sidebar_radio")
        self._sidebar.add_item("rad", "radio", "Emisoras", "sidebar_radio")

        # Servidores
        self._sidebar.add_section("srv", "Servidores", "sidebar_servers")
        for srv in load_servers():
            ico = "sidebar_navidrome" if srv.stype == "navidrome" else "sidebar_jellyfin"
            self._sidebar.add_item("srv", f"srv:{srv.name}", srv.name, ico)
        self._sidebar.add_item("srv", "add_server", "+ Añadir servidor", "add")

        # Dispositivos
        self._sidebar.add_section("dev", "Dispositivos", "sidebar_devices")
        for d in get_mounted_devices():
            self._sidebar.add_item("dev", f"dev:{d['mount']}", d['name'],
                                   "sidebar_devices")

        self._sidebar.set_active("library")

        # Sidebar shadow
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18); shadow.setXOffset(3); shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self._sidebar.setGraphicsEffect(shadow)

    def _on_sidebar_click(self, key: str):
        self._current_playlist = None

        if key == "library":
            self._section_title.setText("Biblioteca")
            self._kind_filter = None
            self._apply_filters()
            self._view_mode = "list"
            self._view_switcher.set_view("list", emit=False)
            self._search.show()

        elif key and key.startswith("pl:"):
            pid = int(key.split(":", 1)[1])
            self._current_playlist = pid
            items = self._db.get_playlist_items(pid)
            self._model.populate(items)
            self._count.setText(f"{len(items)} temas")
            self._views.show("library"); self._table.setModel(self._model)
            self._table.setColumnWidth(0, 280); self._table.setColumnWidth(1, 170)
            self._table.setColumnWidth(2, 170); self._table.setColumnWidth(3, 55)
            self._table.setColumnWidth(4, 110); self._table.setColumnWidth(5, 75)
            name = next((p["name"] for p in self._db.get_playlists() if p["id"] == pid), "")
            self._section_title.setText(f"Playlist · {name}")
            self._search.show()

        elif key == "albums":
            self._section_title.setText("Álbumes")
            self._show_coverflow()
            self._search.show()

        elif key == "folders":
            self._section_title.setText("Carpetas")
            self._views.show("folders")
            self._search.hide()

        elif key == "new_playlist":
            self._create_playlist()

        elif key == "radio":
            self._section_title.setText("📻 Radio")
            self._views.show("radio")
            self._search.hide()

        elif key == "add_server":
            self._add_server()

        elif key and key.startswith("srv:"):
            name = key.split(":", 1)[1]
            self._open_server(name)

        elif key and key.startswith("dev:"):
            mount = key.split(":", 1)[1]
            files = scan_device_music(mount)
            items = []
            for fp in files:
                n = os.path.basename(fp); e = os.path.splitext(fp)[1].lower()
                k = media_kind(e)
                items.append(MediaItem(filepath=fp, filename=n,
                             directory=os.path.dirname(fp), ext=e, kind=k, title=n))
            self._model.populate(items)
            self._count.setText(f"{len(items)} archivos")
            self._views.show("library"); self._table.setModel(self._model)
            self._section_title.setText(os.path.basename(mount))
            self._search.show()

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
                if files:
                    self._player.enqueue(files, play_now=True)
                    self._show_expanded()

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

            if self._content.count() > 2:
                self._content.removeWidget(self._content.widget(2))
            self._content.insertWidget(2, self._remote_browser)
            self._views.show("remote")

            self._remote_browser.load_artists()
            self._section_title.setText(f"🌐 {name}")
            self._search.hide()
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
        self._player.play_url(url, title, artist)
        self._player_bar.set_track(title, f"{artist} · Navidrome")
        self.setWindowTitle(f"Astra Music Player — {title}")

    def _play_radio(self, url: str, name: str):
        self._player.play_url(url, name, "Radio")
        self._player_bar.set_track(name, "📻 Radio")
        self.setWindowTitle(f"Astra Music Player — {name}")

    # ── Search ──

    def _on_search(self, text: str):
        self._search_text = text.strip()
        self._apply_filters()

    # ── CoverFlow ──

    def _on_view_mode_changed(self, mode: str):
        self._view_mode = mode
        if mode == "list":
            self._apply_filters()
            self._section_title.setText("Biblioteca")
            self._fade_content("library")
        elif mode == "grid":
            self._show_album_grid()
            self._section_title.setText("Carátulas")
            self._fade_content("album_grid")
        elif mode == "coverflow":
            self._show_coverflow()
            self._section_title.setText("Coverflow")
            self._fade_content("coverflow")

    def _fade_content(self, target: str):
        if self._views.current() == target:
            return
        self._views.show(target)
        effect = QGraphicsOpacityEffect(self._content)
        self._content.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.3)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: self._content.setGraphicsEffect(None))
        anim.start()

    def _show_list_view(self):
        self._view_switcher.set_view("list", emit=False)
        self._on_view_mode_changed("list")

    def _show_grid_view(self):
        self._view_switcher.set_view("grid", emit=False)
        self._on_view_mode_changed("grid")

    def _show_album_grid(self):
        self._album_grid.set_items(self._all_items, 180)
        self._count.setText(f"{len(self._all_items)} temas")

    def _show_coverflow_view(self):
        self._view_switcher.set_view("coverflow", emit=False)
        self._on_view_mode_changed("coverflow")

    def _show_coverflow(self):
        items = self._all_items
        if self._kind_filter:
            items = [i for i in items if i.kind == self._kind_filter]
        covers = load_covers_for_albums(items, 260, lazy=True)

        if not covers:
            self._views.show("empty")
            self._count.setText("0 álbumes")
            return

        if self._coverflow is None:
            self._coverflow = CoverFlowWidget()
            self._coverflow.double_clicked.connect(self._on_coverflow_dbl)
            self._coverflow.cover_snapped.connect(self._on_coverflow_snap)
            if self._content.count() > 3:
                self._content.removeWidget(self._content.widget(3))
            self._content.insertWidget(3, self._coverflow)

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
            self._player.enqueue(filepaths, play_now=True)
            self._show_expanded()

    def _on_coverflow_snap(self, index: int):
        if not self._coverflow or index >= len(self._coverflow._items):
            return
        item = self._coverflow._items[index]
        if item and item.pixmap and not item.pixmap.isNull():
            self._apply_adaptive_background(item.pixmap)

    # ── Expanded View ──

    def _show_expanded(self):
        if not self._player._current:
            return

        if self._expanded is None:
            self._expanded = ExpandedNowPlaying()
            self._expanded.go_back.connect(self._on_expanded_back)
            self._expanded.play_clicked.connect(self._player.toggle)
            self._expanded.prev_clicked.connect(self._on_expanded_prev)
            self._expanded.next_clicked.connect(self._on_expanded_next)
            self._expanded.seek_requested.connect(self._player.seek)
            self._expanded.volume_changed.connect(self._player.set_volume)
            self._expanded.track_from_queue.connect(self._on_queue_track)
            self._expanded.queue_reordered.connect(self._player.reorder_queue)

            # Sync position/duration
            self._player.position_changed.connect(self._expanded.set_position)
            self._player.duration_changed.connect(self._expanded.set_duration)
            self._player.state_changed.connect(
                lambda s: self._expanded.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

            if self._content.count() > 4:
                self._content.removeWidget(self._content.widget(4))
            self._content.insertWidget(4, self._expanded)

        # Update track info
        current = self._player._current
        name = os.path.basename(current) if current else ""
        from audio.audio_chain import get_quality_label
        qual, _ = get_quality_label(current) if current else ("", "")
        artist = ""
        for i in self._all_items:
            if i.filepath == current:
                artist = i.artist
                album = i.album
                subtitle_parts = []
                if artist: subtitle_parts.append(artist)
                if album: subtitle_parts.append(album)
                if i.year: subtitle_parts.append(str(i.year))
                subtitle = " · ".join(subtitle_parts) if subtitle_parts else ""
                cover_path = ""
                from library.album_art import find_cover_in_dir
                cover = find_cover_in_dir(os.path.dirname(current))
                if cover:
                    cover_path = cover
                self._expanded.set_track(
                    i.title or name, artist, album, qual, cover_path)
                break
        else:
            self._expanded.set_track(name, artist, "", qual, "")

        self._expanded.set_state(
            "playing" if self._player.state == PlaybackState.PLAYING else "paused")
        self._expanded.set_queue(self._player.get_queue())
        self._section_title.setText("Reproduciendo")

        self._views.show("expanded")

    def _on_expanded_back(self):
        self._views.show("library")
        self._section_title.setText("Biblioteca")

    def _on_expanded_prev(self):
        self._player.play_prev()
        self._show_expanded()

    def _on_expanded_next(self):
        self._player.play_next()
        self._show_expanded()

    def _on_queue_track(self, filepath: str):
        self._player.play(filepath)
        self._show_expanded()

    # ── File open / scan ──

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

    def _scan_path(self, path: str):
        from PySide6.QtCore import QThread
        worker = ScannerWorker(self._db, path)
        thread = QThread()
        progress = QProgressDialog("Escaneando...", "Cancelar", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal); progress.setMinimumDuration(300)
        worker.moveToThread(thread)
        worker.progress.connect(
            lambda c, t, f: progress.setLabelText(f"[{c}/{t}] {os.path.basename(f)[:60]}"))
        worker.progress.connect(lambda c, t, f: progress.setValue(int(c / max(t, 1) * 100)))
        worker.finished.connect(lambda a: self._on_scan_done(a, progress, thread))
        progress.canceled.connect(worker.cancel)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit); worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater); thread.start()

    def _on_scan_done(self, added, progress, thread):
        progress.close()
        self._load_library()

    # ── Playback ──

    def _on_table_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        fp = self._model.index(idx.row(), MediaTableModel.COL_FILEPATH)
        fp = self._model.data(fp, Qt.DisplayRole)
        if not fp:
            return
        menu = QMenu(self)
        menu.addAction("Reproducir", lambda: self._play_file(fp))
        menu.addAction("Añadir a cola", lambda: self._player.enqueue([fp], play_now=False))
        menu.addSeparator()
        menu.addAction("Editar metadatos...", lambda: self._edit_tags(fp))
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _edit_tags(self, filepath: str):
        from library.tag_editor import TagEditorDialog
        dlg = TagEditorDialog(filepath, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._db.add_file(filepath)
            self._load_library()

    def _on_table_dbl(self, idx):
        fp = self._model.index(idx.row(), MediaTableModel.COL_FILEPATH)
        fp = self._model.data(fp, Qt.DisplayRole)
        if fp:
            self._play_file(fp)

    def _play_file(self, filepath: str, add_to_queue: bool = False):
        if add_to_queue:
            self._player.enqueue([filepath], play_now=False)
        else:
            self._player.enqueue([filepath], play_now=True)

        name = os.path.basename(filepath)
        qual, _ = get_quality_label(filepath)
        artist = qual or ""
        quality_str = qual
        for item in self._all_items:
            if item.filepath == filepath:
                artist = item.artist or qual or ""
                ext = item.ext.upper().lstrip(".")
                if item.sample_rate:
                    if item.sample_rate >= 1000:
                        quality_str = f"{ext} · {item.sample_rate/1000:.1f}kHz"
                    else:
                        quality_str = f"{ext} · {item.sample_rate}Hz"
                elif item.bitrate and item.bitrate >= 1000:
                    quality_str = f"{ext} · {item.bitrate//1000}kbps"
                else:
                    quality_str = ext
                break
        self._player_bar.set_track(name, artist)
        self._player_bar.set_quality(quality_str)

        from library.album_art import find_cover_in_dir
        cover = find_cover_in_dir(os.path.dirname(filepath))
        if cover:
            from PySide6.QtGui import QPixmap
            pix = QPixmap(cover)
            if not pix.isNull():
                self._apply_adaptive_background(pix)
            else:
                self._reset_background()
        else:
            self._reset_background()

        if self._mpris:
            dur = 0
            album = ""
            cover_path = ""
            for item in self._all_items:
                if item.filepath == filepath:
                    dur = int(item.duration)
                    album = item.album or ""
                    break
            self._mpris.player.set_metadata(
                title=name, artist=artist or "",
                album=album, duration=dur)

        self._notify_track(name, artist)

        self.setWindowTitle(f"Astra Music Player — {name}")

    def _on_state(self, state: PlaybackState):
        s = "playing" if state == PlaybackState.PLAYING else \
            "paused" if state == PlaybackState.PAUSED else "stopped"
        self._player_bar.set_state(s)
        if state == PlaybackState.STOPPED:
            self._player_bar.set_position(0)

    def _on_stop(self):
        self._player.stop()
        self._player_bar.set_state("stopped"); self._player_bar.set_position(0)
        self._player_bar.set_duration(0)
        self._player_bar.set_track("Sin reproducción", "Añade música a la biblioteca")
        self._reset_background()
        self.setWindowTitle("Astra Music Player")

    def _extract_colors(self, pixmap):
        from PySide6.QtGui import QColor
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

    # ── Transmit ──

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
            self._player.set_output_device(None)
            self._player_bar._transmit_btn.setStyleSheet("")
        else:
            self._transmit_mgr.set_active(device)
            self._player.set_output_device(device)
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
        active = self._transmit_mgr.get_active()

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0, QColor(18, 18, 21))
        grad.setColorAt(0.5, QColor(15, 15, 18))
        grad.setColorAt(1, QColor(12, 12, 14))
        painter.fillRect(rect, grad)
        # subtle noise texture
        noise = QImage(rect.width() // 2, rect.height() // 2, QImage.Format_Grayscale8)
        for y in range(noise.height()):
            for x in range(noise.width()):
                noise.setPixel(x, y, random.randint(0, 5))
        painter.setOpacity(0.03)
        painter.drawImage(rect, noise.scaled(rect.size()))

    def closeEvent(self, event):
        try:
            if hasattr(self, '_sync_mgr') and self._sync_mgr.is_active:
                self._sync_mgr.stop()
            if self._player._queue and self._db:
                self._db.save_queue(self._player._queue, self._player._queue_index)
        except Exception:
            pass
        self._player.stop()
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
                self._player.enqueue(files, play_now=True)
