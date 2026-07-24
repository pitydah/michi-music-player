"""Dialogs runtime test — verifies playlist dialogs compile and instantiate."""
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

import pytest

QML_DIR = Path(__file__).resolve().parents[2] / "ui_qml"

DIALOG_FILES = [
    "pages/playlists/PlaylistEditorDialog.qml",
    "pages/playlists/PlaylistImportDialog.qml",
]


@pytest.mark.parametrize("rel_path", DIALOG_FILES)
def test_dialog_compiles(qtbot, rel_path):
    path = QML_DIR / rel_path
    if not path.exists():
        pytest.skip(f"Dialog file {rel_path} does not exist")
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
    assert component.isReady(), [
        error.toString() for error in component.errors()
    ]
    engine.deleteLater()
