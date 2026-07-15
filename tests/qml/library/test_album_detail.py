"""Tests for AlbumDetailPage — album detail, multi-disc, play."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge

pytestmark = [pytest.mark.qml_module("album_views")]


class TestAlbumDetail:
    @pytest.fixture
    def bridge(self):
        qs = MagicMock()
        qs.fetch_album_detail.return_value = {
            "title": "Test Album",
            "artist": "Test Artist",
            "year": 2024,
            "genre": "Rock",
            "disc_count": 2,
            "compilation": True,
            "missing_count": 1,
        }
        qs.fetch_album_tracks_internal.return_value = [
            {"track_id": 1, "title": "Track 1", "artist": "Test Artist",
             "album_key": "ak1", "filepath": "/m/s1.flac",
             "duration": 200, "format": "FLAC", "disc_number": 1,
             "track_number": 1, "bit_depth": 24, "missing": False},
            {"track_id": 2, "title": "Track 2", "artist": "Test Artist",
             "album_key": "ak1", "filepath": "/m/s2.flac",
             "duration": 180, "format": "FLAC", "disc_number": 1,
             "track_number": 2, "bit_depth": 24, "missing": False},
            {"track_id": 3, "title": "Track 3", "artist": "Test Artist",
             "album_key": "ak1", "filepath": "/m/s3.flac",
             "duration": 220, "format": "FLAC", "disc_number": 2,
             "track_number": 1, "bit_depth": 24, "missing": False},
        ]
        return LibraryBridge(query_service=qs)

    def test_album_detail_loads(self, bridge):
        detail = bridge.getAlbumDetail("ak1")
        assert detail["ok"] is True
        assert detail["title"] == "Test Album"
        assert detail["artist"] == "Test Artist"
        assert detail["year"] == 2024
        assert detail["genre"] == "Rock"

    def test_album_detail_disc_count(self, bridge):
        detail = bridge.getAlbumDetail("ak1")
        assert detail["disc_count"] == 2

    def test_album_compilation_detected(self, bridge):
        detail = bridge.getAlbumDetail("ak1")
        assert detail["compilation"] is True

    def test_album_missing_tracks(self, bridge):
        detail = bridge.getAlbumDetail("ak1")
        assert detail["missing_count"] == 1

    def test_album_tracks(self, bridge):
        tracks = bridge.getAlbumTracks("ak1")
        assert len(tracks) == 3
        assert tracks[0]["title"] == "Track 1"

    def test_multi_disc_tracks(self, bridge):
        tracks = bridge.getAlbumTracks("ak1")
        disc1 = [t for t in tracks if t["disc_number"] == 1]
        disc2 = [t for t in tracks if t["disc_number"] == 2]
        assert len(disc1) == 2
        assert len(disc2) == 1

    def test_play_album(self, bridge):
        pb = MagicMock()
        bridge._playback_ctrl = pb
        result = bridge.playAlbum("ak1")
        assert result["ok"] is True
        assert result["count"] == 3

    def test_enqueue_album(self, bridge):
        pb = MagicMock()
        bridge._playback_ctrl = pb
        result = bridge.enqueueAlbum("ak1")
        assert result["ok"] is True
        assert result["count"] == 3

    def test_album_detail_not_found(self):
        qs = MagicMock()
        qs.fetch_album_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getAlbumDetail("nonexistent")
        assert result["ok"] is False

    def test_album_detail_no_query_service(self):
        bridge = LibraryBridge()
        result = bridge.getAlbumDetail("ak1")
        assert result["ok"] is False

    def test_album_disc_button_states(self, bridge):
        detail = bridge.getAlbumDetail("ak1")
        assert detail["disc_count"] > 1

    def test_album_track_count(self, bridge):
        tracks = bridge.getAlbumTracks("ak1")
        assert len(tracks) == 3

    def test_play_single_disc_track(self, bridge):
        tracks = bridge.getAlbumTracks("ak1")
        disc1 = [t for t in tracks if t["disc_number"] == 1]
        assert len(disc1) == 2
        pb = MagicMock()
        bridge._playback_ctrl = pb
        bridge.playTrackById(disc1[0]["track_id"])

    def test_album_detail_empty_qs_tracks(self):
        qs = MagicMock()
        qs.fetch_album_tracks_internal.return_value = []
        bridge = LibraryBridge(query_service=qs)
        tracks = bridge.getAlbumTracks("empty")
        assert tracks == []

    def test_album_details_compilation_artist_shown(self, bridge):
        detail = bridge.getAlbumDetail("ak1")
        assert detail["compilation"] is True
        tracks = bridge.getAlbumTracks("ak1")
        for t in tracks:
            assert "artist" in t
