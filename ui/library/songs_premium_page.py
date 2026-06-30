"""SongsPremiumPage — premium song management view for Biblioteca > Canciones.

Integrates MediaItemTableModel, SongsFilterBar, SongsBulkActionBar,
and SongsDetailPanel into a single QWidget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTableView,
)

from library.mediaitem_table_model import MediaItemTableModel
from ui.library.songs_filter_bar import SongsFilterBar
from ui.library.songs_bulk_action_bar import SongsBulkActionBar
from ui.library.songs_detail_panel import SongsDetailPanel

if TYPE_CHECKING:
    pass


class SongsPremiumPage(QWidget):
    """Premium songs management page.

    Contains a filter bar, a master table, a detail panel, and a bulk action bar.
    Works with SongsController for data and actions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = MediaItemTableModel(self)
        self._ctrl = None
        self._setup_ui()

    def set_controller(self, ctrl):
        self._ctrl = ctrl
        if ctrl:
            self._filter_bar.set_formats(
                ctrl.query_service.distinct_formats()
            )

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Filter bar
        self._filter_bar = SongsFilterBar(self)
        self._filter_bar.filters_changed.connect(self._on_filters_changed)
        outer.addWidget(self._filter_bar)

        # Splitter: table + detail panel
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(0)

        # Table
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionsClickable(True)
        self._table.setStyleSheet(self._table_qss())
        self._table.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        splitter.addWidget(self._table)

        # Detail panel
        self._detail_panel = SongsDetailPanel()
        splitter.addWidget(self._detail_panel)

        outer.addWidget(splitter, 1)

        # Bulk action bar
        self._bulk_bar = SongsBulkActionBar(self)
        outer.addWidget(self._bulk_bar)

    def _on_filters_changed(self, filters: dict):
        if not self._ctrl:
            return
        items = self._ctrl.apply_filter(**filters)
        fav_ids = self._ctrl.status_service._fav_ids if self._ctrl else set()
        status_cache = self._ctrl.status_service._quality_cache if self._ctrl else {}
        self._model.populate(items, fav_ids=fav_ids, status_cache=status_cache)
        self._resize_columns()

    def _on_selection_changed(self, selected, _deselected):
        rows = [r.row() for r in selected.indexes()]
        unique_rows = list(dict.fromkeys(rows))
        count = len(unique_rows)
        self._bulk_bar.show_for_selection(count)

        if count == 1:
            item = self._model.item_at(unique_rows[0])
            if item:
                self._detail_panel.show_item(item)
        else:
            self._detail_panel.clear()

    def _resize_columns(self):
        widths = self._model.column_widths()
        for i, w in enumerate(widths):
            if i < self._model.columnCount():
                self._table.setColumnWidth(i, w)

    def load_data(self, items: list, fav_ids: set[int] | None = None,
                  status_cache: dict[int, dict] | None = None):
        self._model.populate(items, fav_ids=fav_ids, status_cache=status_cache)
        self._resize_columns()

    @staticmethod
    def _table_qss() -> str:
        return """
        QTableView {
            background: transparent;
            alternate-background-color: rgba(255,255,255,0.02);
            border: none;
            outline: none;
            color: rgba(255,255,255,0.80);
            font-size: 12px;
        }
        QTableView::item:selected {
            background: rgba(143,183,255,0.18);
            color: rgba(255,255,255,0.95);
        }
        QTableView::item:hover {
            background: rgba(143,183,255,0.08);
        }
        QHeaderView::section {
            background: rgba(255,255,255,0.04);
            color: rgba(255,255,255,0.60);
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 6px 4px;
            font-size: 11px;
            font-weight: 600;
        }
        """
