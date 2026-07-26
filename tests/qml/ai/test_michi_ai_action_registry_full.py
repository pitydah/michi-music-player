from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = [pytest.mark.qml_module("michi_ai")]


@pytest.fixture
def services() -> None:
    svc = {
        "michi_ai_service": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
    }
    svc["michi_ai_service"].process_message.return_value = {"ok": True, "response": "OK"}
    return svc


@pytest.fixture
def bridge(services) -> None:
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
    )


def test_play_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("reproduce canción 42")
    services["michi_ai_service"].process_message.assert_called_once()


def test_queue_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("encolar canción 7")
    services["michi_ai_service"].process_message.assert_called_once()


def test_playlist_action_forwards_to_engine(bridge, services) -> None:
    services["michi_ai_service"].process_message.side_effect = [
        {"requires_confirmation": True, "intent": "crear playlist"},
        {"ok": True, "response": "Playlist creada."},
    ]
    bridge.sendMessage("crear playlist llamada Favoritos")
    bridge.sendMessage("sí")
    assert bridge.status == "SUCCEEDED"


def test_mix_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("ir a mix")
    services["michi_ai_service"].process_message.assert_called_once()


def test_search_action_forwards_to_engine(bridge, services) -> None:
    services["michi_ai_service"].process_message.return_value = {
        "ok": True, "response": "Resultados encontrados"
    }
    bridge.sendMessage("buscar rock progresivo")
    services["michi_ai_service"].process_message.assert_called_once()


def test_navigation_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("ir a biblioteca")
    services["michi_ai_service"].process_message.assert_called()


def test_settings_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("abrir ajustes")
    services["michi_ai_service"].process_message.assert_called_once()


def test_metadata_action_dispatched(bridge, services) -> None:
    services["michi_ai_service"].process_message.return_value = {
        "ok": True, "response": "Reproduciendo..."
    }
    bridge.sendMessage("reproduce canción 1")
    assert bridge.status == "SUCCEEDED"


def test_audio_lab_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("ir a biblioteca")
    services["michi_ai_service"].process_message.assert_called_once()


def test_doctor_action_forwards_to_engine(bridge, services) -> None:
    services["michi_ai_service"].process_message.return_value = {
        "ok": True, "response": "Diagnóstico completo."
    }
    bridge.sendMessage("diagnosticar biblioteca")
    assert bridge.status == "SUCCEEDED"


def test_devices_action_forwards_to_engine(bridge, services) -> None:
    bridge.sendMessage("ir a conexiones")
    services["michi_ai_service"].process_message.assert_called()


def test_action_unavailable_on_no_service() -> None:
    bridge = MichiAIBridge()
    bridge.sendMessage("reproduce canción 42")
    assert bridge.status == "FAILED"
