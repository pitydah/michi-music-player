"""M9 QML foundation regression guards and smoke tests."""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path("src/michi/presentation/qml").resolve()


def _load_qml(path: str, name: str) -> QQmlComponent:
    """Load a QML file and assert it compiles + instantiates."""
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine, str(QML_DIR / path))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{name}: {errs}"
    obj = component.create()
    assert obj is not None, f"{name}: null object"
    obj.deleteLater()
    return component


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestRoutedViewRootsNoAnchorsFill:
    @staticmethod
    def _root_has_anchors(path: str) -> bool:
        content = Path(path).read_text()
        lines = content.split("\n")
        root_depth = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Find the root element (first non-import line)
            if stripped and not stripped.startswith("import") and root_depth is None:
                root_depth = 0
                # Count braces on the root line itself, then scan children
                root_depth = lines[i].count("{") - lines[i].count("}")
                for j in range(i + 1, len(lines)):
                    js = lines[j]
                    if not js.strip():
                        continue
                    # Track brace depth
                    root_depth += js.count("{")
                    root_depth -= js.count("}")
                    if "anchors.fill" in js and root_depth <= 1:
                        return True
                    if root_depth < 0:
                        break
                return False
        return False

    def test_now_playing_root(self):
        assert not self._root_has_anchors(
            "src/michi/presentation/qml/views/NowPlayingView.qml"
        )

    def test_library_root(self):
        assert not self._root_has_anchors(
            "src/michi/presentation/qml/views/LibraryView.qml"
        )

    def test_queue_root(self):
        assert not self._root_has_anchors(
            "src/michi/presentation/qml/views/QueueView.qml"
        )

    def test_settings_view_root(self):
        assert not self._root_has_anchors(
            "src/michi/presentation/qml/views/SettingsView.qml"
        )

    def test_settings_placeholder_removed(self):
        assert not Path(
            "src/michi/presentation/qml/views/SettingsPlaceholder.qml"
        ).exists()

    def test_sidebar_no_hardcoded_delegate_id(self):
        content = Path("src/michi/presentation/qml/shell/Sidebar.qml").read_text()
        assert "delegate: itemDelegate" not in content

    def test_settings_view_ownership(self):
        content = Path("src/michi/presentation/qml/views/SettingsView.qml").read_text()
        assert "playback.volume" in content
        assert "playback.set_volume" in content
        assert "library.currentDir" in content
        # M6.9-PRESENTATION: the ONLY settings mutation the view performs
        # is the Online Library Enrichment policy switch; geometry/theme
        # mutations stay out of the view.
        assert "settingsBridge.set_theme" not in content
        assert "settingsBridge.set_window_geometry" not in content
        assert "settingsBridge.set_online_enrichment" in content


class TestQmlSmoke:
    def test_michi_button(self, qapp):
        _load_qml("ui/MichiButton.qml", "MichiButton")

    def test_michi_text_field(self, qapp):
        _load_qml("ui/MichiTextField.qml", "MichiTextField")

    def test_michi_panel(self, qapp):
        _load_qml("ui/MichiPanel.qml", "MichiPanel")

    def test_michi_slider(self, qapp):
        _load_qml("ui/MichiSlider.qml", "MichiSlider")

    def test_shell(self, qapp):
        _load_qml("shell/AppShell.qml", "AppShell")

    def test_michi_glass_surface(self, qapp):
        _load_qml("primitives/MichiGlassSurface.qml", "MichiGlassSurface")

    def test_michi_focus_ring(self, qapp):
        _load_qml("primitives/MichiFocusRing.qml", "MichiFocusRing")

    def test_michi_status_chip(self, qapp):
        _load_qml("primitives/MichiStatusChip.qml", "MichiStatusChip")

    def test_michi_icon_button(self, qapp):
        _load_qml("controls/MichiIconButton.qml", "MichiIconButton")

    def test_michi_search_field(self, qapp):
        _load_qml("controls/MichiSearchField.qml", "MichiSearchField")

    def test_artwork(self, qapp):
        _load_qml("media/Artwork.qml", "Artwork")

    def test_ui_gallery(self, qapp):
        _load_qml("dev/MichiUIGallery.qml", "MichiUIGallery")

    def test_michi_entity_row(self, qapp):
        _load_qml("media/MichiEntityRow.qml", "MichiEntityRow")

    def test_michi_album_row(self, qapp):
        _load_qml("media/MichiAlbumRow.qml", "MichiAlbumRow")

    def test_queue_panel(self, qapp):
        _load_qml("components/QueuePanel.qml", "QueuePanel")

    def test_now_playing_bar(self, qapp):
        _load_qml("player/NowPlayingBar.qml", "NowPlayingBar")


def test_now_playing_bar_preserves_landmarks_in_responsive_layout(qapp):
    """The canonical landmarks remain present without fixed x coordinates."""
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine, str(QML_DIR / "player/NowPlayingBar.qml"))
    errs = "; ".join(error.toString() for error in component.errors())
    assert component.status() == QQmlComponent.Ready, errs
    root = component.create()
    assert root is not None
    root.setProperty("width", 1920)
    root.setProperty("height", 154)
    qapp.processEvents()

    assert root.property("width") == 1920
    assert root.property("height") == 154
    assert root.property("compact") is False
    assert root.property("narrow") is False
    for object_name in (
        "trackCard",
        "trackArtwork",
        "playbackZone",
        "timeline",
        "playPauseButton",
        "outputZone",
        "queueButton",
        "volumeSlider",
        "qualityBadge",
        "outputDeviceButton",
        "audioEngineIndicator",
    ):
        item = root.findChild(QObject, object_name)
        assert item is not None, object_name

    qml = (QML_DIR / "player/NowPlayingBar.qml").read_text()
    assert "RowLayout" in qml
    assert "transportOrigin" not in qml
    assert "x: root.width" not in qml

    root.deleteLater()
