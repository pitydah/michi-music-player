from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation


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


class TestSettingsKeys:
    def test_volume_change_sends_to_engine(self, bridge, services) -> None:
        bridge.sendMessage("cambiar ajuste volumen a 80")
        services["michi_ai_service"].process_message.assert_called_once()

    def test_theme_change_sends_to_engine(self, bridge, services) -> None:
        bridge.sendMessage("cambiar ajuste tema oscuro")
        services["michi_ai_service"].process_message.assert_called_once()

    def test_setting_change_requires_confirmation_via_engine(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "cambiar ajuste"
        }
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_setting_change_confirm_executes_via_engine(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "cambiar ajuste"},
            {"ok": True, "response": "Ajuste aplicado."},
        ]
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_setting_change_fails_via_engine(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "No se pudo cambiar el ajuste."
        }
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "FAILED"

    def test_setting_no_ai_service(self) -> None:
        bridge = MichiAIBridge()
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "FAILED"
        assert bridge.lastError == "NO_AI_SERVICE"
