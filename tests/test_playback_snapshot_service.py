"""Unit tests for the canonical PlaybackSnapshotService and PlayerBarService."""
from __future__ import annotations

from core.playback_snapshot_service import (
    AVAILABLE,
    SERVICE_UNAVAILABLE,
    PlaybackSnapshotService,
)
from core.player_bar_service import PlayerBarService


class FakePlayerSnapshot:
    """PlayerService with a controllable get_playback_snapshot."""

    def __init__(self, snapshot: dict | None = None,
                 raise_on_read: bool = False):
        self._snapshot = snapshot
        self._raise = raise_on_read

    def get_playback_snapshot(self):
        if self._raise:
            raise RuntimeError("engine read failed")
        return self._snapshot


class TestPlaybackSnapshotService:
    def test_no_player_is_explicit_unavailable(self):
        svc = PlaybackSnapshotService(player_service=None)
        snap = svc.snapshot()
        assert snap["available"] is False
        assert snap["status"] == SERVICE_UNAVAILABLE
        assert snap["volume"] is None
        assert snap["position"] is None
        assert snap["track"] is None
        assert svc.get_state() == "unavailable"
        assert svc.get_volume() is None
        assert svc.get_position() is None
        health = svc.health()
        assert health["available"] is False
        assert "player_missing" in health["reasons"]

    def test_read_failure_is_explicit_unavailable(self):
        player = FakePlayerSnapshot(raise_on_read=True)
        svc = PlaybackSnapshotService(player_service=player)
        snap = svc.snapshot()
        assert snap["available"] is False
        assert snap["status"] == SERVICE_UNAVAILABLE
        assert snap["volume"] is None

    def test_playing_snapshot_derived_from_backend(self):
        snap = {
            "backend_id": "gstreamer",
            "state": "playing",
            "current_path": "/music/a.flac",
            "title": "Tema A",
            "artist": "Artista",
            "album": "Álbum",
            "position_seconds": 12.5,
            "duration_seconds": 180.0,
            "volume": 40,
            "queue_index": 2,
            "queue_length": 10,
        }
        svc = PlaybackSnapshotService(player_service=FakePlayerSnapshot(snap))
        result = svc.snapshot()
        assert result["available"] is True
        assert result["status"] == AVAILABLE
        assert result["state"] == "playing"
        assert result["position"] == 12.5
        assert result["volume"] == 40
        assert result["track"] == {
            "title": "Tema A", "artist": "Artista", "album": "Álbum",
            "filepath": "/music/a.flac"}
        assert result["queue"] == {"active": True, "count": 10, "index": 2}
        assert result["source"] == "local"
        assert svc.get_state() == "playing"
        assert svc.get_volume() == 40
        assert svc.get_position() == 12.5

    def test_radio_source_label(self):
        snap = {"backend_id": "gstreamer", "state": "playing",
                "current_uri": "http://radio.example/x", "queue_length": 0}
        svc = PlaybackSnapshotService(player_service=FakePlayerSnapshot(snap))
        assert svc.snapshot()["source"] == "radio"

    def test_mpd_source_label(self):
        snap = {"backend_id": "mpd", "state": "playing",
                "current_path": "/music/a.flac", "queue_length": 4}
        svc = PlaybackSnapshotService(player_service=FakePlayerSnapshot(snap))
        assert svc.snapshot()["source"] == "mpd"

    def test_empty_track_is_none(self):
        snap = {"backend_id": "gstreamer", "state": "stopped",
                "current_path": "", "current_uri": "", "title": "",
                "artist": "", "album": "", "queue_length": 0}
        svc = PlaybackSnapshotService(player_service=FakePlayerSnapshot(snap))
        assert svc.snapshot()["track"] is None


class TestPlayerBarFacade:
    def test_no_player_no_invented_values(self):
        svc = PlayerBarService(player_service=None)
        assert svc.get_state() == "unavailable"
        assert svc.get_volume() is None
        assert svc.get_position() is None
        assert svc.available is False
        health = svc.health()
        assert health["available"] is False
        assert health["status"] == SERVICE_UNAVAILABLE

    def test_delegates_to_snapshot_service(self):
        snap = {"backend_id": "gstreamer", "state": "paused",
                "current_path": "/a.flac", "position_seconds": 5.0,
                "volume": 60, "queue_length": 3}
        snapshot_svc = PlaybackSnapshotService(
            player_service=FakePlayerSnapshot(snap))
        bar = PlayerBarService(snapshot_service=snapshot_svc)
        assert bar.available is True
        assert bar.get_state() == "paused"
        assert bar.get_volume() == 60
        assert bar.get_position() == 5.0
        assert bar.get_snapshot()["queue"]["count"] == 3

    def test_player_service_compat_constructor(self):
        bar = PlayerBarService(player_service=FakePlayerSnapshot(None))
        assert bar.available is True
        assert bar.get_state() == "unavailable"  # snapshot read returned None
