"""Verify UI works at different scales."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parents[1] / "ui_qml"


@pytest.fixture(autouse=True)
def mock_singletons(monkeypatch):
    monkeypatch.setattr(
        "PySide6.QtQml.qmlRegisterSingletonInstance",
        lambda *a, **kw: None,
    )


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


PAGES = [
    "pages/SettingsPage.qml",
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
]


@pytest.mark.parametrize("scale", ["1.0", "1.25", "1.5", "1.75", "2.0"])
@pytest.mark.parametrize("page", PAGES)
def test_page_loads_at_scale(engine, scale, page):
    os.environ["QT_SCALE_FACTOR"] = scale
    engine.addImportPath(str(QML_DIR))
    c = QQmlComponent(engine)
    c.loadUrl(QUrl.fromLocalFile(str(QML_DIR / page)))
    assert c.isReady(), f"Scale {scale}, {page}: {c.errorString()}"
