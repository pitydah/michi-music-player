from unittest.mock import MagicMock
from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge


class TestOutputProfilesBridge:
    def test_create(self):
        bridge = OutputProfilesBridge(player_service=MagicMock())
        assert bridge is not None


class TestSetActiveProfileRealResults:
    """The bridge must propagate real service results, never fabricate success."""

    def _make(self, player):
        bridge = OutputProfilesBridge(player_service=player)
        bridge._active_id = "standard"
        return bridge

    def test_propagates_verified_and_state(self):
        player = MagicMock()
        player.get_active_profile_id.return_value = "standard"
        player.set_profile.return_value = {
            "ok": True, "verified": True, "persisted": True,
            "state": "persisted", "active_profile": "hifi_pcm",
            "active_backend": "gstreamer", "fallback": False,
        }
        bridge = self._make(player)
        result = bridge.setActiveProfile("hifi_pcm")
        assert result["ok"] is True
        assert result["verified"] is True
        assert result["state"] == "persisted"
        assert result["active_backend"] == "gstreamer"
        assert bridge.activeProfileId == "hifi_pcm"

    def test_no_fabrication_on_non_dict_result(self):
        player = MagicMock()
        player.get_active_profile_id.return_value = "standard"
        player.set_profile.return_value = True  # not a dict -> must not fabricate ok=True
        bridge = self._make(player)
        result = bridge.setActiveProfile("hifi_pcm")
        assert result["ok"] is False
        assert result["active_profile"] == "standard"

    def test_propagates_rollback_flag(self):
        player = MagicMock()
        player.get_active_profile_id.return_value = "standard"
        player.set_profile.return_value = {
            "ok": False, "code": "VERIFY_FAILED", "rollback": True,
            "error": "VERIFY_FAILED", "active_profile": "standard",
            "active_backend": "gstreamer", "fallback": False,
        }
        bridge = self._make(player)
        result = bridge.setActiveProfile("michi_hifi_mpd")
        assert result["ok"] is False
        assert result["rollback"] is True
        assert result["active_profile"] == "standard"

    def test_resolve_backend_reads_real_preferred_backend(self):
        bridge = self._make(MagicMock())
        # Real production profiles are dataclasses — must read the real attribute.
        assert bridge._resolve_backend("michi_hifi_mpd") == "mpd"
        assert bridge._resolve_backend("unknown_profile") == "gstreamer"
