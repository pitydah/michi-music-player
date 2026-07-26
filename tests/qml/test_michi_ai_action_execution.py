from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import AI_STATES, MichiAIBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def services() -> None:
    svc = {
        "michi_ai_service": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
        "job_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "capability_bridge": MagicMock(),
        "page_state_store": MagicMock(),
        "accessibility_bridge": MagicMock(),
    }
    svc["michi_ai_service"].process_message.return_value = {"ok": True, "response": "OK"}
    return svc


@pytest.fixture
def bridge(services) -> None:
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        job_service=services["job_service"],
        confirmation_service=services["confirmation_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
        capability_bridge=services["capability_bridge"],
        page_state_store=services["page_state_store"],
        accessibility_bridge=services["accessibility_bridge"],
    )


class TestStates:
    def test_initial_state(self, bridge) -> None:
        assert bridge.status == "IDLE"

    def test_valid_states(self, bridge) -> None:
        for s in AI_STATES:
            bridge._set_status(s)
            assert bridge.status == s

    def test_invalid_state_ignored(self, bridge) -> None:
        bridge._set_status("IDLE")
        bridge._set_status("bogus")
        assert bridge.status == "IDLE"


class TestActionExecution:
    def test_reproducir_cancion(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 42")
        services["michi_ai_service"].process_message.assert_called_once()

    def test_reproducir_album(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo álbum..."
        }
        bridge.sendMessage("reproduce el álbum Abbey Road")
        assert bridge.status == "SUCCEEDED"

    def test_encolar(self, bridge, services) -> None:
        bridge.sendMessage("encolar canción 7")
        services["michi_ai_service"].process_message.assert_called_once()

    def test_buscar(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Resultados encontrados"
        }
        bridge.sendMessage("buscar rock progresivo")
        assert bridge.status == "SUCCEEDED"

    def test_abrir_ruta(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Navegando..."
        }
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_abrir_ajustes(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Abriendo ajustes..."
        }
        bridge.sendMessage("abrir ajustes")
        assert bridge.status == "SUCCEEDED"

    def test_crear_playlist_requires_confirmation(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "crear playlist"
        }
        bridge.sendMessage("crear playlist")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_confirm_creates_playlist(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "crear playlist"},
            {"ok": True, "response": "Playlist creada."},
        ]
        bridge.sendMessage("crear playlist")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_cancel_aborts_action(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "crear playlist"},
            {"ok": True, "response": "Cancelado."},
        ]
        bridge.sendMessage("crear playlist")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("no")
        assert bridge.status == "SUCCEEDED"

    def test_diagnosticar(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Diagnóstico completo."
        }
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_cambiar_ajuste_confirmado(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "cambiar ajuste"},
            {"ok": True, "response": "Ajuste aplicado."},
        ]
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_unknown_action_returns_fallback(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "No entendí esa solicitud."
        }
        bridge.sendMessage("qué hora es")
        assert bridge.status == "FAILED"
        assert len(bridge._chat_history) >= 2

    def test_engine_error_returns_failed(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = Exception("Engine error")
        bridge.sendMessage("reproduce canción")
        assert bridge.status == "FAILED"


class TestCancel:
    def test_cancel_clears_pending(self, bridge) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.cancel()
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_cancel_during_confirmation(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "crear playlist"
        }
        bridge.sendMessage("crear playlist")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.cancel()
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_cancel_idempotent(self, bridge) -> None:
        bridge.cancel()
        assert bridge.status == "CANCELLED"
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_cancel_command(self, bridge) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_cancel_detener(self, bridge) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.sendMessage("detener")
        assert bridge.status == "CANCELLED"

    def test_cancel_parar(self, bridge) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.sendMessage("parar")
        assert bridge.status == "CANCELLED"


class TestScore:
    def test_score_includes_all_services(self, bridge, services) -> None:
        score = bridge.aiScore()
        assert score["score"] > 0
        assert score["has_ai_service"] is True
        assert score["has_registry"] is True
        assert score["has_nav"] is True
        assert score["has_job"] is True

    def test_score_no_services(self) -> None:
        minimal = MichiAIBridge()
        score = minimal.aiScore()
        assert score["score"] >= 5
