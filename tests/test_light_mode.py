"""Verify light mode doesn't break UI loading."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parents[1] / "ui_qml"


def _load_qml(engine: QQmlEngine, relative_path: str) -> QQmlComponent:
    engine.addImportPath(str(QML_DIR))
    c = QQmlComponent(engine)
    c.loadUrl(QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    return c


@pytest.fixture(autouse=True)
def mock_singletons(monkeypatch):
    monkeypatch.setattr(
        "PySide6.QtQml.qmlRegisterSingletonInstance",
        lambda *a, **kw: None,
    )


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def test_theme_has_light_mode_switch(qapp) -> None:
    content = (QML_DIR / "theme/MichiTheme.qml").read_text()
    assert "setDarkMode" in content
    assert "darkMode" in content
    assert "MichiColors.lightMode" in content


def test_theme_motion_references_exist(qapp) -> None:
    content = (QML_DIR / "theme/MichiTheme.qml").read_text()
    assert "motionFast" in content
    assert "motionNormal" in content
    assert "motionSlow" in content


def test_colors_have_light_and_dark_variants(qapp) -> None:
    content = (QML_DIR / "theme/MichiColors.qml").read_text()
    assert "lightMode" in content
    assert "light" in content.lower()
    assert "dark" in content.lower()


def test_page_loads_in_qml_engine(engine) -> None:
    component = _load_qml(engine, "pages/SettingsPage.qml")
    assert component.isReady(), component.errorString()


def test_home_page_loads(engine) -> None:
    component = _load_qml(engine, "pages/home/HomePage.qml")
    assert component.isReady(), component.errorString()


def test_library_page_loads(engine) -> None:
    component = _load_qml(engine, "pages/library/LibraryPage.qml")
    assert component.isReady(), component.errorString()


def test_settings_page_no_errors(engine) -> None:
    component = _load_qml(engine, "pages/SettingsPage.qml")
    assert component.isReady(), component.errorString()
