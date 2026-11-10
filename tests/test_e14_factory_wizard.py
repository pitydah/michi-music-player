"""E14 Factory wizard must leave a failed flash actionable."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi_ecosystem.application.factory_coordinator import FactoryResult
from michi_ecosystem.presentation.stream_factory_bridge import StreamFactoryBridge

ROOT = Path(__file__).resolve().parents[1]


def test_review_button_retries_only_after_a_visible_error() -> None:
    source = (
        ROOT / "src/michi/presentation/qml/ecosystem/factory/StreamFactoryWizard.qml"
    ).read_text()
    assert 'qsTr("Reintentar flasheo")' in source
    assert 'qsTr("Iniciar flasheo")' in source
    assert "streamFactory.errorMessage.length > 0" in source


class _Service:
    pass


class _Orchestrator:
    def __init__(self) -> None:
        self.starts = 0

    def start(self, request: object) -> None:
        self.starts += 1


@pytest.fixture(scope="module")
def qapp():
    qt = pytest.importorskip("PySide6.QtGui")
    app = qt.QGuiApplication.instance()
    if app is None:
        app = qt.QGuiApplication([])
    yield app


def _bridge() -> tuple[StreamFactoryBridge, _Orchestrator]:
    orchestrator = _Orchestrator()
    bridge = StreamFactoryBridge(_Service(), orchestrator=orchestrator)
    bridge.selectDevice("ttyUSB0")
    bridge.setNetwork("Michi", "secret")
    return bridge, orchestrator


def _fail(bridge: StreamFactoryBridge, *, code: str, message: str) -> None:
    bridge._on_finished(
        FactoryResult(
            operation_id="op",
            ok=False,
            cancelled=False,
            error=message,
            error_code=code,
        )
    )


def test_official_firmware_failure_returns_to_review_and_can_retry(qapp) -> None:
    bridge, orchestrator = _bridge()
    bridge.startFlash()
    assert bridge.step == "flashing"
    _fail(
        bridge,
        code="OFFICIAL_FIRMWARE_UNAVAILABLE",
        message="No hay firmware oficial disponible.",
    )
    assert bridge.step == "review"
    assert bridge.stepIndex == 6
    assert bridge.busy is False
    assert bridge.errorTitle == "Firmware oficial no disponible"
    assert bridge.errorHelp
    assert bridge.errorMessage == "No hay firmware oficial disponible."
    assert bridge.selectedPort == "ttyUSB0"
    assert bridge.canStartFlash is True
    bridge.startFlash()
    assert orchestrator.starts == 2
    assert bridge.step == "flashing"


def test_usb_disconnect_returns_to_review_without_losing_inputs(qapp) -> None:
    bridge, _ = _bridge()
    bridge.startFlash()
    _fail(bridge, code="DEVICE_DISCONNECTED", message="La placa se desconectó.")
    assert bridge.step == "review"
    assert bridge.busy is False
    assert bridge.errorMessage == "La placa se desconectó."
    assert bridge.selectedPort == "ttyUSB0"
    assert bridge.step != "flashing"


def test_cancelled_flash_returns_to_intro(qapp) -> None:
    bridge, _ = _bridge()
    bridge.startFlash()
    bridge._on_finished(FactoryResult(operation_id="op", ok=False, cancelled=True))
    assert bridge.step == "intro"
    assert bridge.stepIndex == 0
    assert bridge.errorMessage == ""


def test_flash_failure_is_not_a_terminal_progress_state(qapp) -> None:
    bridge, _ = _bridge()
    bridge.startFlash()
    _fail(bridge, code="FLASH_FAILED", message="Falló la escritura.")
    assert bridge.progressStage == ""
    assert bridge.step == "review"
    assert bridge.errorMessage == "Falló la escritura."
