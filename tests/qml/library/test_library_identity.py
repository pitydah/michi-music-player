from __future__ import annotations

import hashlib
from core.library.identity import (
    TrackIdentity, AlbumIdentity, ArtistIdentity,
)


class TestTrackIdentity:
    def test_constructor(self):
        tid = TrackIdentity(track_id=1, track_uid="uid1", source_id=42)
        assert tid.track_id == 1
        assert tid.track_uid == "uid1"
        assert tid.source_id == 42

    def test_from_filepath(self):
        fp = "/music/song.flac"
        tid = TrackIdentity.from_filepath(1, fp)
        assert tid.track_id == 1
        expected_hash = hashlib.sha256(fp.encode()).hexdigest()[:16]
        assert tid.filepath_hash == expected_hash
        assert tid.track_uid == f"fp:{expected_hash}"

    def test_from_row(self):
        tid = TrackIdentity.from_row((1, "uid1", 42, "abc123"))
        assert tid.track_id == 1
        assert tid.track_uid == "uid1"
        assert tid.source_id == 42
        assert tid.filepath_hash == "abc123"

    def test_from_row_minimal(self):
        tid = TrackIdentity.from_row((1, "uid1"))
        assert tid.track_id == 1
        assert tid.source_id is None

    def test_frozen(self):
        tid = TrackIdentity(track_id=1, track_uid="uid1")
        import dataclasses
        assert dataclasses.fields(tid)


class TestAlbumIdentity:
    def test_constructor(self):
        aid = AlbumIdentity(album_key="key1", album_artist="Artist",
                            album_title="Album")
        assert aid.album_key == "key1"
        assert aid.album_artist == "Artist"
        assert aid.album_title == "Album"

    def test_frozen(self):
        aid = AlbumIdentity(album_key="k", album_artist="a", album_title="t")
        import dataclasses
        assert dataclasses.fields(aid)


class TestArtistIdentity:
    def test_constructor(self):
        aid = ArtistIdentity(artist_name="Name", artist_sort="Sort")
        assert aid.artist_name == "Name"
        assert aid.artist_sort == "Sort"

    def test_default_sort(self):
        aid = ArtistIdentity(artist_name="Name")
        assert aid.artist_sort == ""
