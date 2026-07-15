"""Tests for Mix v12 — no generacion sincrona, usa MixService + JobService."""
from unittest.mock import MagicMock, patch

import pytest


class TestMixBridgeCreation:
    def test_requires_playback_service(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        with pytest.raises(Exception):
            MixBridge()

    def test_creation_with_playback(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        assert mb is not None

    def test_state_default(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        assert mb.stateName == "IDLE"

    def test_categories(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        cats = mb.categories
        assert len(cats) > 0

    def test_current_songs_default(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        assert len(mb.currentSongs) == 0


class TestMixOperations:
    def test_configure(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.configure("favorites")
        assert result.get("ok")

    def test_configure_unknown(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.configure("nonexistent")
        assert not result.get("ok")

    def test_validate(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock(), mix_service=MagicMock())
        mb.configure("favorites")
        result = mb.validate()
        assert isinstance(result, dict)

    def test_reset(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        mb.configure("favorites")
        result = mb.reset()
        assert result.get("ok")
        assert mb.stateName == "IDLE"

    def test_play_mix_empty(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.playMix()
        assert not result.get("ok")

    def test_enqueue_mix_empty(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.enqueueMix()
        assert not result.get("ok")

    def test_explain_empty(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.explainCurrentMix()
        assert not result.get("ok")

    def test_play_from_index_empty(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.playFromIndex(0)
        assert not result.get("ok")

    def test_enqueue_track_empty(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.enqueueTrack(0)
        assert not result.get("ok")

    def test_save_mix_as_playlist_empty(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.saveMixAsPlaylist("Test")
        assert not result.get("ok")

    def test_refresh(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.refresh()
        assert isinstance(result, dict)

    def test_regenerate(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock())
        result = mb.regenerate()
        assert isinstance(result, dict)

    def test_uses_mix_service(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(playback_service=MagicMock(), mix_service=MagicMock())
        assert mb._mix_svc is not None
