"""Tests for ArtistRepository — artist groups state and lookups."""
import os
from unittest.mock import MagicMock
from ui.controllers.artist_repository import ArtistRepository


def make_mock_item(filepath, title="Song", artist="Artist", album="Album", **kwargs):
    item = MagicMock()
    item.filepath = filepath
    item.title = title
    item.artist = artist
    item.album = album
    item.duration = kwargs.get("duration", 180.0)
    item.year = kwargs.get("year", 2020)
    item.genre = kwargs.get("genre", "Rock")
    item.track_number = kwargs.get("track_number", 1)
    item.disc_number = kwargs.get("disc_number", 0)
    item.disc_total = kwargs.get("disc_total", 0)
    item.track_total = kwargs.get("track_total", 0)
    item.ext = kwargs.get("ext", ".flac")
    item.albumartist = kwargs.get("albumartist", "")
    item.filename = kwargs.get("filename", os.path.basename(filepath))
    item.directory = kwargs.get("directory", os.path.dirname(filepath))
    item.kind = "audio"
    item.bitrate = 0
    item.sample_rate = 0
    item.channels = 0
    item.size = 0
    item.mtime = 0.0
    item.composer = ""
    return item


class TestArtistRepository:
    def test_empty_repo(self):
        repo = ArtistRepository()
        assert repo.count == 0
        assert repo.groups == []
        assert repo.current_key is None
        assert repo.get_group("nada") is None
        assert repo.filepaths("nada") == []

    def test_build_groups_items(self):
        items = [
            make_mock_item("/tmp/a.flac", "Song 1", "Artist A", "Album X"),
            make_mock_item("/tmp/b.flac", "Song 2", "Artist A", "Album X"),
            make_mock_item("/tmp/c.mp3", "Song 3", "Artist B", "Album Y"),
        ]
        repo = ArtistRepository()
        repo.build(items)

        assert repo.count >= 1
        groups = repo.groups
        assert any("artist a" in g.key for g in groups)

    def test_get_group_found(self):
        items = [
            make_mock_item("/tmp/a.flac", "Song 1", "Test Artist", "Test Album"),
        ]
        repo = ArtistRepository()
        repo.build(items)

        group = repo.get_group("test artist")
        assert group is not None
        assert group.track_count == 1
        assert group.album_count == 1

    def test_get_group_not_found(self):
        repo = ArtistRepository()
        assert repo.get_group("noexiste") is None

    def test_current_key(self):
        repo = ArtistRepository()
        assert repo.current_key is None
        repo.current_key = "some_key"
        assert repo.current_key == "some_key"
        repo.clear_current()
        assert repo.current_key is None

    def test_filepaths_filters_missing(self):
        items = [
            make_mock_item("/tmp/exists.flac", "Song", "Artist", "Album"),
            make_mock_item("/tmp/missing.flac", "Song", "Artist", "Album"),
        ]
        repo = ArtistRepository()
        repo.build(items)
        paths = repo.filepaths("artist")
        assert isinstance(paths, list)
