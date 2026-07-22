"""QueueListModel — BasePagedListModel observing the canonical QueueService."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal, Slot

from ui_qml.models.BasePagedListModel import BasePagedListModel


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
        self._queue_state = state
        self.refresh()

    @Slot()
    def _unsubscribe_queue(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def _owner(self) -> str:
        return "queue"

    def roleNames(self) -> dict:
        return {self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.TitleRole: b"title", self.ArtistRole: b"artist",
                self.AlbumRole: b"album", self.AlbumKeyRole: b"albumKey",
                self.DurationRole: b"duration",
                self.CurrentRole: b"current", self.PositionRole: b"position"}

    def data(self, index, role=Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.TitleRole: "title", self.ArtistRole: "artist",
                   self.AlbumRole: "album", self.AlbumKeyRole: "album_key",
                   self.DurationRole: "duration",
                   self.CurrentRole: "is_current", self.PositionRole: "position"}
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

    def _item_to_dict(self, item: Any, position: int = 0) -> dict:
        current_index = int(self._queue_state.get("current_index", -1))
        if isinstance(item, dict):
            return {
                "track_id": item.get("id", item.get("track_id", 0)),
                "track_uid": item.get("track_uid", ""),
                "title": item.get("title", ""),
                "artist": item.get("artist", ""),
                "album": item.get("album", ""),
                "album_key": item.get("album_key", ""),
                "duration": item.get("duration", 0),
                "is_current": position == current_index,
                "position": position,
            }
        return {
            "track_id": getattr(item, "id", getattr(item, "track_id", 0)),
            "track_uid": getattr(item, "track_uid", ""),
            "title": getattr(item, "title", ""),
            "artist": getattr(item, "artist", ""),
            "album": getattr(item, "album", ""),
            "album_key": getattr(item, "album_key", ""),
            "duration": getattr(item, "duration", 0),
            "is_current": position == current_index,
            "position": position,
        }
