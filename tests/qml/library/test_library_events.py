from __future__ import annotations

from dataclasses import fields
from core.library.events import (
    TrackAdded, TrackUpdated, TrackRemoved, TrackMissingChanged,
    FavoriteChanged, PlayCountChanged, AlbumChanged, ArtistChanged,
    SourceChanged, ScanStarted, ScanProgress, ScanFinished,
    MetadataWritten, ArtworkChanged, PlaylistChanged, QueueChanged,
)


class TestLibraryEvents:
    def test_track_added(self):
        e = TrackAdded(track_id=1, track_uid="uid1", source_id=42)
        assert e.track_id == 1
        assert e.track_uid == "uid1"
        assert e.source_id == 42

    def test_track_added_default(self):
        e = TrackAdded(track_id=1, track_uid="uid1")
        assert e.source_id is None

    def test_track_updated(self):
        e = TrackUpdated(track_id=1, fields_changed=["title", "artist"])
        assert e.track_id == 1
        assert "title" in e.fields_changed

    def test_track_removed(self):
        e = TrackRemoved(track_id=5)
        assert e.track_id == 5

    def test_track_missing_changed(self):
        e = TrackMissingChanged(track_id=3, is_missing=True)
        assert e.is_missing is True

    def test_favorite_changed(self):
        e = FavoriteChanged(track_id=2, is_favorite=False)
        assert e.is_favorite is False

    def test_play_count_changed(self):
        e = PlayCountChanged(track_id=1, play_count=42)
        assert e.play_count == 42

    def test_album_changed(self):
        e = AlbumChanged(album_key="key1", fields_changed=["title"])
        assert e.album_key == "key1"

    def test_artist_changed(self):
        e = ArtistChanged(artist_name="Artist X")
        assert e.artist_name == "Artist X"

    def test_source_changed(self):
        e = SourceChanged(source_id=1, status="scanning")
        assert e.status == "scanning"

    def test_scan_started(self):
        e = ScanStarted(source_id=1)
        assert e.source_id == 1

    def test_scan_progress(self):
        e = ScanProgress(source_id=1, progress=0.5, current_file="song.flac")
        assert e.progress == 0.5
        assert e.current_file == "song.flac"

    def test_scan_finished(self):
        e = ScanFinished(source_id=1, tracks_added=10, tracks_removed=2)
        assert e.tracks_added == 10
        assert e.tracks_removed == 2

    def test_all_events_are_dataclasses(self):
        for cls in [TrackAdded, TrackUpdated, TrackRemoved, TrackMissingChanged,
                     FavoriteChanged, PlayCountChanged, AlbumChanged, ArtistChanged,
                     SourceChanged, ScanStarted, ScanProgress, ScanFinished,
                     MetadataWritten, ArtworkChanged, PlaylistChanged, QueueChanged]:
            assert fields(cls), f"{cls.__name__} has no fields"
