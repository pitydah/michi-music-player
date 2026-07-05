"""BasePagedListModel — shared paginated QAbstractListModel infrastructure."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Signal


class BasePagedListModel(QAbstractListModel):
    """Base class for paginated list models with async loading.

    Subclasses must define:
        roleNames()
        data()
        _fetch_count() -> int
        _fetch_page(offset, limit) -> list[dict]
    """

    countChanged = Signal()
    loadingChanged = Signal()
    errorChanged = Signal()
    hasMoreChanged = Signal()

    def __init__(self, page_size: int = 250, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._total_count = 0
        self._page_size = page_size
        self._loading = False
        self._error = ""
        self._query_executor = None
        self._owner_id = ""
        self._request_gen = 0

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._items)

    @Property(int, notify=countChanged)
    def totalCount(self):
        return self._total_count

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @Property(str, notify=errorChanged)
    def error(self):
        return self._error

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self):
        return len(self._items) < self._total_count

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        return len(self._items) < self._total_count

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid() or self._loading:
            return
        self._load_page(len(self._items))

    def refresh(self, **kwargs):
        """Refresh the model with new query parameters. Override in subclass."""
        self._request_gen += 1
        self._error = ""
        self._loading = True
        self.loadingChanged.emit()
        self._load_count(**kwargs)
        self._load_page(0, **kwargs)

    def _load_count(self, **kwargs):
        try:
            self._total_count = self._fetch_count(**kwargs)
        except Exception as e:
            self._total_count = 0
            self._error = str(e)
        self.countChanged.emit()
        self.hasMoreChanged.emit()

    def _load_page(self, offset: int, **kwargs):
        self._loading = True
        self.loadingChanged.emit()
        try:
            items = self._fetch_page(offset, self._page_size, **kwargs)
            if offset == 0:
                self.beginResetModel()
                self._items = items
                self.endResetModel()
            else:
                self.beginInsertRows(QModelIndex(), offset, offset + len(items) - 1)
                self._items.extend(items)
                self.endInsertRows()
            self._error = ""
        except Exception as e:
            self._error = str(e)
            self.errorChanged.emit()
        self._loading = False
        self.loadingChanged.emit()
        self.countChanged.emit()
        self.hasMoreChanged.emit()

    def _fetch_count(self, **kwargs) -> int:
        raise NotImplementedError

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict]:
        raise NotImplementedError
