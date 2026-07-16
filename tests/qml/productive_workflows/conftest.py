"""V13 productive workflows — use real QGuiApplication + QQmlApplicationEngine.

Fakes only at external boundaries (FakeAudioBackend, FakeNetworkTransport,
FakeMtpAdapter). No Fake*Bridge classes.
"""

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
    from ui_qml_bridge.bridge_factory import BridgeFactory
    factory = BridgeFactory(bs.container)
    bs._bridges = factory.create_all()
    return bs


@pytest.fixture(scope="module")
def engine(bootstrap):
    engine = QQmlApplicationEngine()
    bridges = bootstrap.create_bridges()
    from ui_qml_bridge.context_registrar import ContextRegistrar
    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    registrar = ContextRegistrar(engine)
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        bridge = bridges.get(bridge_key)
        if bridge is not None:
            registrar.register(qml_name, bridge)
    bootstrap.register_context(engine)
    engine.addImportPath("ui_qml")
    yield engine
    engine.deleteLater()


@pytest.fixture
def page_state(bootstrap):
    return bootstrap.container.get("page_state") if hasattr(bootstrap, "container") else None
