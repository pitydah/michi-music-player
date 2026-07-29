from __future__ import annotations

from pathlib import Path


QML_LIBRARY = Path(__file__).resolve().parents[3] / "ui_qml" / "pages" / "library"


def test_collections_page_uses_collection_service_contract() -> None:
    source = (QML_LIBRARY / "CollectionsPage.qml").read_text(encoding="utf-8")

    assert "createCollection(" in source
    assert "deleteCollection(" in source
    assert "queryCollection(" in source


def test_folder_browser_uses_hierarchical_tree_model() -> None:
    source = (QML_LIBRARY / "FolderBrowserPage.qml").read_text(encoding="utf-8")
    tree = (QML_LIBRARY / "FolderTreeView.qml").read_text(encoding="utf-8")

    assert "folderTreeModel" in source
    assert "TreeView {" in tree
    assert "toggleExpanded" in tree
