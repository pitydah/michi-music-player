"""FolderTreeModel — hierarchical folder browser model."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal


class FolderNode:
    """One lazily loaded directory in the folder tree."""

    def __init__(self, path: str, name: str, parent: FolderNode | None = None) -> None:
        self.path = path
        self.name = name
        self.parent = parent
        self.children: list[FolderNode] = []
        self._loaded = False

    def appendChild(self, child: FolderNode) -> None:  # noqa: N802 - Qt model convention
        self.children.append(child)


class FolderTreeModel(QAbstractItemModel):
    """Expose configured library roots as a lazy hierarchical Qt model."""

    PathRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    ErrorRole = Qt.UserRole + 3

    errorOccurred = Signal(str, str)  # path, error_message

    def __init__(
        self,
        root_paths: list[str] | None = None,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._root_nodes = [
            FolderNode(path, Path(path).name or path)
            for path in (root_paths or [])
        ]

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt API
        return {self.PathRole: b"path", self.NameRole: b"name"}

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        del parent
        return 1

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid() and parent.column() != 0:
            return 0
        node = self._get_node(parent)
        return len(node.children) if node is not None else len(self._root_nodes)

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),
    ) -> QModelIndex:
        if row < 0 or column != 0:
            return QModelIndex()
        parent_node = self._get_node(parent)
        children = parent_node.children if parent_node is not None else self._root_nodes
        if row >= len(children):
            return QModelIndex()
        return self.createIndex(row, column, children[row])

    def parent(self, index: QModelIndex) -> QModelIndex:
        node = self._get_node(index)
        if node is None or node.parent is None:
            return QModelIndex()
        parent_node = node.parent
        grandparent = parent_node.parent
        siblings = grandparent.children if grandparent is not None else self._root_nodes
        return self.createIndex(siblings.index(parent_node), 0, parent_node)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        node = self._get_node(index)
        if node is None:
            return None
        if role in {Qt.DisplayRole, self.NameRole}:
            return node.name
        if role == self.PathRole:
            return node.path
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:  # noqa: N802
        if not parent.isValid():
            return bool(self._root_nodes)
        node = self._get_node(parent)
        return bool(node and (not node._loaded or node.children))

    def canFetchMore(self, parent: QModelIndex) -> bool:  # noqa: N802
        node = self._get_node(parent)
        return bool(node and not node._loaded)

    def fetchMore(self, parent: QModelIndex) -> None:  # noqa: N802
        node = self._get_node(parent)
        if node is None or node._loaded:
            return
        try:
            with os.scandir(node.path) as entries:
                children = sorted(
                    (
                        FolderNode(entry.path, entry.name, node)
                        for entry in entries
                        if entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".")
                    ),
                    key=lambda child: child.name.casefold(),
                )
        except (OSError, PermissionError) as exc:
            self.errorOccurred.emit(node.path, str(exc))
            children = []
        node._loaded = True
        if not children:
            return
        self.beginInsertRows(parent, 0, len(children) - 1)
        for child in children:
            node.appendChild(child)
        self.endInsertRows()

    @staticmethod
    def _get_node(index: QModelIndex) -> FolderNode | None:
        if not index.isValid():
            return None
        node = index.internalPointer()
        return node if isinstance(node, FolderNode) else None
