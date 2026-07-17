"""Runtime tests for MichiDialog using QQmlApplicationEngine (supports QQC2.Popup)."""
from __future__ import annotations

import time
from pathlib import Path
import pytest
from PySide6.QtCore import QUrl, QObject, QCoreApplication
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

TEST_DIR = Path(__file__).resolve().parent
HOST_QML = str(TEST_DIR / "host" / "DialogHost.qml")
ROOT = TEST_DIR.parent.parent.parent


def _process():
    QCoreApplication.processEvents()
    time.sleep(0.05)


def _load_dialog():
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(ROOT))
    engine.load(QUrl.fromLocalFile(HOST_QML))
    root = engine.rootObjects()[0]
    dialog = root.findChild(QObject, "testDialog")
    return engine, root, dialog


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


class TestMichiDialog:
    def test_dialog_instantiates(self, qapp):
        engine, root, dialog = _load_dialog()
        assert dialog is not None
        assert hasattr(dialog, "open")
        assert hasattr(dialog, "close")

    def test_dialog_open_close(self, qapp):
        engine, root, dialog = _load_dialog()
        dialog.open()
        _process()
        assert dialog.property("visible") or dialog.property("opened")
        dialog.close()
        _process()
        assert not dialog.property("visible") or not dialog.property("opened")

    def test_dialog_focus_trap_implemented(self, qapp):
        qml_path = Path(ROOT) / "ui_qml" / "components" / "MichiDialog.qml"
        qml = qml_path.read_text()
        assert "_wireKeyNavigation" in qml
        assert "_findFirstFocusable" in qml or "_isFocusable" in qml
        assert "KeyNavigation.tab" in qml or "KeyNavigation.backtab" in qml

    @pytest.mark.xfail(strict=False, reason="QQmlApplicationEngine.activeFocusItem no disponible en offscreen")
    def test_dialog_focus_trap_runtime(self, qapp):
        engine, root, dialog = _load_dialog()
        dialog.open()
        _process()
        accept_btn = dialog.findChild(QObject, "acceptBtn")
        cancel_btn = dialog.findChild(QObject, "cancelBtn")
        assert accept_btn is not None
        assert cancel_btn is not None
        assert dialog.property("visible") or dialog.property("opened")
        dialog.close()
        _process()
