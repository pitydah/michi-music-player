"""UIBuilder — constructs the entire MainWindow widget tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QSplitter, QStackedWidget, QTableView, QToolButton, QVBoxLayout,
    QWidget, QAbstractItemView, QHeaderView,
)

from library.album_grid import AlbumGridWidget
from library.song_grid import SongGridWidget
from streaming.radio_widget import RadioWidget
from ui.central.central_styles import (
    header_qss, section_icon_box_qss, section_title_qss,
    section_subtitle_qss, tool_button_qss, count_badge_qss,
    table_qss, scrollbar_qss, table_header_qss,
    search_qss, menu_qss,
)
from ui.discover_dashboard import DiscoverDashboard
from ui.folder_browser import FolderBrowserWidget
from ui.playlist_hub import PlaylistHubWidget
from ui.playlist_detail_view import PlaylistDetailView
from ui.metadata_editor import MetadataEditorWidget
from ui.artist_grid import ArtistGridWidget
from ui.artist_detail_view import ArtistDetailView
from ui.genre_grid import GenreGridWidget
from ui.genres.genre_hub_page import GenreHubPage
from ui.genres.genre_detail_page import GenreDetailPage
from ui.genres.genre_cleanup_page import GenreCleanupPage
from ui.genre_detail_view import GenreDetailView
from ui.icons import get_icon, get_qicon
from ui.nowplaying_bar import NowPlayingBar
from ui.sidebar_widget import SidebarWidget
from ui.sidebar_controller import SidebarController
from ui.view_controller import ViewController
from ui.view_switcher import SegmentedViewSwitcher

if TYPE_CHECKING:
    from ui.window import MainWindow


def _nav_button_qss() -> str:
    return """
        QToolButton {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
        }
        QToolButton:hover {
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.10);
        }
        QToolButton:pressed {
            background: rgba(255,255,255,0.03);
        }
        QToolButton:disabled {
            background: transparent;
            border: 1px solid transparent;
        }
    """


class UIBuilder:
    """Constructs all widgets, stacks, and layouts for MainWindow.

    Call build() once after core/optional/controller init is complete.
    All widgets are stored directly on the MainWindow instance (self._win).
    """

    def __init__(self, window: MainWindow):
        self._win = window

    def _nav_back(self):
        self._win._nav_ctrl.navigate_back()

    def _nav_forward(self):
        self._win._nav_ctrl.navigate_forward()

    def build(self):
        w = self._win

        # ── Sidebar ──
        w._sidebar = SidebarWidget()
        w._sidebar.setMinimumWidth(270)
        w._sidebar.setMaximumWidth(380)
        w._sidebar_controller = SidebarController(w._sidebar, w._db)
        w._sidebar_controller.navigation_requested.connect(
            lambda key, _w=w: _w._nav_ctrl.dispatch(key))
        w._sidebar.setContextMenuPolicy(Qt.CustomContextMenu)
        w._sidebar.customContextMenuRequested.connect(lambda pos, _w=w: _w._sidebar_menu_ctrl.show_context_menu(pos))

        # ── Header ──
        header = QFrame()
        header.setObjectName("headerBar")
        header.setStyleSheet(header_qss())
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 8, 16, 8)
        hl.setSpacing(10)

        # Section icon capsule
        w._section_icon_box = QFrame()
        w._section_icon_box.setObjectName("sectionIconBox")
        w._section_icon_box.setFixedSize(40, 40)
        w._section_icon_box.setStyleSheet(section_icon_box_qss())
        icon_box_inner = QVBoxLayout(w._section_icon_box)
        icon_box_inner.setContentsMargins(0, 0, 0, 0)
        icon_box_inner.setAlignment(Qt.AlignCenter)

        w._section_icon = QLabel()
        w._section_icon.setFixedSize(24, 24)
        w._section_icon.setAlignment(Qt.AlignCenter)
        w._section_icon.setStyleSheet("background: transparent; border: none;")
        icon_box_inner.addWidget(w._section_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        w._section_title = QLabel("Todas las canciones")
        w._section_title.setObjectName("sectionTitle")
        w._section_title.setStyleSheet(section_title_qss())
        w._section_subtitle = QLabel("Toda tu música local")
        w._section_subtitle.setObjectName("sectionSubtitle")
        w._section_subtitle.setStyleSheet(section_subtitle_qss())
        title_box.addWidget(w._section_title)
        title_box.addWidget(w._section_subtitle)

        title_wrap = QHBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(6)

        w._back_btn = QToolButton()
        w._back_btn.setObjectName("navBackBtn")
        w._back_btn.setIcon(get_qicon("nav_back"))
        w._back_btn.setIconSize(QSize(18, 18))
        w._back_btn.setToolTip("Atrás (Alt+Izquierda)")
        w._back_btn.setCursor(Qt.PointingHandCursor)
        w._back_btn.setStyleSheet(_nav_button_qss())
        w._back_btn.setFixedSize(38, 38)
        w._back_btn.setEnabled(False)
        w._back_btn.clicked.connect(self._nav_back)
        title_wrap.addWidget(w._back_btn)

        w._forward_btn = QToolButton()
        w._forward_btn.setObjectName("navForwardBtn")
        w._forward_btn.setIcon(get_qicon("nav_forward"))
        w._forward_btn.setIconSize(QSize(18, 18))
        w._forward_btn.setToolTip("Adelante (Alt+Derecha)")
        w._forward_btn.setCursor(Qt.PointingHandCursor)
        w._forward_btn.setStyleSheet(_nav_button_qss())
        w._forward_btn.setFixedSize(38, 38)
        w._forward_btn.setEnabled(False)
        w._forward_btn.clicked.connect(self._nav_forward)
        title_wrap.addWidget(w._forward_btn)

        title_wrap.addWidget(w._section_icon_box)
        title_wrap.addLayout(title_box)
        hl.addLayout(title_wrap)
        hl.addSpacing(12)

        w._search = QLineEdit()
        w._search.setPlaceholderText("Buscar canciones...")
        w._search.setClearButtonEnabled(True)
        w._search.setMinimumWidth(160)
        w._search.setMaximumWidth(300)
        w._search.textChanged.connect(lambda text, _w=w: _w._search_router.on_search(text))
        w._search.setStyleSheet(search_qss())
        w._count = QLabel("")
        w._count.setObjectName("countBadge")
        w._count.setStyleSheet(count_badge_qss())
        w._count.setVisible(False)

        # View selector (segmented capsule)
        w._view_switcher = SegmentedViewSwitcher(get_icon)
        w._view_switcher.view_changed.connect(lambda mode, _w=w: _w._view_router.on_mode_changed(mode))
        w._view_mode = "list"

        # Responsive: actualizar view switcher al redimensionar el header
        header._orig_resize = header.resizeEvent
        def _header_resize(event, _self=header, _vs=w._view_switcher):
            _self._orig_resize(event)
            _vs.update_for_width(_self.width())
        header.resizeEvent = _header_resize

        w._settings_btn = QToolButton()
        w._settings_btn.setObjectName("settingsButton")
        w._settings_btn.setIcon(get_qicon("warm_settings", size=24))
        w._settings_btn.setIconSize(QSize(24, 24))
        w._settings_btn.setFixedSize(44, 44)
        w._settings_btn.setToolTip("Configuración y acciones")
        w._settings_btn.setPopupMode(QToolButton.InstantPopup)
        w._settings_btn.setStyleSheet(tool_button_qss("icon"))

        settings_menu = QMenu(w)
        settings_menu.setStyleSheet(menu_qss())
        ac = w._action_ctrl
        settings_menu.addAction(ac._open_file_action)
        settings_menu.addAction(ac._add_folder_action)
        settings_menu.addSeparator()
        settings_menu.addAction(ac._import_playlist_action)
        settings_menu.addAction(ac._export_playlist_action)
        settings_menu.addSeparator()
        transmit_sub = settings_menu.addMenu("Transmitir")
        transmit_sub.addAction(ac._add_transmit_device_action)
        transmit_sub.addAction(ac._manage_transmit_devices_action)
        settings_menu.addSeparator()
        settings_menu.addAction(ac._sync_action)
        settings_menu.addSeparator()
        settings_menu.addAction(ac._preferences_action)
        settings_menu.addAction(ac._duplicates_action)
        settings_menu.addSeparator()
        settings_menu.addAction(ac._shortcuts_action)
        settings_menu.addAction(ac._about_action)
        settings_menu.addSeparator()
        settings_menu.addAction(ac._quit_action)
        w._settings_btn.setMenu(settings_menu)

        # Album sort/filter row (shown only for albums section)
        w._album_sort_btn = QToolButton()
        w._album_sort_btn.setText("Ordenar")
        w._album_sort_btn.setToolTip("Ordenar álbumes")
        w._album_sort_btn.setPopupMode(QToolButton.InstantPopup)
        w._album_sort_btn.setFixedHeight(32)
        w._album_sort_btn.setStyleSheet(tool_button_qss())
        w._setup_album_sort_menu()
        w._album_sort_btn.hide()

        w._album_filter_btn = QToolButton()
        w._album_filter_btn.setText("Filtrar")
        w._album_filter_btn.setToolTip("Filtrar álbumes")
        w._album_filter_btn.setPopupMode(QToolButton.InstantPopup)
        w._album_filter_btn.setFixedHeight(32)
        w._album_filter_btn.setStyleSheet(tool_button_qss())
        w._setup_album_filter_menu()
        w._album_filter_btn.hide()

        # Context actions container
        w._context_actions_box = QHBoxLayout()
        w._context_actions_box.setSpacing(6)
        w._context_actions_box.addWidget(w._album_sort_btn)
        w._context_actions_box.addWidget(w._album_filter_btn)

        hl.addStretch()
        hl.addWidget(w._view_switcher)
        hl.addLayout(w._context_actions_box)
        hl.addWidget(w._search)
        hl.addWidget(w._count)
        hl.addWidget(w._settings_btn)

        # ── Table ──
        w._table = QTableView()
        w._table.setShowGrid(False)
        w._table.setAlternatingRowColors(True)
        w._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        w._table.setSelectionMode(QAbstractItemView.SingleSelection)
        w._table.setFrameShape(QFrame.NoFrame)
        w._table.horizontalHeader().setStretchLastSection(True)
        w._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        w._table.horizontalHeader().setSectionsClickable(True)
        w._table.horizontalHeader().setSortIndicatorShown(True)
        w._table.horizontalHeader().setHighlightSections(False)
        w._table.verticalHeader().setVisible(False)
        w._table.verticalHeader().setDefaultSectionSize(30)
        w._table.setSortingEnabled(True)
        w._table.setStyleSheet(table_qss() + scrollbar_qss())
        w._table.horizontalHeader().setStyleSheet(table_header_qss())
        w._table.doubleClicked.connect(lambda idx, _w=w: _w._playback_ctrl.on_table_dbl(idx))
        w._table.setContextMenuPolicy(Qt.CustomContextMenu)
        w._table.customContextMenuRequested.connect(lambda pos, _w=w: _w._playback_ctrl.on_table_menu(pos))

        placeholder = QLabel()
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.82); font-size: 16px; font-weight: 500;"
            "  background: transparent; border: none; padding: 48px 48px 12px 48px; }")
        placeholder.setText(
            "\U0001f3b5  Añade música a tu biblioteca\n\n"
            "Abre una carpeta o arrastra archivos para comenzar")

        placeholder_albums = QLabel()
        placeholder_albums.setAlignment(Qt.AlignCenter)
        placeholder_albums.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.82); font-size: 15px;"
            "  background: transparent; border: none; padding: 48px; }")
        placeholder_albums.setText(
            "\U0001f4c0  Sin álbumes en la biblioteca\n\n"
            "Añade carpetas de música para ver carátulas aquí")

        placeholder_expanded = QLabel("")
        placeholder_expanded.setAlignment(Qt.AlignCenter)

        # ── Expanded view (created on demand) ──
        w._expanded = None
        w._coverflow = None
        w._remote_browser = None
        w._remote_placeholder = QLabel("Conecta a un servidor remoto primero")
        w._remote_placeholder.setAlignment(Qt.AlignCenter)
        w._remote_placeholder.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.62); font-size: 15px; font-weight: 500;"
            "  background: transparent; border: none; }")
        w._radio_widget = RadioWidget(w._radio_manager)
        w._radio_widget.station_selected.connect(lambda url, name, _w=w: _w._srv_ctrl.play_radio(url, name))
        w._radio_widget.count_changed.connect(lambda vis, tot, _w=w: _w._srv_ctrl.on_radio_count(vis, tot))

        w._album_grid = AlbumGridWidget()
        w._album_grid.set_worker_manager(w._workers)
        w._album_grid.queue_requested.connect(
            lambda fps, _w=w: _w._play_filepaths(fps, play_now=False))
        w._album_grid.playlist_requested.connect(
            lambda fps, _w=w: _w._album_ctrl.create_playlist(fps))
        w._album_grid.play_next_requested.connect(
            lambda fps, _w=w: _w._play_filepaths(fps, play_now=False) if w._playback.get_queue() else None)
        w._album_grid.cover_search_requested.connect(
            lambda group, _w=w: _w._album_ctrl.search_cover(group))
        w._album_grid.metadata_requested.connect(
            lambda group, _w=w: _w._album_ctrl.edit_album_metadata(
                group.data.get("tracks", []) if group.data else []))
        w._album_grid.quality_requested.connect(
            lambda group, _w=w: _w._album_ctrl.analyze_album_quality(
                group.data.get("tracks", []) if group.data else []))
        w._album_grid.send_to_server_requested.connect(
            lambda group, _w=w: _w._album_ctrl.send_album_to_server(
                group.data.get("tracks", []) if group.data else []))
        w._album_grid.sync_mobile_requested.connect(
            lambda group, _w=w: _w._album_ctrl.sync_album_to_mobile(
                group.data.get("tracks", []) if group.data else []))
        w._album_grid.duplicate_review_requested.connect(
            lambda group, _w=w: _w._album_ctrl.review_album_duplicates(
                group.data.get("tracks", []) if group.data else []))
        w._album_grid.open_folder_requested.connect(
            lambda folder, _w=w: _w._album_ctrl.open_folder(folder))
        w._album_grid.details_requested.connect(
            lambda group, _w=w: _w._album_ctrl.show_details(group))
        w._album_grid.add_folder_requested.connect(
            lambda: w._library_import.add_folder(w))
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            import contextlib
            with contextlib.suppress(TypeError, RuntimeError):
                w._album_grid.album_selected.disconnect()
        w._album_grid.album_selected.connect(
            lambda group, _w=w: _w._album_ctrl.show_album_detail_from_cover_item(group))

        w._song_grid = SongGridWidget()
        w._song_grid.song_double_clicked.connect(
            lambda fp, _w=w: _w._play_file(fp))
        w._song_grid.song_context_menu.connect(
            lambda fp, pos, _w=w: _w._show_song_context_menu(fp, pos))

        # Generic song grid for external views (playlists, favs, recent)
        w._generic_song_grid = SongGridWidget()
        w._generic_song_grid.song_double_clicked.connect(
            lambda fp, _w=w: _w._play_file(fp))

        # Build songs stacked widget: list (table) + grid (cards) inside Canciones tab
        w._songs_stack = QStackedWidget()
        w._songs_stack.setObjectName("songsStack")
        w._songs_stack.setStyleSheet("background: transparent; border: none;")
        w._songs_stack.addWidget(w._table)
        w._songs_stack.addWidget(w._song_grid)
        w._songs_stack.setCurrentIndex(0)

        # Build albums: grid (carátulas) + detail view inside Álbumes tab
        from ui.album_detail_view import AlbumDetailView
        w._album_detail_view = AlbumDetailView()
        w._album_detail_view.track_play_requested.connect(w._play_file)
        w._album_detail_view.play_album_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.play_album(tracks))
        w._album_detail_view.queue_album_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.queue_album(tracks))
        w._album_detail_view.play_next_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.play_next_album(tracks))
        w._album_detail_view.playlist_album_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.create_playlist_from_tracks(tracks))
        w._album_detail_view.metadata_album_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.edit_album_metadata(tracks))
        w._album_detail_view.cover_album_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.search_or_change_cover(tracks))
        w._album_detail_view.quality_album_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.analyze_album_quality(tracks))
        w._album_detail_view.send_to_server_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.send_album_to_server(tracks))
        w._album_detail_view.sync_mobile_requested.connect(
            lambda tracks, _w=w: _w._album_ctrl.sync_album_to_mobile(tracks))
        w._album_detail_view.track_queue_requested.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=False))
        w._album_detail_view.track_metadata_requested.connect(
            lambda fp, _w=w: _w._open_metadata_for_files([fp]))
        w._album_detail_view.track_analyze_requested.connect(
            lambda fp, _w=w: _w._album_ctrl.analyze_album_quality(
                [fp]))
        w._album_detail_view.open_folder_requested.connect(
            lambda folder, _w=w: _w._album_ctrl.open_folder([folder]))
        w._album_detail_view.open_folder_requested.connect(
            lambda folder, _w=w: __import__("subprocess").Popen(["xdg-open", folder])
            if folder else None)

        w._albums_stack = QStackedWidget()
        w._albums_stack.setObjectName("albumsStack")
        w._albums_stack.setStyleSheet("background: transparent; border: none;")
        w._albums_stack.addWidget(w._album_grid)
        w._albums_stack.addWidget(w._album_detail_view)
        w._albums_stack.setCurrentIndex(0)

        # Generic tracks table for playlists/favs/recent (separate from Canciones table)
        w._generic_tracks_table = QTableView()
        w._generic_tracks_table.setShowGrid(False)
        w._generic_tracks_table.setAlternatingRowColors(True)
        w._generic_tracks_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        w._generic_tracks_table.setSelectionMode(QAbstractItemView.SingleSelection)
        w._generic_tracks_table.setFrameShape(QFrame.NoFrame)
        w._generic_tracks_table.horizontalHeader().setStretchLastSection(True)
        w._generic_tracks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        w._generic_tracks_table.verticalHeader().setVisible(False)
        w._generic_tracks_table.verticalHeader().setDefaultSectionSize(30)
        w._generic_tracks_table.setSortingEnabled(True)
        w._generic_tracks_table.setStyleSheet(table_qss() + scrollbar_qss())

        w._discover = DiscoverDashboard()
        w._discover.navigate_requested.connect(
            lambda key, _w=w: _w._nav_ctrl.dispatch(key))

        w._playlist_hub = PlaylistHubWidget()
        w._playlist_hub.create_playlist_requested.connect(lambda _w=w: _w._sidebar_menu_ctrl.create_playlist())
        w._playlist_hub.import_m3u_requested.connect(lambda _w=w: _w._playlist_ctrl.import_m3u())
        w._playlist_hub.export_playlists_requested.connect(lambda _w=w: _w._playlist_ctrl.export_playlists())
        w._playlist_hub.smart_playlist_requested.connect(lambda key, _w=w: _w._playlist_ctrl.open_smart_playlist(key))
        w._playlist_hub.playlist_open_requested.connect(
            lambda pid, _w=w: _w._nav_ctrl.dispatch(f"pl:{pid}"))
        w._playlist_hub.playlist_play_requested.connect(
            lambda pid, _w=w: _w._playlist_ctrl.hub_playlist_play(pid))
        w._playlist_hub.playlist_queue_requested.connect(
            lambda pid, _w=w: _w._playlist_ctrl.hub_playlist_queue(pid))
        w._playlist_hub.create_from_folder_requested.connect(
            lambda _w=w: _w._playlist_ctrl.hub_create_from_folder())
        w._playlist_hub.create_from_queue_requested.connect(
            lambda _w=w: _w._playlist_ctrl.hub_create_from_queue())
        w._playlist_hub.export_text_requested.connect(
            lambda _w=w: _w._toast_svc.show("Funcionalidad en desarrollo — disponible próximamente", "info"))
        w._playlist_hub.find_duplicates_requested.connect(
            lambda _w=w: _w._toast_svc.show("Detección de duplicados pendiente de implementación", "info"))
        w._playlist_hub.scan_metadata_requested.connect(
            lambda _w=w: _w._toast_svc.show("Revisión de metadatos pendiente de implementación", "info"))
        w._playlist_hub.scan_missing_covers_requested.connect(
            lambda _w=w: _w._toast_svc.show("Búsqueda de carátulas faltantes pendiente de implementación", "info"))
        w._playlist_hub.clean_empty_playlists_requested.connect(
            lambda _w=w: _w._toast_svc.show("Limpieza de playlists vacías pendiente de implementación", "info"))
        w._playlist_hub.find_lost_files_requested.connect(
            lambda _w=w: _w._toast_svc.show("Búsqueda de canciones perdidas pendiente de implementación", "info"))

        w._playlist_detail = PlaylistDetailView()
        w._playlist_detail.play_requested.connect(lambda pid, _w=w: _w._playlist_ctrl.hub_playlist_play(pid))
        w._playlist_detail.queue_requested.connect(lambda pid, _w=w: _w._playlist_ctrl.hub_playlist_queue(pid))
        w._playlist_detail.edit_requested.connect(lambda pid, _w=w: _w._sidebar_menu_ctrl.edit_playlist_dialog(pid))
        w._playlist_detail.track_double_clicked.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=True))
        w._playlist_detail.track_activated.connect(
            w._on_playlist_track_activated)

        w._playlist_hub.playlist_edit_requested.connect(lambda pid, _w=w: _w._sidebar_menu_ctrl.edit_playlist_dialog(pid))
        w._playlist_hub.create_from_album_requested.connect(
            w._playlist_ctrl.create_from_album)
        w._playlist_hub.create_from_artist_requested.connect(
            w._playlist_ctrl.create_from_artist)
        w._playlist_hub.create_from_genre_requested.connect(
            w._playlist_ctrl.create_from_genre)
        w._playlist_hub.create_from_search_requested.connect(
            w._playlist_ctrl.create_from_search)

        w._metadata_editor = MetadataEditorWidget()
        w._metadata_editor.files_saved.connect(w._on_metadata_saved)
        w._metadata_editor.request_library_refresh.connect(lambda _w=w: _w._lib_ctrl.refresh_library())

        w._artist_grid = ArtistGridWidget()
        w._artist_detail = ArtistDetailView()
        w._artist_grid.artist_selected.connect(lambda key, _w=w: _w._artist_ctrl.open_artist_detail(key))
        w._artist_grid.artist_play_requested.connect(lambda key, _w=w: _w._artist_ctrl.play_artist(key))
        w._artist_grid.artist_queue_requested.connect(lambda key, _w=w: _w._artist_ctrl.queue_artist(key))
        w._artist_grid.artist_playlist_requested.connect(lambda key, _w=w: _w._artist_ctrl.create_playlist_from_artist(key))
        w._artist_grid.artist_metadata_requested.connect(lambda key, _w=w: _w._artist_ctrl.edit_artist_metadata(key))
        w._artist_grid.artist_enrich_requested.connect(w._refresh_artist_info)
        w._artist_grid.artist_mix_requested.connect(lambda key, _w=w: _w._artist_ctrl.create_artist_mix(key))
        w._artist_grid.artist_analyze_requested.connect(lambda key, _w=w: _w._artist_ctrl.analyze_artist_discography(key))
        w._artist_grid.artist_send_to_server_requested.connect(lambda key, _w=w: _w._artist_ctrl.send_artist_to_micro_server(key))
        w._artist_grid.artist_resolve_aliases_requested.connect(lambda key, _w=w: _w._artist_ctrl.resolve_artist_aliases(key))
        w._artist_detail.play_all_requested.connect(lambda key, _w=w: _w._artist_ctrl.play_artist(key))
        w._artist_detail.shuffle_all_requested.connect(lambda key, _w=w: _w._artist_ctrl.play_artist(key, shuffle=True))
        w._artist_detail.queue_all_requested.connect(lambda key, _w=w: _w._artist_ctrl.queue_artist(key))
        w._artist_detail.play_album_requested.connect(
            lambda fps, _w=w: _w._play_filepaths(fps, play_now=True))
        w._artist_detail.queue_album_requested.connect(
            lambda fps, _w=w: _w._play_filepaths(fps, play_now=False))
        w._artist_detail.playlist_artist_requested.connect(lambda key, _w=w: _w._artist_ctrl.create_playlist_from_artist(key))
        w._artist_detail.metadata_artist_requested.connect(lambda key, _w=w: _w._artist_ctrl.edit_artist_metadata(key))
        w._artist_detail.metadata_files_requested.connect(
            w._open_metadata_for_files)
        w._artist_detail.artist_enrich_requested.connect(w._refresh_artist_info)
        w._artist_detail.track_play_requested.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=True))
        w._artist_detail.track_queue_requested.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=False))
        w._artist_detail.track_metadata_requested.connect(
            lambda fp, _w=w: _w._open_metadata_for_files([fp]))
        # New detail signals
        w._artist_detail.album_metadata_requested.connect(
            lambda fps, _w=w: _w._artist_ctrl.open_metadata_for_files(fps))
        w._artist_detail.album_analyze_requested.connect(
            lambda fps, _w=w: _w._artist_ctrl.analyze_artist_album(fps))
        w._artist_detail.album_send_to_server_requested.connect(
            lambda fps, _w=w: _w._artist_ctrl.send_artist_album_to_micro_server(fps))
        w._artist_detail.track_analyze_requested.connect(
            lambda fp, _w=w: _w._artist_ctrl.analyze_artist_track(fp))
        w._artist_detail.track_send_to_server_requested.connect(
            lambda fp, _w=w: _w._artist_ctrl.send_artist_track_to_micro_server(fp))
        w._artist_detail.artist_mix_requested.connect(
            lambda key, _w=w: _w._artist_ctrl.create_artist_mix(key))
        w._artist_detail.artist_analyze_requested.connect(
            lambda key, _w=w: _w._artist_ctrl.analyze_artist_discography(key))
        w._artist_detail.artist_send_to_server_requested.connect(
            lambda key, _w=w: _w._artist_ctrl.send_artist_to_micro_server(key))
        w._artist_detail.artist_resolve_aliases_requested.connect(
            lambda key, _w=w: _w._artist_ctrl.resolve_artist_aliases(key))
        w._artist_detail.album_navigate_requested.connect(
            lambda album_title, _w=w: _w._album_ctrl.navigate_to_album_by_title(album_title))

        # Build artists stacked widget: grid + detail inside Artistas tab
        w._artists_stack = QStackedWidget()
        w._artists_stack.setObjectName("artistsStack")
        w._artists_stack.setStyleSheet("background: transparent; border: none;")
        w._artists_stack.addWidget(w._artist_grid)
        w._artists_stack.addWidget(w._artist_detail)
        w._artists_stack.setCurrentIndex(0)

        # Genre grid + detail
        w._genre_grid = GenreGridWidget()
        w._genre_detail = GenreDetailView()
        w._genre_grid.genre_selected.connect(lambda key, _w=w: _w._genre_ctrl.open_genre_detail(key))
        w._genre_grid.genre_play_requested.connect(lambda key, _w=w: _w._genre_ctrl.play_genre(key))
        w._genre_grid.genre_shuffle_requested.connect(lambda key, _w=w: _w._genre_ctrl.play_genre(key, shuffle=True))
        w._genre_grid.genre_queue_requested.connect(lambda key, _w=w: _w._genre_ctrl.queue_genre(key))
        w._genre_grid.genre_playlist_requested.connect(lambda key, _w=w: _w._genre_ctrl.create_playlist_from_genre(key))
        w._genre_grid.genre_metadata_requested.connect(lambda key, _w=w: _w._genre_ctrl.edit_genre_metadata(key))
        w._genre_grid.genre_normalize_requested.connect(lambda key, _w=w: _w._genre_ctrl.normalize_genre(key))
        w._genre_detail.play_requested.connect(lambda key, _w=w: _w._genre_ctrl.play_genre(key))
        w._genre_detail.shuffle_requested.connect(lambda key, _w=w: _w._genre_ctrl.play_genre(key, shuffle=True))
        w._genre_detail.queue_requested.connect(lambda key, _w=w: _w._genre_ctrl.queue_genre(key))
        w._genre_detail.playlist_requested.connect(lambda key, _w=w: _w._genre_ctrl.create_playlist_from_genre(key))
        w._genre_detail.metadata_requested.connect(lambda key, _w=w: _w._genre_ctrl.edit_genre_metadata(key))
        w._genre_detail.normalize_requested.connect(lambda key, _w=w: _w._genre_ctrl.normalize_genre(key))
        w._genre_detail.track_play_requested.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=True))
        w._genre_detail.track_queue_requested.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=False))

        # Build genres stacked widget: grid + detail inside Géneros tab
        w._genres_stack = QStackedWidget()
        w._genres_stack.setObjectName("genresStack")
        w._genres_stack.setStyleSheet("background: transparent; border: none;")
        w._genres_stack.addWidget(w._genre_grid)     # index 0
        w._genres_stack.addWidget(w._genre_detail)   # index 1

        # New genre hub page, detail page, and cleanup page
        w._genre_hub_page = GenreHubPage()
        w._genre_detail_page = GenreDetailPage()
        w._genre_cleanup_page = GenreCleanupPage()

        # Bind pages to controller AFTER creation so references exist
        w._genre_ctrl.bind_pages(
            hub_page=w._genre_hub_page,
            detail_page=w._genre_detail_page,
            cleanup_page=w._genre_cleanup_page,
            cleanup_ctrl=getattr(w, '_genre_cleanup_ctrl', None),
            db_genre_repo=getattr(w, '_db_genre_repo', None),
            stats_svc=getattr(w, '_genre_stats_svc', None),
            mix_svc=getattr(w, '_genre_mix_svc', None),
        )

        w._genre_hub_page.genre_selected.connect(
            lambda key, _w=w: _w._genre_ctrl.open_genre_detail(key))
        w._genre_hub_page.genre_play_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.play_genre(key))
        w._genre_hub_page.genre_shuffle_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.play_genre(key, shuffle=True))
        w._genre_hub_page.genre_queue_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.queue_genre(key))
        w._genre_hub_page.genre_mix_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.create_mix_for_genre(key))
        w._genre_hub_page.genre_radio_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.create_radio_for_genre(key))
        w._genre_hub_page.genre_playlist_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.create_playlist_from_genre(key))
        w._genre_hub_page.genre_cleanup_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.show_cleanup_page())
        w._genre_hub_page.cleanup_page_requested.connect(
            lambda: w._genre_ctrl.show_cleanup_page())

        w._genre_detail_page.play_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.play_genre(key))
        w._genre_detail_page.shuffle_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.play_genre(key, shuffle=True))
        w._genre_detail_page.queue_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.queue_genre(key))
        w._genre_detail_page.mix_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.create_mix_for_genre(key))
        w._genre_detail_page.radio_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.create_radio_for_genre(key))
        w._genre_detail_page.playlist_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.create_playlist_from_genre(key))
        w._genre_detail_page.cleanup_requested.connect(
            lambda key, _w=w: _w._genre_ctrl.show_cleanup_page())
        w._genre_detail_page.track_play_requested.connect(
            lambda fp, _w=w: _w._play_filepaths([fp], play_now=True))

        w._genre_cleanup_page.refresh_requested.connect(
            lambda: w._genre_ctrl.show_cleanup_page())
        w._genre_cleanup_page.merge_requested.connect(
            lambda sources, target, _w=w: _w._genre_cleanup_ctrl.execute_merge(
                sources, target) if target and sources else None)
        w._genre_cleanup_page.apply_genre_requested.connect(
            lambda tids, genre, _w=w: _w._genre_cleanup_ctrl.execute_apply_genre(tids, genre))

        # Register new genre pages in the views system
        w._genres_stack.addWidget(w._genre_hub_page)     # index 2
        w._genres_stack.addWidget(w._genre_detail_page)   # index 3
        w._genres_stack.addWidget(w._genre_cleanup_page)  # index 4
        w._genres_stack.setCurrentIndex(0)

        w._folder_browser = FolderBrowserWidget(db=w._db)
        w._folder_browser.folder_selected.connect(w._on_folder_selected)
        w._folder_browser.queue_requested.connect(w._on_folder_queued)
        w._folder_browser.scan_requested.connect(w._on_folder_scan_requested)
        w._folder_browser.create_playlist_requested.connect(
            lambda name, fps, _w=w: _w._file_actions.folder_create_playlist(name, fps))

        w._content = QStackedWidget()
        w._content.setMinimumHeight(200)

        w._views = ViewController(w._content, w)
        w._views.register("empty", placeholder)
        w._views.register("remote", w._remote_placeholder)
        w._views.register("expanded", placeholder_expanded)
        w._views.register("radio", w._radio_widget)
        w._views.register("discover", w._discover)
        w._views.register("playlist_hub", w._playlist_hub)
        w._views.register("playlist_detail", w._playlist_detail)
        w._views.register("metadata_editor", w._metadata_editor)
        w._views.register("home_audio", w._home_audio_view)
        w._views.register("identifier", w._identifier_view)
        w._views.show("empty")

        from ui.view_navigator import ViewNavigator
        w._nav = ViewNavigator(w._content, w._views, w._views)
        w._nav._widgets = [
            w._content, w._album_grid,
            w._folder_browser, w._radio_widget,
            w._playlist_hub, w._metadata_editor,
            w._discover, w._identifier_view,
            w._home_audio_view,
        ]
        from core.background_theme_service import BackgroundThemeService
        w._bg_theme = BackgroundThemeService(w._content)
        from core.playback_controller import PlaybackController
        w._playback_ctrl = PlaybackController(w)

        # ── Content wrapper ──
        cw = QWidget()
        cw.setObjectName("contentSurface")
        cw.setStyleSheet(
            "QWidget#contentSurface {"
            "  background: #090B11;"
            "  border-left: 1px solid rgba(255,255,255,0.045);"
            "}")
        w._content.setStyleSheet(
            "QStackedWidget {"
            "  background: #090B11;"
            "  border: none;"
            "}")
        cl = QVBoxLayout(cw)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        cl.addWidget(header)
        cl.addWidget(w._content)

        # ── Splitter ──
        sp = QSplitter(Qt.Horizontal)
        sp.addWidget(w._sidebar)
        sp.addWidget(cw)
        sp.setCollapsible(0, False)
        sp.setCollapsible(1, False)
        sp.setStretchFactor(0, 0)
        sp.setStretchFactor(1, 1)
        sp.setSizes([320, 900])
        sp.setStyleSheet(
            "QSplitter::handle { background: rgba(255,255,255,0.08); width: 2px; }")

        # ── NowPlaying bar ──
        w._player_bar = NowPlayingBar()
        from ui.controllers.player_bar_controller import PlayerBarController
        ctx_svc = getattr(w, '_context_svc', None)
        w._player_bar_ctrl = PlayerBarController(w._player_bar, context_service=ctx_svc)

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
        wl.addWidget(w._player_bar)

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
        w.setCentralWidget(cent)
