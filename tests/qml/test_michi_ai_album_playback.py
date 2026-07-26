from __future__ import annotations


from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


class TestAlbumPlayback:
    def test_send_message_fails_without_service(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce el álbum Test Album")
        assert bridge.status == "FAILED"

    def test_send_message_no_name(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce el álbum")
        assert bridge.status == "FAILED"

    def test_cancel_works(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce el álbum Test")
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_refresh_does_not_crash(self):
        bridge = MichiAIBridge()
        bridge.refresh()
        assert bridge is not None
