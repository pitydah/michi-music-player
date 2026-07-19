from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine


def test_distribution_page_uses_bridge_models_and_real_actions():
    qml = Path("ui_qml/pages/home_audio/DistributionHubPage.qml").read_text(
        encoding="utf-8"
    )

    for model in (
        "bridge.sources",
        "bridge.servers",
        "bridge.receiverList",
        "bridge.destinations",
        "bridge.routes",
    ):
        assert model in qml

    for action in (
        "startServer",
        "stopServer",
        "discoverReceivers",
        "createRoute",
        "startRoute",
        "stopRoute",
        "retryRoute",
        "updateRoute",
        "deleteRoute",
    ):
        assert action in qml

    assert 'navigationBridge.navigate("home_audio")' not in qml


def test_distribution_page_instantiates_without_snapcast(qtbot):
    path = Path("ui_qml/pages/home_audio/DistributionHubPage.qml").resolve()
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
    assert component.isReady(), [error.toString() for error in component.errors()]
    instance = component.create()
    assert instance is not None
    instance.deleteLater()
    engine.deleteLater()
