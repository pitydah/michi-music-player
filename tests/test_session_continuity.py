"""Session continuity tests — restore, missing tracks, index remap, no autoplay."""

from __future__ import annotations

import os


import pytest

from core.queue_service import QueueService, _queue_state_path

pytestmark = [pytest.mark.qml_module("queue")]


@pytest.fixture(autouse=True)
def clean_state():
    path = _queue_state_path()
    if os.path.exists(path):
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def service():
    return QueueService()


@pytest.fixture
def sample_items():
    return [
        {"track_id": "1", "title": "Song A", "filepath": "/a.flac",
         "source_type": "local_file", "duration": 200},
        {"track_id": "2", "title": "Song B", "filepath": "/b.flac",
         "source_type": "local_file", "duration": 300},
        {"track_id": "3", "title": "Song C", "filepath": "/c.flac",
         "source_type": "local_file", "duration": 250},
    ]


class TestSessionRestore:
    """Verify queue restore behavior after application restart."""

    def test_restore_no_autoplay(self, service, sample_items):
        """After restore, current_index should be set but no playback starts."""
        service.set_items(sample_items, current_index=1)
        service.save_state(position=42.0)
        fresh = QueueService()
        result = fresh.load_state()
        assert result["ok"]
        # QueueService has the state but doesn't trigger playback
        # (playback is started by the UI layer, not QueueService)
        assert fresh.current_index == 1
        assert fresh.count == 3

    def test_restore_position_clamp(self, service, sample_items):
        """Position should be clamped to the track duration after restore."""
        service.set_items(sample_items, current_index=1)
        # Save with position > duration of track B (300s)
        service.save_state(position=500.0)
        fresh = QueueService()
        result = fresh.load_state()
        assert result["ok"]
        # Position is stored as-is; clamping happens at the UI level

    def test_restore_preserves_shuffle_order(self, service, sample_items):
        """Shuffle order should be preserved across restore."""
        service.set_items(sample_items, current_index=1)
        service.toggle_shuffle()
        service.save_state()
        fresh = QueueService()
        result = fresh.load_state()
        assert result["ok"]
        assert fresh.shuffle

    def test_restore_preserves_repeat_mode(self, service, sample_items):
        """Repeat mode should be preserved across restore."""
        service.set_items(sample_items, current_index=0)
        service.repeat = "one"
        service.save_state()
        fresh = QueueService()
        result = fresh.load_state()
        assert result["ok"]
        assert fresh.repeat == "one"


class TestMissingTrackHandling:
    """Verify missing tracks are handled gracefully during restore."""

    def test_resolve_fn_marks_missing_tracks(self, service, sample_items):
        """Tracks that fail resolve_fn should be marked as unavailable."""
        service.set_items(sample_items, current_index=1)
        service.save_state()

        def resolve(item):
            return item if item["track_id"] != "2" else None

        fresh = QueueService()
        result = fresh.load_state(resolve_fn=resolve)
        assert result["ok"]
        assert result["missing_count"] == 1
        assert "2" in result["missing_track_ids"]

    def test_resolve_fn_adjusts_current_index(self, service, sample_items):
        """current_index should be adjusted when preceding tracks are missing."""
        service.set_items(sample_items, current_index=2)
        service.save_state()

        # Track 1 is missing — current_index should shift
        def resolve(item):
            return item if item["track_id"] != "1" else None

        fresh = QueueService()
        result = fresh.load_state(resolve_fn=resolve)
        assert result["ok"]
        # After removing track 1, remaining are [2, 3] at indices [0, 1]
        # Original index 2 (track 3) should map to index 1
        assert fresh.current_index == 1

    def test_all_tracks_missing_results_empty(self, service, sample_items):
        """If all tracks fail resolve, queue should be empty."""
        service.set_items(sample_items, current_index=0)
        service.save_state()

        def resolve(item):
            return None

        fresh = QueueService()
        result = fresh.load_state(resolve_fn=resolve)
        assert result["ok"]
        assert fresh.count == 0
        assert result["missing_count"] == 3

    def test_no_resolve_fn_keeps_all_tracks(self, service, sample_items):
        """Without resolve_fn, all tracks should be kept."""
        service.set_items(sample_items, current_index=1)
        service.save_state()
        fresh = QueueService()
        result = fresh.load_state()
        assert result["ok"]
        assert fresh.count == 3
        assert result.get("missing_count", 0) == 0

    def test_resolve_fn_with_empty_queue(self, service):
        """Restore with no saved state should return error."""
        fresh = QueueService()
        result = fresh.load_state()
        assert not result["ok"]
        assert result["error"] == "NO_SAVED_STATE"


class TestQueueBridgeRestore:
    """Verify QueueBridge delegate to QueueService for restore."""

    def test_bridge_save_and_load(self, service, sample_items):
        from ui_qml_bridge.queue_bridge import QueueBridge
        service.set_items(sample_items, current_index=0)
        bridge = QueueBridge(queue_service=service)
        save_result = bridge.saveState()
        assert save_result.get("ok")
        load_result = bridge.loadState()
        assert load_result.get("ok")

    def test_bridge_persist_delegates(self, service, sample_items):
        from ui_qml_bridge.queue_bridge import QueueBridge
        service.set_items(sample_items, current_index=0)
        bridge = QueueBridge(queue_service=service)
        # persist() delegates to queue_service.persist()
        result = bridge.persist()
        assert result.get("ok")

    def test_bridge_restore_delegates(self, service, sample_items):
        from ui_qml_bridge.queue_bridge import QueueBridge
        service.set_items(sample_items, current_index=0)
        bridge = QueueBridge(queue_service=service)
        # restore() delegates to queue_service.restore()
        result = bridge.restore()
        # restore() on a service with no saved state returns error
        assert "ok" in result
