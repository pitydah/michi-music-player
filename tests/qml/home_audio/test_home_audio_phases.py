"""Contracts for Home Audio roadmap phases 3 through 7."""

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parents[3] / "ui_qml"
HOME_AUDIO_DIR = QML_DIR / "pages" / "home_audio"
pytestmark = pytest.mark.isolation


@pytest.fixture
def engine(qapp) -> QQmlEngine:
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_DIR))
    return qml_engine


@pytest.mark.parametrize(
    "filename",
    ["GroupEditorPage.qml", "HomeAssistantPanel.qml", "DiagnosticsPage.qml"],
)
def test_phase_page_loads(engine, filename) -> None:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(HOME_AUDIO_DIR / filename)))

    assert component.isReady(), component.errorString()


def test_group_editor_uses_receiver_bridge_contract() -> None:
    source = (HOME_AUDIO_DIR / "GroupEditorPage.qml").read_text(encoding="utf-8")

    assert "homeAudioBridge.receiverList" in source
    assert "createGroup(root.groupName, root.selectedReceiverIds)" in source
    assert "updateGroup(root.groupId, root.groupName, root.selectedReceiverIds)" in source
    assert "function routeEnter(route, params)" in source


def test_home_assistant_form_passes_host_port_and_token() -> None:
    source = (HOME_AUDIO_DIR / "HomeAudioPage.qml").read_text(encoding="utf-8")

    assert "configureHa(host, port, token)" in source


def test_home_assistant_panel_supports_discovery_entity_selection_and_live_state() -> None:
    source = (HOME_AUDIO_DIR / "HomeAssistantPanel.qml").read_text(encoding="utf-8")

    for contract in (
        "discoverHomeAssistantInstances",
        "homeAssistantInstances",
        "bridge.devices",
        "selectedEntityIds",
        "importHomeAssistantEntities",
        "haWebSocketConnected",
        "modelData.state",
    ):
        assert contract in source


def test_setup_wizard_wires_home_assistant_panel_actions() -> None:
    source = (HOME_AUDIO_DIR / "SetupWizardPage.qml").read_text(encoding="utf-8")

    assert "onConfigureClicked" in source
    assert "root.ha.configureHa(host, port, token)" in source
    assert "onDisconnectClicked" in source
    assert "root.ha.disconnectHa()" in source


def test_diagnostics_page_exposes_required_operational_status() -> None:
    source = (HOME_AUDIO_DIR / "DiagnosticsPage.qml").read_text(encoding="utf-8")

    for contract in (
        "snapserverState",
        "fifoExists",
        "fifoWritable",
        "fifoSize",
        "activeStreams",
        "connectedReceivers",
        "lastError",
        "latency_ms",
        "testTone",
    ):
        assert contract in source
