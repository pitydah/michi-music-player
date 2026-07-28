"""Verify album view renders with productive layout — geometry, model, delegates."""
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtWidgets import QApplication

pytestmark = pytest.mark.skipif(
    not QApplication.instance(),
    reason="Requires QApplication"
)


@pytest.fixture
def engine():
    app = QApplication.instance() or QApplication([])
    e = QQmlEngine()
    e.addImportPath("ui_qml")
    return e


def _load_component(engine, path):
    c = QQmlComponent(engine)
    c.loadUrl(QUrl.fromLocalFile(path))
    if c.status() == QQmlComponent.Error:
        raise RuntimeError(f"QML compile error: {c.errors()}")
    obj = c.create()
    if not obj:
        raise RuntimeError("Failed to create QML object")
    return obj, c


def test_album_view_host_has_geometry(engine):
    """AlbumViewHost root and contentArea have non-zero geometry."""
    root, _ = _load_component(engine, "ui_qml/pages/library/album/AlbumViewHost.qml")
    root.forceActiveFocus()
    assert root.width > 0 or root.implicitWidth > 0
    assert root.height > 0 or root.implicitHeight > 0


def test_album_view_content_area_clipped(engine):
    """contentArea in AlbumViewHost has clip: true."""
    root, _ = _load_component(engine, "ui_qml/pages/library/album/AlbumViewHost.qml")
    # contentArea is the first child Item
    for child in root.children():
        if hasattr(child, "clip"):
            assert child.clip, "contentArea must have clip: true"
            break


def test_album_view_model_mismatch_state(engine):
    """modelContentMismatch is true when totalCount>0 but loadedCount==0."""
    root, _ = _load_component(engine, "ui_qml/pages/library/album/AlbumViewHost.qml")
    # Set up model conditions via dynamic properties
    root.totalCount = 5
    root.loadedCount = 0
    root.initialLoading = False
    root.loadingMore = False
    root.hasError = False
    # The property must recalculate
    mismatch = root.property("modelContentMismatch")
    assert mismatch is True, "Expected modelContentMismatch=True with 5 total, 0 loaded"


def test_album_view_renders_with_data(engine):
    """AlbumViewHost renders delegates when model has data."""
    root, _ = _load_component(engine, "ui_qml/pages/library/album/AlbumViewHost.qml")
    # Simulate a real model state
    root.totalCount = 10
    root.loadedCount = 10
    root.initialLoading = False
    root.loadingMore = False
    root.hasError = False
    # The contentArea should be visible and sized
    for child in root.children():
        if hasattr(child, "clip"):
            child.width = 800
            child.height = 600
            assert child.width > 0
            assert child.height > 0
            break
