from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QModelIndex, Qt

from library.folder_tree_model import FolderTreeModel


def test_folder_tree_exposes_roots_and_lazy_sorted_children(tmp_path: Path) -> None:
    root = tmp_path / "Music"
    root.mkdir()
    (root / "Zulu").mkdir()
    (root / "alpha").mkdir()
    (root / ".cache").mkdir()
    model = FolderTreeModel([str(root)])

    root_index = model.index(0, 0, QModelIndex())
    assert model.rowCount() == 1
    assert model.data(root_index, Qt.DisplayRole) == "Music"
    assert model.canFetchMore(root_index) is True

    model.fetchMore(root_index)

    assert model.rowCount(root_index) == 2
    assert [
        model.data(model.index(row, 0, root_index), Qt.DisplayRole)
        for row in range(model.rowCount(root_index))
    ] == ["alpha", "Zulu"]
    child_index = model.index(0, 0, root_index)
    assert model.parent(child_index) == root_index
    assert model.data(child_index, model.PathRole) == str(root / "alpha")


def test_folder_tree_marks_unreadable_node_loaded_without_children(tmp_path: Path) -> None:
    root = tmp_path / "Music"
    root.mkdir()
    model = FolderTreeModel([str(root)])
    root_index = model.index(0, 0)

    with patch("library.folder_tree_model.os.scandir", side_effect=PermissionError):
        model.fetchMore(root_index)

    assert model.rowCount(root_index) == 0
    assert model.canFetchMore(root_index) is False
