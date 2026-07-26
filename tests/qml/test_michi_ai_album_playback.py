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


class TestAlbumPlayback:
    def test_play_album_sends_to_engine(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo álbum..."
        }
        bridge.sendMessage("reproduce el álbum Test Album")
        services["michi_ai_service"].process_message.assert_called_once()
        assert bridge.status == "SUCCEEDED"

    def test_play_album_not_found(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "Álbum no encontrado"
        }
        bridge.sendMessage("reproduce el álbum NoSuchAlbum")
        assert bridge.status == "FAILED"

    def test_play_album_no_name(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "Nombre de álbum requerido"
        }
        bridge.sendMessage("reproduce el álbum")
        assert bridge.status == "FAILED"

    def test_play_album_ambiguous(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Múltiples álbumes encontrados."
        }
        bridge.sendMessage("reproduce el álbum Album")
        assert bridge.status == "SUCCEEDED"

    def test_play_album_no_service(self) -> None:
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce el álbum Test")
        assert bridge.status == "FAILED"

    def test_play_album_parses_correctly(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "Dark Side no encontrado"
        }
        bridge.sendMessage("reproduce el álbum Dark Side")
        assert bridge.status == "FAILED"
