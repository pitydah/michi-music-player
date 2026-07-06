"""BasePagedListModel — async paginated QAbstractListModel via QueryExecutor.

Subclasses define:
    _owner() -> str              unique owner id (e.g. "tracks", "albums")
    _fetch_count(**query) -> int
    _fetch_page(offset, limit, **query) -> list[dict]

refresh() executes one combined task (count + page).
fetchMore() reuses the stored query args.
Stale results are ignored.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Signal


class BasePagedListModel(QAbstractListModel):
    countChanged = Signal()
    totalCountChanged = Signal()
    loadingChanged = Signal()
    loadingMoreChanged = Signal()
    errorChanged = Signal()
    hasMoreChanged = Signal()

    def __init__(self, page_size: int = 250, query_executor=None, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._total_count = 0
        self._page_size = page_size
        self._loading = False
        self._loading_more = False
        self._error_code = ""
        self._error_message = ""
        self._qe = query_executor
        self._query_args: dict = {}
        self._active_request_id: int = 0
        self._refresh_gen = 0

    # ── Properties ──

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._items)

    @Property(int, notify=totalCountChanged)
    def totalCount(self):
        return self._total_count

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @Property(bool, notify=loadingMoreChanged)
    def loadingMore(self):
        return self._loading_more

    @Property(str, notify=errorChanged)
    def errorCode(self):
        return self._error_code

    @Property(str, notify=errorChanged)
    def errorMessage(self):
        return self._error_message

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self):
        return len(self._items) < self._total_count

    @Property(int, constant=True)
    def activeRequestId(self):
        return self._active_request_id

    # ── QAbstractListModel ──

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        return len(self._items) < self._total_count and not self._loading and not self._loading_more

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid() or self._loading or self._loading_more:
            return
        if not self._qe or not len(self._items) < self._total_count:
            return
        self._loading_more = True
        self.loadingMoreChanged.emit()
        gen = self._refresh_gen
        offset = len(self._items)
        query = dict(self._query_args)
        page_size = self._page_size

        def _task():
            return self._fetch_page(offset, page_size, **query)

        def _on_success(items):
            if gen != self._refresh_gen:
                return
            if not items:
                items = []
            self.beginInsertRows(QModelIndex(), offset, offset + len(items) - 1)
            self._items.extend(items)
            self.endInsertRows()
            self._loading_more = False
            self.loadingMoreChanged.emit()
            self.countChanged.emit()
            self.hasMoreChanged.emit()

        def _on_error(code, msg):
            if gen != self._refresh_gen:
                return
            self._error_code = code
            self._error_message = msg
            self._loading_more = False
            self.loadingMoreChanged.emit()
            self.errorChanged.emit()

        if self._qe is not None:
            self._active_request_id = self._qe.submit(
                self._owner(), _task, on_success=_on_success, on_error=_on_error,
            )
        else:
            items = _task()
            _on_success(items)

    # ── Refresh API ──

    def refresh(self, **kwargs):
        if self._loading:
            return
        self._refresh_gen += 1
        self._query_args = dict(kwargs)
        self._error_code = ""
        self._error_message = ""
        self._loading = True
        self.loadingChanged.emit()
        gen = self._refresh_gen
        query = dict(kwargs)
        page_size = self._page_size

        def _task():
            count = self._fetch_count(**query)
            items = self._fetch_page(0, page_size, **query)
            return (count, items)

        def _on_success(result):
            if gen != self._refresh_gen:
                return
            count, items = result if isinstance(result, tuple) and len(result) == 2 else (0, [])
            self._total_count = count if isinstance(count, int) else 0
            self.beginResetModel()
            self._items = list(items) if items else []
            self.endResetModel()
            self._error_code = ""
            self._error_message = ""
            self._loading = False
            self.loadingChanged.emit()
            self.totalCountChanged.emit()
            self.countChanged.emit()
            self.hasMoreChanged.emit()

        def _on_error(code, msg):
            if gen != self._refresh_gen:
                return
            self._error_code = code
            self._error_message = msg
            self._loading = False
            self.loadingChanged.emit()
            self.errorChanged.emit()

        if self._qe is not None:
            self._active_request_id = self._qe.submit(
                self._owner(), _task, on_success=_on_success, on_error=_on_error,
            )
        else:
            result = _task()
            _on_success(result)

    def retry(self):
        if self._query_args:
            self.refresh(**self._query_args)

    # ── Subclass hooks ──

    def _owner(self) -> str:
        raise NotImplementedError

    def _fetch_count(self, **kwargs) -> int:
        raise NotImplementedError

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict]:
        raise NotImplementedError
