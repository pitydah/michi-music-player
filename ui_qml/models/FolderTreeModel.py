"""FolderTreeModel — lazy-loaded folder tree from LibraryDB."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Property, Signal


class FolderTreeModel(QAbstractListModel):
    dataChanged = Signal()
    loadingChanged = Signal()

    PathRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    TrackCountRole = Qt.UserRole + 3
    IsExpandableRole = Qt.UserRole + 4
    ExpandedRole = Qt.UserRole + 5

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._folders: list[dict[str, Any]] = []
        self._loading = False

    def roleNames(self):
        return {
            self.PathRole: b"folderPath",
            self.NameRole: b"folderName",
            self.TrackCountRole: b"trackCount",
            self.IsExpandableRole: b"isExpandable",
            self.ExpandedRole: b"expanded",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._folders)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._folders):
            return None
        item = self._folders[index.row()]
        mapping = {
            self.PathRole: "path",
            self.NameRole: "name",
            self.TrackCountRole: "track_count",
            self.IsExpandableRole: "is_expandable",
            self.ExpandedRole: "expanded",
        }
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        return None

    @Property(int, notify=dataChanged)
    def count(self):
        return len(self._folders)

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    def refresh(self):
        self._loading = True
        self.loadingChanged.emit()
        folders = []
        if self._db and hasattr(self._db, 'conn'):
            try:
                rows = self._db.conn.execute(
                    "SELECT DISTINCT COALESCE(directory, ''), COUNT(*) as cnt "
                    "FROM media_items WHERE deleted_at IS NULL AND COALESCE(directory, '') != '' "
                    "GROUP BY directory ORDER BY directory LIMIT 500"
                ).fetchall()
                for r in rows:
                    path = r[0]
                    folders.append({
                        "path": path, "name": path.rsplit("/", 1)[-1] if "/" in path else path,
                        "track_count": r[1], "is_expandable": True, "expanded": False,
                    })
            except Exception:
                pass
        self.beginResetModel()
        self._folders = folders
        self.endResetModel()
        self._loading = False
        self.loadingChanged.emit()
        self.dataChanged.emit()
