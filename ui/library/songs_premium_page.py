"""SongsPremiumPage — premium song management view for Biblioteca > Canciones.

Integrates MediaItemTableModel, SongsFilterBar, SongsBulkActionBar,
and SongsDetailPanel. Works with SongsController for data and actions.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTableView, QHeaderView, QLabel, QMenu,
)

from library.mediaitem_table_model import MediaItemTableModel
from library.songs_view_state import SongsFilterState
from ui.library.songs_filter_bar import SongsFilterBar
from ui.library.songs_bulk_action_bar import SongsBulkActionBar
from ui.library.songs_detail_panel import SongsDetailPanel
from ui.library.songs_status_delegate import SongsStatusDelegate


class SongsPremiumPage(QWidget):
    """Premium songs management page with filter bar, master table, detail panel, bulk actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = MediaItemTableModel(self)
        self._ctrl = None
        self._setup_ui()

    def set_controller(self, ctrl):
        self._ctrl = ctrl
        if ctrl:
            ctrl.data_changed.connect(self._on_data_changed)
            self._filter_bar.set_formats(
                ctrl.query_service.distinct_formats()
            )
            self._filter_bar.set_genres(
                ctrl.query_service.distinct_genres()
            )
            from PySide6.QtCore import QSettings
            settings = QSettings("Michi", "MichiMusicPlayer")
            cols_str = settings.value("songs_optional_columns", "")
            if cols_str:
                self._model.set_optional_columns(cols_str.split(","))

    def _on_data_changed(self, vs):
        self._model.populate(vs.items, fav_set=set(vs.favorite_track_ids),
                             status_cache=dict(vs.status_cache))
        self._resize_columns()
        self._loading_label.hide()
        if not vs.items:
            self._empty_label.show()
        else:
            self._empty_label.hide()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._filter_bar = SongsFilterBar(self)
        self._filter_bar.filters_changed.connect(self._on_filters_changed)
        outer.addWidget(self._filter_bar)

        self._loading_label = QLabel("Cargando canciones...")
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet("color: rgba(255,255,255,0.50); font-size: 13px;")
        self._loading_label.hide()
        outer.addWidget(self._loading_label)

        self._empty_label = QLabel("No hay canciones que coincidan con los filtros")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: rgba(255,255,255,0.40); font-size: 13px;")
        self._empty_label.hide()
        outer.addWidget(self._empty_label)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(0)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionsClickable(True)
        self._table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.horizontalHeader().customContextMenuRequested.connect(self._show_column_menu)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_body_context_menu)
        self._table.setStyleSheet(self._table_qss())
        self._delegate = SongsStatusDelegate(
            status_cache_provider=lambda: self._ctrl.status_cache() if self._ctrl else {})
        self._table.setItemDelegateForColumn(9, self._delegate)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._table)

        self._detail_panel = SongsDetailPanel()
        self._detail_panel.play_requested.connect(self._on_detail_play)
        self._detail_panel.queue_requested.connect(self._on_detail_queue)
        self._detail_panel.edit_requested.connect(self._on_detail_edit)
        self._detail_panel.locate_requested.connect(self._on_detail_locate)
        self._detail_panel.fav_requested.connect(self._on_detail_fav)
        self._detail_panel.analyze_requested.connect(self._on_detail_analyze)
        splitter.addWidget(self._detail_panel)

        outer.addWidget(splitter, 1)

        self._bulk_bar = SongsBulkActionBar(self)
        self._bulk_bar.action_play.connect(lambda: self._run_bulk("play"))
        self._bulk_bar.action_queue.connect(lambda: self._run_bulk("queue"))
        self._bulk_bar.action_edit_metadata.connect(lambda: self._run_bulk("edit"))
        self._bulk_bar.action_toggle_fav.connect(lambda: self._run_bulk("fav"))
        self._bulk_bar.action_add_to_playlist.connect(lambda: self._run_bulk("playlist"))
        self._bulk_bar.action_analyze.connect(lambda: self._run_bulk("analyze"))
        self._bulk_bar.action_locate.connect(lambda: self._run_bulk("locate"))
        outer.addWidget(self._bulk_bar)

    def selected_items(self) -> list:
        sel = self._table.selectionModel()
        if not sel:
            return []
        rows = sorted(set(r.row() for r in sel.selectedRows()))
        return [self._model.item_at(r) for r in rows if self._model.item_at(r) is not None]

    def _run_bulk(self, action: str):
        items = self.selected_items()
        if not items or not self._ctrl:
            return
        if action == "play":
            self._ctrl.play_items(items)
        elif action == "queue":
            self._ctrl.queue_items(items)
        elif action == "edit":
            self._ctrl.edit_metadata(items)
        elif action == "fav":
            for item in items:
                self._ctrl.toggle_favorite(item)
        elif action == "playlist":
            self._ctrl.add_to_playlist(items)
        elif action == "analyze":
            self._ctrl.analyze_quality(items)
        elif action == "locate":
            self._ctrl.locate_file(items[0])
        elif action == "server":
            self._ctrl.send_to_micro_server(items)
        elif action == "mobile":
            self._ctrl.sync_to_mobile(items)
        elif action == "convert":
            self._ctrl.convert_items(items)

    def _on_detail_play(self, item):
        if self._ctrl:
            self._ctrl.play_items([item])

    def _on_detail_queue(self, item):
        if self._ctrl:
            self._ctrl.queue_items([item])

    def _on_detail_edit(self, item):
        if self._ctrl:
            self._ctrl.edit_metadata([item])

    def _on_detail_locate(self, item):
        if self._ctrl:
            self._ctrl.locate_file(item)

    def _on_detail_fav(self, item):
        if self._ctrl:
            self._ctrl.toggle_favorite(item)

    def _on_detail_analyze(self, item):
        if self._ctrl:
            self._ctrl.analyze_quality([item])

    def _on_filters_changed(self, state: SongsFilterState):
        if not self._ctrl:
            return
        self._ctrl.apply_filter(filter_state=state)
        # _on_data_changed will be called via data_changed signal

    def _on_selection_changed(self, selected, _deselected):
        rows = [r.row() for r in selected.indexes()]
        unique_rows = list(dict.fromkeys(rows))
        count = len(unique_rows)
        self._bulk_bar.show_for_selection(count)
        if count == 1:
            item = self._model.item_at(unique_rows[0])
            if item:
                status = self._model.status_for_item(item)
                self._detail_panel.show_item(item, status=status)
        else:
            self._detail_panel.clear()

    def _resize_columns(self):
        widths = self._model.column_widths()
        for i, w in enumerate(widths):
            if i < self._model.columnCount():
                self._table.setColumnWidth(i, w)

    def load_data(self, items: list, fav_set: set[str] | None = None,
                  status_cache: dict[int, dict] | None = None):
        self._loading_label.show()
        if self._ctrl:
            wm = getattr(getattr(self._ctrl, '_services', None), 'workers', None)
            if wm and hasattr(wm, 'run_task') and len(items) > 500:
                def _compute():
                    vs = self._ctrl.view_state()
                    return vs
                def _on_done(vs):
                    if vs is None:
                        return
                    self._model.populate(
                        vs.items,
                        fav_set=set(vs.favorite_track_ids),
                        status_cache=dict(vs.status_cache),
                    )
                    self._resize_columns()
                    self._loading_label.hide()
                    if not vs.items:
                        self._empty_label.show()
                    else:
                        self._empty_label.hide()
                wm.run_task("load_songs", _compute, on_done=_on_done)
                return
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        self._model.populate(items, fav_set=fav_set, status_cache=status_cache)
        self._resize_columns()
        self._loading_label.hide()
        if not items:
            self._empty_label.show()
        else:
            self._empty_label.hide()

    def _show_column_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtCore import QSettings
        menu = QMenu(self)
        current_opts = set(self._model.get_optional_columns())
        for key, (label, _width) in [
            ("bitrate", "Bitrate"), ("sample_rate", "Sample Rate"), ("bit_depth", "Bit Depth"),
            ("channels", "Canales"), ("bpm", "BPM"), ("key", "Tonalidad"),
            ("play_count", "Reproducciones"), ("rating", "Rating"), ("size", "Tamaño"),
            ("replaygain_track", "RG Track"), ("replaygain_album", "RG Album"),
        ]:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(key in current_opts)
            action.setData(key)
        action = menu.exec(self._table.horizontalHeader().viewport().mapToGlobal(pos))
        if action:
            key = action.data()
            opts = list(current_opts)
            if key in opts:
                opts.remove(key)
            else:
                opts.append(key)
            self._model.set_optional_columns(opts)
            self._model.populate(self._model.all_items(), fav_set=self._model.favorite_set(),
                                 status_cache=self._model.status_cache())
            vs = self._ctrl.view_state() if self._ctrl else None
            if vs:
                self._model.populate(vs.items, fav_set=set(vs.favorite_track_ids),
                                     status_cache=dict(vs.status_cache))
            self._resize_columns()
            settings = QSettings("Michi", "MichiMusicPlayer")
            settings.setValue("songs_optional_columns", ",".join(opts))

    def _show_body_context_menu(self, pos):
        items = self.selected_items()
        if not items:
            return
        from ui.central.central_styles import menu_qss
        menu = QMenu(self)
        menu.setStyleSheet(menu_qss())

        play_act = menu.addAction("▶ Reproducir")
        queue_act = menu.addAction("⊕ Añadir a la cola")
        menu.addSeparator()
        fav_act = menu.addAction("★ Favorito / Quitar favorito")
        metadata_act = menu.addAction("✎ Editar metadatos")
        playlist_act = menu.addAction("📋 Agregar a playlist")
        menu.addSeparator()
        analyze_act = menu.addAction("🔬 Analizar calidad")
        locate_act = menu.addAction("📁 Localizar archivo")
        menu.addSeparator()
        server_act = menu.addAction("📤 Enviar a Michi Micro Server")
        mobile_act = menu.addAction("📱 Sincronizar a Michi Mobile")
        convert_act = menu.addAction("🔄 Convertir formato")
        menu.addSeparator()
        select_all_act = menu.addAction("Seleccionar todo")

        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if not action:
            return
        if action == play_act:
            self._run_bulk("play")
        elif action == queue_act:
            self._run_bulk("queue")
        elif action == fav_act:
            self._run_bulk("fav")
        elif action == metadata_act:
            self._run_bulk("edit")
        elif action == playlist_act:
            self._run_bulk("playlist")
        elif action == analyze_act:
            self._run_bulk("analyze")
        elif action == locate_act:
            self._run_bulk("locate")
        elif action == server_act:
            self._run_bulk("server")
        elif action == mobile_act:
            self._run_bulk("mobile")
        elif action == convert_act:
            self._run_bulk("convert")
        elif action == select_all_act:
            self._table.selectAll()

    @staticmethod
    def _table_qss() -> str:
        return """
        QTableView { background: transparent; alternate-background-color: rgba(255,255,255,0.02);
            border: none; outline: none; color: rgba(255,255,255,0.80); font-size: 12px; }
        QTableView::item { padding: 6px 4px; min-height: 28px; }
        QTableView::item:selected { background: rgba(143,183,255,0.18); color: rgba(255,255,255,0.95); }
        QTableView::item:hover { background: rgba(143,183,255,0.08); }
        QHeaderView::section { background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.60);
            border: none; border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 6px 4px; font-size: 11px; font-weight: 600; }
        """
