"""Keyboard navigation — QML component test."""
from __future__ import annotations

import pytest
from PySide6.QtQml import QQmlEngine, QQmlComponent
from pathlib import Path


@pytest.fixture
def engine():
    eng = QQmlEngine()
    eng.addImportPath(str(Path(__file__).resolve().parent.parent.parent / "ui_qml"))
    return eng


class TestKeyboardNavigation:
    def test_michi_button_keyboard_ready(self, engine):
        c = QQmlComponent(engine, str(
            Path(__file__).resolve().parent.parent.parent / "ui_qml" / "components" / "MichiButton.qml"
        ))
        assert c.status() == QQmlComponent.Ready, f"MichiButton: {c.errorString()}"

    def test_action_button_keyboard_ready(self, engine):
        c = QQmlComponent(engine, str(
            Path(__file__).resolve().parent.parent.parent / "ui_qml" / "components" / "ActionButton.qml"
        ))
        assert c.status() == QQmlComponent.Ready, f"ActionButton: {c.errorString()}"
