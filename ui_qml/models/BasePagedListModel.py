"""BasePagedListModel — async paginated QAbstractListModel via QueryExecutor.

Subclasses define:
    _owner() -> str
    _fetch_count(**query) -> int
    _fetch_page(offset, limit, **query) -> list[dict]

refresh() siempre actualiza query_args y cancela request previo.
fetchMore() preserva filtros. Stale results ignorados.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Signal


class BasePagedListModel(QAbstractListModel):
    countChanged = Signal()
    totalCountChanged = Signal()
    loadingChanged = Signal()
    loadingMoreChanged = Signal()
    refreshingChanged = Signal()
    errorChanged = Signal()
    hasMoreChanged = Signal()
    activeRequestChanged = Signal()
    activeQueryChanged = Signal()

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

    @Property(bool, notify=refreshingChanged)
    def refreshing(self):
        return self._loading and not self._loading_more

    @Property(str, notify=errorChanged)
    def errorCode(self):
        return self._error_code

    @Property(str, notify=errorChanged)
    def errorMessage(self):
        return self._error_message

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self):
        return len(self._items) < self._total_count

    @Property(int, notify=activeRequestChanged)
    def activeRequestId(self):
        return self._active_request_id

    @Property("QVariantMap", notify=activeQueryChanged)
    def activeQuery(self):
        return dict(self._query_args)

    @Property(bool, notify=countChanged)
    def empty(self):
        return self._total_count == 0

    @Property(bool, notify=errorChanged)
    def canRetry(self):
        return bool(self._query_args) and not self._loading

    # ── QAbstractListModel ──

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        return (len(self._items) < self._total_count
                and not self._loading and not self._loading_more)

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
                self._reset_loading_more()
                return
            if not items:
                self._reset_loading_more()
                return
            self.beginInsertRows(QModelIndex(), offset, offset + len(items) - 1)
            self._items.extend(items)
            self.endInsertRows()
            self._loading_more = False
            self.loadingMoreChanged.emit()
            self.countChanged.emit()
            self.hasMoreChanged.emit()

        def _on_error(code, msg):
            if gen != self._refresh_gen:
                self._reset_loading_more()
                return
            self._error_code = code
            self._error_message = msg
            self._loading_more = False
            self.loadingMoreChanged.emit()
            self.errorChanged.emit()

        if self._qe is not None:
            self._active_request_id = self._qe.submit(
                self._owner(), _task, on_success=_on_success, on_error=_on_error,
                supersede=False,
            )
        else:
            items = _task()
            _on_success(items)

    # ── Refresh API ──

    def refresh(self, **kwargs):
        self._invalidate_active()
        self._refresh_gen += 1
        self._query_args = dict(kwargs)
        self._error_code = ""
        self._error_message = ""
        self._loading = True
        self._loading_more = False
        self.loadingChanged.emit()
        self.loadingMoreChanged.emit()
        self.activeQueryChanged.emit()
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
                supersede=True,
            )
            self.activeRequestChanged.emit()
        else:
            result = _task()
            _on_success(result)

    def cancel(self):
        self._invalidate_active()
        self._loading = False
        self._loading_more = False
        self.loadingChanged.emit()
        self.loadingMoreChanged.emit()

    def retry(self):
        if self._query_args:
            self.refresh(**self._query_args)

    def reset(self):
        self._invalidate_active()
        self.beginResetModel()
        self._items = []
        self._total_count = 0
        self._query_args = {}
        self._error_code = ""
        self._error_message = ""
        self._loading = False
        self._loading_more = False
        self.endResetModel()
        self.countChanged.emit()
        self.totalCountChanged.emit()
        self.loadingChanged.emit()
        self.loadingMoreChanged.emit()
        self.hasMoreChanged.emit()

    # ── Internal ──

    def _invalidate_active(self):
        if self._qe and self._active_request_id:
            self._qe.cancel(self._active_request_id)
            self._active_request_id = 0

    def _reset_loading_more(self):
        self._loading_more = False
        self.loadingMoreChanged.emit()

    def _owner(self) -> str:
        raise NotImplementedError

    def _fetch_count(self, **kwargs) -> int:
        raise NotImplementedError

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict]:
        raise NotImplementedError
