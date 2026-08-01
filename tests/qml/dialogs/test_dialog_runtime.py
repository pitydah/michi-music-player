from __future__ import annotations

"""Runtime tests for canonical dialogs (P0 regression).

Locks in the fixes for:
- content/buttons reparenting (dialog content must render in the visual tree)
- Escape/Enter handling (reject/accept)
- defaultTitle resolution (no self-referencing titleText bindings)
- enum close-policy constants (CloseOnEscape / CloseOnClickOutside)
- FocusTrap tab cycling inside the dialog
"""

import sys
from pathlib import Path

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets", reason="PySide6 widgets required")
from PySide6.QtCore import QUrl, Qt  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

pytestmark = pytest.mark.isolation

REPO_ROOT = Path(__file__).resolve().parents[3]
DIALOGS_URL = (REPO_ROOT / "ui_qml/components/dialogs").as_uri()


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    yield app


@pytest.fixture()
def engine(qapp):
    return QQmlEngine(qapp)


def _create_window(engine, qml: str):
    component = QQmlComponent(engine)
    component.setData(qml.encode(), QUrl("file:///dialog_runtime_test.qml"))
    assert component.isReady(), component.errorString()
    window = component.create()
    assert window is not None
    # Prevent the QML engine GC from deleting the C++ object mid-test.
    QQmlEngine.setObjectOwnership(window, QQmlEngine.ObjectOwnership.CppOwnership)
    # The QML context dies with the component; keep it alive for the window.
    window._test_component = component
    return window


def _find(obj, object_name: str):
    try:
        if obj.objectName() == object_name:
            return obj
        children = obj.children()
    except RuntimeError:
        return None  # C++ object already deleted (leftover from a previous test)
    for child in children:
        found = _find(child, object_name)
        if found is not None:
            return found
    return None


def _find_text(item, text: str) -> bool:
    try:
        if item.property("text") == text:
            return True
    except Exception:
        pass
    children = item.childItems() if hasattr(item, "childItems") else item.children()
    return any(_find_text(child, text) for child in children)


class TestConfirmDialogRuntime:
    QML = f"""
    import QtQuick
    import QtQuick.Window
    import "{DIALOGS_URL}" as D

    Window {{
        width: 640; height: 480
        property int confirmedCount: 0
        property int cancelledCount: 0

        D.ConfirmDialog {{
            id: dlg
            objectName: "ConfirmDialog"
            titleText: "Borrar algo"
            message: "Mensaje de prueba visible"
            onConfirmed: confirmedCount++
            onCancelled: cancelledCount++
        }}
    }}
    """

    def test_message_content_renders_when_open(self, engine, qapp):
        window = _create_window(engine, self.QML)
        dlg = _find(window, "ConfirmDialog")
        assert dlg is not None
        dlg.setProperty("open", True)
        qapp.processEvents()
        assert _find_text(dlg, "Mensaje de prueba visible"), (
            "dialog content is not part of the rendered visual tree"
        )
        window.deleteLater()

    def test_escape_rejects(self, engine, qapp):
        window = _create_window(engine, self.QML)
        window.show()
        dlg = _find(window, "ConfirmDialog")
        dlg.setProperty("open", True)
        qapp.processEvents()
        dlg.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(window, Qt.Key_Escape)
        qapp.processEvents()
        assert dlg.property("open") is False
        assert window.property("cancelledCount") == 1
        window.deleteLater()

    def test_enter_accepts(self, engine, qapp):
        window = _create_window(engine, self.QML)
        window.show()
        dlg = _find(window, "ConfirmDialog")
        dlg.setProperty("open", True)
        qapp.processEvents()
        dlg.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(window, Qt.Key_Return)
        qapp.processEvents()
        assert dlg.property("open") is False
        assert window.property("confirmedCount") == 1
        window.deleteLater()

    def test_close_policy_enum_constants(self, engine, qapp):
        window = _create_window(engine, self.QML)
        dlg = _find(window, "ConfirmDialog")
        assert dlg.property("closeOnEscape") == 1
        assert dlg.property("closeOnClickOutside") == 2
        assert dlg.property("closeOnEscapeOrClickOutside") == 3
        assert dlg.property("closePolicy") == 1
        window.deleteLater()

    def test_default_title_resolves(self, engine, qapp):
        qml = f"""
        import QtQuick
        import QtQuick.Window
        import "{DIALOGS_URL}" as D

        Window {{
            width: 640; height: 480
            D.ConfirmDialog {{
                objectName: "ConfirmDialog"
                message: "x"
                open: true
            }}
        }}
        """
        window = _create_window(engine, qml)
        qapp.processEvents()
        dlg = _find(window, "ConfirmDialog")
        assert dlg.property("titleText") == ""
        assert dlg.property("defaultTitle") != ""
        assert _find_text(dlg, dlg.property("defaultTitle"))
        window.deleteLater()

    def test_focus_trap_cycles_focus(self, engine, qapp):
        window = _create_window(engine, self.QML)
        window.show()
        dlg = _find(window, "ConfirmDialog")
        dlg.setProperty("open", True)
        qapp.processEvents()
        cancel_btn = _find(dlg, "confirmDialogCancelButton")
        confirm_btn = _find(dlg, "confirmDialogConfirmButton")
        assert cancel_btn is not None and confirm_btn is not None

        def focused_name():
            for btn in (cancel_btn, confirm_btn):
                try:
                    if btn.property("activeFocus"):
                        return btn.objectName()
                except RuntimeError:
                    pass
            return ""

        QTest.keyClick(window, Qt.Key_Tab)
        qapp.processEvents()
        first = focused_name()
        assert first != "", "focus trap must move focus inside the dialog"
        QTest.keyClick(window, Qt.Key_Backtab)
        qapp.processEvents()
        second = focused_name()
        assert second != ""
        assert second != first, "focus trap must cycle between dialog controls"
        window.deleteLater()


class TestDestructiveDialogRuntime:
    def test_confirm_disabled_until_keyword(self, engine, qapp):
        qml = f"""
        import QtQuick
        import QtQuick.Window
        import "{DIALOGS_URL}" as D

        Window {{
            width: 640; height: 480
            D.DestructiveDialog {{
                objectName: "destructiveDialog"
                message: "Vas a borrar cosas"
                keyword: "BORRAR"
                open: true
            }}
        }}
        """
        window = _create_window(engine, qml)
        qapp.processEvents()
        dlg = _find(window, "destructiveDialog")
        assert dlg.property("_keywordMatched") is False
        assert dlg.property("closePolicy") == 1
        assert dlg.property("defaultTitle") != ""
        window.deleteLater()
