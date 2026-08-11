"""M9 QML foundation regression guards and smoke tests."""

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestRoutedViewRootsNoAnchorsFill:
    def test_now_playing_root_no_anchors(self):
        content = Path(
            "src/michi/presentation/qml/views/NowPlayingView.qml"
        ).read_text()
        lines = content.split("\n")
        in_root = False
        brace_depth = 0
        for line in lines:
            stripped = line.strip()
            if "{ColumnLayout" in stripped or "ColumnLayout {" in stripped:
                in_root = True
            if in_root and "{" in stripped:
                brace_depth += stripped.count("{")
            if in_root and "}" in stripped:
                brace_depth -= stripped.count("}")
            if in_root and brace_depth <= 2 and "anchors.fill" in stripped:
                pytest.fail(f"Root has anchors.fill: {stripped}")
            if in_root and brace_depth == 0 and "}" in stripped:
                break

    def test_library_root_no_anchors(self):
        content = Path("src/michi/presentation/qml/views/LibraryView.qml").read_text()
        lines = content.split("\n")
        in_root = False
        brace_depth = 0
        for line in lines:
            stripped = line.strip()
            if "MichiPanel {" in stripped:
                in_root = True
            if in_root and "{" in stripped:
                brace_depth += stripped.count("{")
            if in_root and "}" in stripped:
                brace_depth -= stripped.count("}")
            if in_root and brace_depth <= 1 and "anchors.fill" in stripped:
                pytest.fail(f"Root has anchors.fill: {stripped}")
            if in_root and brace_depth == 0 and "}" in stripped:
                break

    def test_queue_root_no_anchors(self):
        content = Path("src/michi/presentation/qml/views/QueueView.qml").read_text()
        lines = content.split("\n")
        in_root = False
        brace_depth = 0
        for line in lines:
            stripped = line.strip()
            if "{ColumnLayout" in stripped or "ColumnLayout {" in stripped:
                in_root = True
            if in_root and "{" in stripped:
                brace_depth += stripped.count("{")
            if in_root and "}" in stripped:
                brace_depth -= stripped.count("}")
            if in_root and brace_depth <= 2 and "anchors.fill" in stripped:
                pytest.fail(f"Root has anchors.fill: {stripped}")
            if in_root and brace_depth == 0 and "}" in stripped:
                break


class TestQmlComponentsLoad:
    def test_theme_singleton_imports(self, qapp):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(Path("src/michi/presentation/qml").resolve()))
        # Load a minimal QML that imports the theme
        component = (
            'import QtQuick; import "theme"; '
            "QtObject { property color c: MichiTheme.accent }"
        )
        obj = None
        engine.objectCreated.connect(lambda o, _: None)
        engine.loadData(component.encode(), QUrl())
        engine.clearComponentCache()

    def test_primitives_smoke(self, qapp):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(Path("src/michi/presentation/qml").resolve()))
        primitives = [
            ('import QtQuick; import "ui"; MichiButton {}', "MichiButton"),
            ('import QtQuick; import "ui"; MichiTextField {}', "MichiTextField"),
            ('import QtQuick; import "ui"; MichiPanel {}', "MichiPanel"),
        ]
        for source, _name in primitives:
            engine.loadData(source.encode(), QUrl())
        engine.clearComponentCache()

    def test_shell_loads(self, qapp):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(Path("src/michi/presentation/qml").resolve()))
        engine.loadData(b'import QtQuick; import "shell"; AppShell {}', QUrl())
        engine.clearComponentCache()
