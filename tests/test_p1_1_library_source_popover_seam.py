"""P1.1 regression gate for the productive Library source popover seam."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _ManualPipeline:
    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        self.cancelled.append(generation)


def _world(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(FilesystemLibrarySourceScanner(), library_prefs=_Prefs())
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    pipeline = _ManualPipeline()
    lifecycle = SourceScanLifecycle(coordinator, pipeline)
    bridge = LibraryBridge(
        library,
        source_coordinator=coordinator,
        source_scan_lifecycle=lifecycle,
    )
    return coordinator, pipeline, bridge


def _load(engine, rel):
    component = QQmlComponent(engine, str(QML_DIR / rel))
    errors = "; ".join(error.toString() for error in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{rel}: {errors}"
    obj = component.create()
    engine._keepalive = getattr(engine, "_keepalive", []) + [component]
    return obj


def test_popover_uses_native_qml_url_boundary():
    source = Path(QML_DIR / "views" / "LibrarySourcePopover.qml").read_text()

    assert "import QtQuick.Dialogs" in source
    assert "QUrl.fromLocalFile" not in source
    assert "library.currentDir" not in source
    assert "folderDialog.selectedFolder" in source
    assert (
        "library.add_and_scan_music_source_url(folderDialog.selectedFolder)" in source
    )


def test_folder_dialog_acceptance_routes_to_one_modern_worker(qapp, tmp_path):
    """REAL QML accepted() → Bridge QUrl slot → SourceScanLifecycle worker."""
    coordinator, pipeline, bridge = _world(tmp_path)
    music_root = tmp_path / "Music #1 % colección 日本語"
    music_root.mkdir(parents=True)
    (music_root / "a.flac").write_bytes(b"x")

    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("library", bridge)
    toolbar = _load(engine, "views/LibraryToolbar.qml")

    folder_dialog = toolbar.findChild(QObject, "librarySourceFolderDialog")
    assert folder_dialog is not None, "real LibrarySourcePopover FolderDialog missing"

    selected_folder = QUrl.fromLocalFile(str(music_root))
    assert selected_folder.isLocalFile()
    assert folder_dialog.setProperty("selectedFolder", selected_folder)

    meta = folder_dialog.metaObject()
    accepted_index = meta.indexOfSignal("accepted()")
    assert accepted_index >= 0, "FolderDialog.accepted() signal missing"
    meta.method(accepted_index).invoke(folder_dialog)
    qapp.processEvents()

    sources = coordinator.list_sources()
    assert len(sources) == 1
    assert Path(sources[0].root_path) == music_root
    assert len(pipeline.submissions) == 1

    engine.deleteLater()
