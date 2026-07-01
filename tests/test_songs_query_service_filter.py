"""Tests: Songs query service — quality filter, favorites filter, missing metadata."""

from library.media_item import MediaItem
from library.songs_query_service import SongsQueryService, _classify, _match_quality


def _make_item(fid=1, filepath="/m/a.flac", title="A", ext=".flac",
               sample_rate=44100, bit_depth=16, artist="Art",
               album="Alb", genre="Rock"):
    return MediaItem(
        id=fid, filepath=filepath, title=title, artist=artist,
        album=album, genre=genre, ext=ext,
        sample_rate=sample_rate, bit_depth=bit_depth,
        duration=180.0, filename="a.flac", directory="/m",
        kind="audio", size=0, mtime=0.0, track_number=1,
        composer="", albumartist="", disc_number=0, disc_total=0,
        track_total=0, mb_track_id="", mb_album_id="",
        mb_albumartist_id="", bpm=0, isrc="", label="",
        conductor="", compilation=False, media_type="", encoder="",
        copyright="", originaldate="", remixer="", grouping="",
        mood="", replaygain_track=0.0, replaygain_album=0.0,
        replaygain_track_peak=0.0, play_count=0, last_played=0.0,
        rating=0, created_at=0.0, updated_at=0.0, last_scanned=0.0,
        track_uid="",
    )


class TestSongsQueryService:

    def test_filter_format(self):
        svc = SongsQueryService(None)
        items = [_make_item(fid=1, ext=".flac"), _make_item(fid=2, ext=".mp3")]
        result = svc.filter(items, formats={"FLAC"})
        assert len(result) == 1
        assert result[0].ext == ".flac"

    def test_filter_quality_hires(self):
        svc = SongsQueryService(None)
        items = [
            _make_item(fid=1, ext=".flac", sample_rate=96000, bit_depth=24),
            _make_item(fid=2, ext=".mp3"),
        ]
        result = svc.filter(items, qualities={"hires"})
        assert len(result) == 1
        assert result[0].id == 1

    def test_filter_quality_lossy(self):
        svc = SongsQueryService(None)
        items = [
            _make_item(fid=1, ext=".flac"),
            _make_item(fid=2, ext=".mp3"),
        ]
        result = svc.filter(items, qualities={"lossy"})
        assert len(result) == 1
        assert result[0].id == 2

    def test_filter_favorites_by_filepath(self):
        svc = SongsQueryService(None)
        items = [_make_item(fid=1, filepath="/m/a.flac"),
                 _make_item(fid=2, filepath="/m/b.flac")]
        result = svc.filter(items, only_favorites=True, fav_ids={"/m/b.flac"})
        assert len(result) == 1
        assert result[0].filepath == "/m/b.flac"

    def test_filter_missing_metadata(self):
        svc = SongsQueryService(None)
        items = [
            _make_item(fid=1, title="A", artist="Art", album="Alb", genre="Rock"),
            _make_item(fid=2, title="", artist="", album="", genre=""),
        ]
        result = svc.filter(items, only_missing_metadata=True)
        assert len(result) == 1
        assert result[0].id == 2

    def test_classify_hires(self):
        item = _make_item(ext=".flac", sample_rate=96000, bit_depth=24)
        assert _classify(item) == "hires"

    def test_classify_lossless(self):
        item = _make_item(ext=".flac", sample_rate=44100, bit_depth=16)
        assert _classify(item) == "lossless"

    def test_classify_dsd(self):
        item = _make_item(ext=".dsf")
        assert _classify(item) == "dsd"

    def test_classify_lossy(self):
        item = _make_item(ext=".mp3")
        assert _classify(item) == "lossy"

    def test_match_quality_true(self):
        item = _make_item(ext=".flac", sample_rate=96000, bit_depth=24)
        assert _match_quality(item, {"hires"})

    def test_match_quality_false(self):
        item = _make_item(ext=".mp3")
        assert not _match_quality(item, {"hires"})

    def test_only_missing_file_missing(self, tmp_path):
        svc = SongsQueryService(None)
        existing = tmp_path / "exists.flac"
        existing.write_text("")
        items = [
            _make_item(filepath=str(existing)),
            _make_item(fid=2, filepath=str(tmp_path / "gone.flac")),
        ]
        result = svc.filter(items, only_missing_file=True)
        assert len(result) == 1
        assert "gone.flac" in result[0].filepath
