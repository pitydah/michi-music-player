"""V17 productive workflows — validates real backend, no mocks."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from core.application_bootstrap import ApplicationBootstrap


@pytest.fixture(scope="module")
def qml_app():
    yield QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture(scope="module")
def bootstrap():
    bs = ApplicationBootstrap()
    bs.build()
    bs.start()
    ps = bs.container.get("playback_service")
    engine = getattr(ps, 'engine', None) or getattr(ps, '_engine', None) if ps else None
    assert engine is not None, "playback_service must have a real engine"
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
