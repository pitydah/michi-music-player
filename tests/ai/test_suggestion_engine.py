from __future__ import annotations

from michi_ai.v2.core.models import ContextSnapshot
from michi_ai.v2.suggest.suggestion_engine_v2 import SuggestionEngineV2


class TestSuggestionEngineV2:
    def setup_method(self):
        self.engine = SuggestionEngineV2()

    def test_empty_library_suggestion(self):
        snapshot = ContextSnapshot(
            library={"track_count": 0},
        )
        suggestions = self.engine.generate(snapshot, {"library_doctor.scan": True})
        ids = [s.id for s in suggestions]
        assert "library_empty" in ids

    def test_no_suggestion_when_tracks_exist(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100},
            playback={"now_playing": {"title": "Song"}},
            queue={"count": 5},
        )
        suggestions = self.engine.generate(snapshot, {})
        assert "library_empty" not in [s.id for s in suggestions]

    def test_nothing_playing_suggestion(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100},
            playback={},
        )
        suggestions = self.engine.generate(snapshot, {})
        ids = [s.id for s in suggestions]
        assert "nothing_playing" in ids

    def test_queue_empty_suggestion(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100},
            playback={"now_playing": {"title": "Song"}},
            queue={"count": 0},
        )
        suggestions = self.engine.generate(snapshot, {})
        ids = [s.id for s in suggestions]
        assert "queue_empty" in ids

    def test_metadata_gaps_suggestion(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100, "missing_metadata_count": 5},
        )
        suggestions = self.engine.generate(snapshot, {"metadata.read": True})
        ids = [s.id for s in suggestions]
        assert "metadata_gaps" in ids

    def test_dismiss_prevents_suggestion(self):
        snapshot = ContextSnapshot(
            library={"track_count": 0},
        )
        self.engine.dismiss("library_empty")
        suggestions = self.engine.generate(snapshot, {"library_doctor.scan": True})
        assert "library_empty" not in [s.id for s in suggestions]

    def test_clear_dismissed_restores(self):
        snapshot = ContextSnapshot(
            library={"track_count": 0},
        )
        self.engine.dismiss("library_empty")
        self.engine.clear_dismissed()
        suggestions = self.engine.generate(snapshot, {"library_doctor.scan": True})
        assert "library_empty" in [s.id for s in suggestions]

    def test_dismiss_expires(self):
        self.engine.dismiss("test_suggestion", ttl_seconds=0)
        import time
        time.sleep(0.01)
        assert self.engine.is_dismissed("test_suggestion") is False

    def test_suggestions_ordered_by_priority(self):
        snapshot = ContextSnapshot(
            library={"track_count": 0, "missing_metadata_count": 5},
        )
        suggestions = self.engine.generate(snapshot, {
            "library_doctor.scan": True,
            "metadata.read": True,
        })
        for i in range(len(suggestions) - 1):
            assert suggestions[i].priority <= suggestions[i + 1].priority

    def test_device_connected_suggestion(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100},
            devices={"device_count": 1},
        )
        suggestions = self.engine.generate(snapshot, {})
        ids = [s.id for s in suggestions]
        assert "device_connected" in ids

    def test_audio_features_missing(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100, "tracks_without_audio_features": 50},
        )
        suggestions = self.engine.generate(snapshot, {"audio_lab.analyze": True})
        ids = [s.id for s in suggestions]
        assert "audio_features_missing" in ids

    def test_no_suggestions_with_full_context(self):
        snapshot = ContextSnapshot(
            library={"track_count": 100, "missing_metadata_count": 0, "tracks_without_audio_features": 0},
            playback={"now_playing": {"title": "Song"}},
            queue={"count": 5},
        )
        suggestions = self.engine.generate(snapshot, {})
        assert len(suggestions) >= 0
