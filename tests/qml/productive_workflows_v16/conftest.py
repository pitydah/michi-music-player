"""V16 productive workflows conftest."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from core.application_bootstrap import ApplicationBootstrap


@pytest.fixture(scope="module")
def qml_app():
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


@pytest.fixture(scope="module")
def bootstrap():
    bs = ApplicationBootstrap()
    bs.build()
    bs.start()
    return bs


@pytest.fixture(scope="module")
def bridges(bootstrap):
    return bootstrap.create_bridges()


@pytest.fixture
def engine(bootstrap, bridges):
    engine = QQmlApplicationEngine()
    from ui_qml_bridge.context_registrar import ContextRegistrar
    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    registrar = ContextRegistrar(engine)
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        b = bridges.get(bridge_key)
        if b is not None:
            registrar.register(qml_name, b)
    engine.addImportPath("ui_qml")
    yield engine
    engine.deleteLater()
