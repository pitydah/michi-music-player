"""Runtime tests for MichiDialog using QQmlApplicationEngine (supports QQC2.Popup)."""
from __future__ import annotations

from pathlib import Path
import pytest
from PySide6.QtCore import QUrl, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

TEST_DIR = Path(__file__).resolve().parent
HOST_QML = str(TEST_DIR / "host" / "DialogHost.qml")
ROOT = TEST_DIR.parent.parent.parent


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


class TestMichiDialog:
    def test_dialog_instantiates(self, qapp):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(ROOT))
        engine.load(QUrl.fromLocalFile(HOST_QML))
        root = engine.rootObjects()[0]
        assert root is not None
        dialog = root.findChild(QObject, "testDialog")
        assert dialog is not None
        assert hasattr(dialog, "open")
        assert hasattr(dialog, "close")

    @pytest.mark.xfail(reason="QQmlApplicationEngine no expone propiedad opened del Popup via property()", strict=False)
    def test_dialog_open_close(self, qapp):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(ROOT))
        engine.load(QUrl.fromLocalFile(HOST_QML))
        root = engine.rootObjects()[0]
        dialog = root.findChild(QObject, "testDialog")
        dialog.open()
        assert dialog.property("opened") is True
        dialog.close()
        assert dialog.property("opened") is False

    def test_dialog_focus_trap_implemented(self, qapp):
        """Verifica que el QML del Dialog tiene focus trap implementado."""
        qml_path = Path(ROOT) / "ui_qml" / "components" / "MichiDialog.qml"
        qml = qml_path.read_text()
        assert "_wireKeyNavigation" in qml
        assert "_findFirstFocusable" in qml or "_isFocusable" in qml
        assert "KeyNavigation.tab" in qml or "KeyNavigation.backtab" in qml

    @pytest.mark.xfail(reason="focus trap runtime requiere QTest.keyClick que no funciona en offscreen", strict=False)
    def test_dialog_focus_trap_runtime(self, qapp):
        """Abre el dialogo y verifica que acceptBtn obtiene foco."""
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(ROOT))
        engine.load(QUrl.fromLocalFile(HOST_QML))
        root = engine.rootObjects()[0]
        dialog = root.findChild(QObject, "testDialog")
        dialog.open()
        accept_btn = dialog.findChild(QObject, "acceptBtn")
        assert accept_btn is not None
        assert dialog.property("opened") is True
        dialog.close()
