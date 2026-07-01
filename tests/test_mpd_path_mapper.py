"""Tests for MPD Path Mapper."""

import os


class TestMpdPathMapper:
    def test_to_mpd_path(self):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper(
            music_dir="/home/user/Music",
            local_root="/home/user/Music")
        result = mapper.to_mpd_path("/home/user/Music/Album/track.flac")
        assert result == "Album/track.flac"

    def test_from_mpd_path(self):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper(
            music_dir="/home/user/Music",
            local_root="/home/user/Music")
        result = mapper.from_mpd_path("Album/track.flac")
        expected = os.path.normpath("/home/user/Music/Album/track.flac")
        assert result == expected

    def test_from_mpd_path_absolute_passthrough(self):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper(
            music_dir="/home/user/Music",
            local_root="/home/user/Music")
        result = mapper.from_mpd_path("/absolute/path.flac")
        assert result == "/absolute/path.flac"

    def test_to_mpd_path_no_match_returns_full(self):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper(
            music_dir="/home/user/Music",
            local_root="/home/user/Music")
        result = mapper.to_mpd_path("/other/location/track.flac")
        assert result == "/other/location/track.flac"

    def test_set_music_directory(self):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper()
        mapper.set_music_directory("/new/music")
        assert mapper.music_directory == "/new/music"

    def test_set_local_root(self):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper()
        mapper.set_local_root("/new/root")
        result = mapper.from_mpd_path("track.flac")
        expected = os.path.normpath("/new/root/track.flac")
        assert result == expected
