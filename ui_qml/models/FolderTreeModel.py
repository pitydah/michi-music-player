"""FolderTreeModel — BasePagedListModel for folder browsing via QueryService."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from ui_qml.models.BasePagedListModel import BasePagedListModel


class FolderTreeModel(BasePagedListModel):
    PathRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    TrackCountRole = Qt.UserRole + 3
    IsExpandableRole = Qt.UserRole + 4
    ExpandedRole = Qt.UserRole + 5

    def __init__(self, query_service=None, query_executor=None, parent=None):
        super().__init__(page_size=200, query_executor=query_executor, parent=parent)
        self._qs = query_service

    def roleNames(self):
        return {self.PathRole: b"folderPath", self.NameRole: b"folderName",
                self.TrackCountRole: b"trackCount",
                self.IsExpandableRole: b"isExpandable", self.ExpandedRole: b"expanded"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.PathRole: "path", self.NameRole: "name",
                   self.TrackCountRole: "track_count",
                   self.IsExpandableRole: "is_expandable", self.ExpandedRole: "expanded"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        return None

    def refresh(self, parent_path: str = ""):
        self._parent_path = parent_path
        super().refresh(parent_path=parent_path)

    def _fetch_count(self, **kwargs) -> int:
        if not self._qs:
            return 0
        parent_path = kwargs.get("parent_path", "")
        return self._qs.count_folders(parent_path=parent_path)

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._qs:
            return []
        parent_path = kwargs.get("parent_path", "")
        return self._qs.fetch_folders(parent_path=parent_path, offset=offset, limit=limit)
