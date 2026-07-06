"""BasePagedListModel — async paginated QAbstractListModel via QueryExecutor."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Signal


class BasePagedListModel(QAbstractListModel):
    countChanged = Signal()
    loadingChanged = Signal()
    errorChanged = Signal()
    hasMoreChanged = Signal()
    loadingMoreChanged = Signal()

    def __init__(self, page_size: int = 250, query_executor=None, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._total_count = 0
        self._page_size = page_size
        self._loading = False
        self._loading_more = False
        self._error = ""
        self._qe = query_executor
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

    @Property(bool, notify=loadingMoreChanged)
    def loadingMore(self):
        return self._loading_more

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
        return len(self._items) < self._total_count and not self._loading

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid() or self._loading or self._loading_more:
            return
        self._loading_more = True
        self.loadingMoreChanged.emit()
        gen = self._request_gen
        offset = len(self._items)

        def _task():
            return self._fetch_page(offset, self._page_size)

        def _done(result):
            if gen != self._request_gen or not result:
                self._loading_more = False
                self.loadingMoreChanged.emit()
                return
            self.beginInsertRows(QModelIndex(), offset, offset + len(result) - 1)
            self._items.extend(result)
            self.endInsertRows()
            self._loading_more = False
            self.loadingMoreChanged.emit()
            self.countChanged.emit()
            self.hasMoreChanged.emit()

        if self._qe and hasattr(self._qe, 'submit'):
            self._qe.submit(self._owner_id, _task, callback=_done)
        else:
            result = _task()
            _done(result)

    def refresh(self, **kwargs):
        self._request_gen += 1
        self._error = ""
        self._loading = True
        self.loadingChanged.emit()
        gen = self._request_gen

        def _count_task():
            return self._fetch_count(**kwargs)

        def _page_task():
            return self._fetch_page(0, self._page_size, **kwargs)

        def _all_done(results):
            if gen != self._request_gen:
                self._loading = False
                self.loadingChanged.emit()
                return
            count, items = results if isinstance(results, tuple) and len(results) == 2 else (0, [])
            if count is not None:
                self._total_count = count
            self.beginResetModel()
            self._items = items if items else []
            self.endResetModel()
            self._error = ""
            self._loading = False
            self.loadingChanged.emit()
            self.countChanged.emit()
            self.hasMoreChanged.emit()
            self.errorChanged.emit()

        if self._qe and hasattr(self._qe, 'submit'):
            self._qe.submit(self._owner_id, _count_task, callback=lambda c: None)
            self._qe.submit(self._owner_id, _page_task, callback=lambda p: _all_done((p, p)))
        else:
            count = _count_task()
            items = _page_task()
            _all_done((count, items))

    def _fetch_count(self, **kwargs) -> int:
        raise NotImplementedError

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict]:
        raise NotImplementedError
