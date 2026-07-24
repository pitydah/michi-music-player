"""QueueListModel — BasePagedListModel observing the canonical QueueService."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal, Slot

from ui_qml.models.BasePagedListModel import BasePagedListModel
from ui_qml.models.queue_item import queue_item_from_raw


class QueueListModel(BasePagedListModel):
    """Reactive projection of the canonical queue state."""

    _domainChanged = Signal(str, object)
    TrackIdRole = Qt.UserRole + 1
    TrackUidRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    ArtistRole = Qt.UserRole + 4
    AlbumRole = Qt.UserRole + 5
    AlbumKeyRole = Qt.UserRole + 6
    DurationRole = Qt.UserRole + 7
    CurrentRole = Qt.UserRole + 8
    PositionRole = Qt.UserRole + 9
    CoverKeyRole = Qt.UserRole + 10
    SourceTypeRole = Qt.UserRole + 11

    def __init__(self, queue_service=None, query_executor=None, parent=None) -> None:
        super().__init__(page_size=500, query_executor=query_executor, parent=parent)
        self._queue_service = queue_service
        self._queue_state = queue_service.get_state() if queue_service else {
            "items": [], "current_index": -1,
        }
        self._unsubscribe = None
        self._domainChanged.connect(self._on_domain_changed)
        if queue_service and hasattr(queue_service, "subscribe"):
            self._unsubscribe = queue_service.subscribe(self._queue_event)
        self.destroyed.connect(self._unsubscribe_queue)
        self.refresh()

    def _queue_event(self, event: str, state: dict) -> None:
        self._domainChanged.emit(event, state)

    @Slot(str, object)
    def _on_domain_changed(self, event: str, state: dict) -> None:
        if event == "operationFailed":
            return
        old_index = int(self._queue_state.get("current_index", -1))
        new_index = int(state.get("current_index", -1))
        self._queue_state = state
        if event == "currentIndexChanged" and old_index != new_index:
            self._emit_current_changed(old_index, new_index)
        else:
            self.refresh()

    def _emit_current_changed(self, old_index: int, new_index: int) -> None:
        """Emit targeted dataChanged for current index rows without full reset."""
        top = self._page_size if len(self._items) < self._total_count else len(self._items)
        tl = self.index(0, 0)
        br = self.index(max(top - 1, 0), 0)
        self.dataChanged.emit(tl, br, [self.CurrentRole])
        self.countChanged.emit()
        self.totalCountChanged.emit()

    @Slot()
    def _unsubscribe_queue(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def shutdown(self) -> None:
        """Stop observing queue changes before the owning bridge is disposed."""
        self._unsubscribe_queue()

    def _owner(self) -> str:
        return "queue"

    def roleNames(self) -> dict[int, bytes]:
        return {self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.TitleRole: b"title", self.ArtistRole: b"artist",
                self.AlbumRole: b"album", self.AlbumKeyRole: b"albumKey",
                self.DurationRole: b"duration",
                self.CurrentRole: b"current", self.PositionRole: b"position",
                self.CoverKeyRole: b"coverKey", self.SourceTypeRole: b"sourceType"}

    def data(self, index, role=Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.TitleRole: "title", self.ArtistRole: "artist",
                    self.AlbumRole: "album", self.AlbumKeyRole: "album_key",
                    self.DurationRole: "duration",
                    self.CurrentRole: "is_current", self.PositionRole: "position",
                    self.CoverKeyRole: "cover_key", self.SourceTypeRole: "source_type"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self) -> None:
        super().refresh()

    def _fetch_count(self, **kwargs) -> int:
        return len(self._queue_state.get("items", []))

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        queue = self._queue_state.get("items", [])
        page = queue[offset:offset + limit]
        return [self._item_to_dict(item, offset + index)
                for index, item in enumerate(page)]

    def _item_to_dict(self, item: Any, position: int = 0) -> dict[str, Any]:
        current_index = int(self._queue_state.get("current_index", -1))
        return queue_item_from_raw(item, position, current_index).as_dict()
