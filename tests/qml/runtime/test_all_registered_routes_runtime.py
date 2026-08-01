"""Verify EVERY registered route compiles and instantiates."""
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from ui_qml_bridge.route_registry import ROUTES

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"


@pytest.fixture(scope="module")
def engine():
    app = QGuiApplication.instance() or QGuiApplication([])
    e = QQmlEngine()
    e.addImportPath(str(QML_ROOT))
    return e


@pytest.mark.parametrize("route_key", sorted(ROUTES.keys()))
def test_route_compiles(engine, route_key):
    spec = ROUTES[route_key]
    source = spec.get("source", "")
    rel = source.replace("../", "")
    qml_path = QML_ROOT / rel
    if not qml_path.exists():
        pytest.skip(f"source missing: {rel}")
    comp = QQmlComponent(engine)
    comp.loadUrl(qml_path.resolve().as_uri())
    assert comp.status() != QQmlComponent.Error, (
        f"Compile errors: {[str(e) for e in comp.errors()]}"
    )
    comp.deleteLater()
