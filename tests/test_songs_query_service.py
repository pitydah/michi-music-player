"""Tests: SongsQueryService — filter, search, format/genre extraction."""

from library.media_item import MediaItem
from library.songs_query_service import SongsQueryService


class _DummyDb:
    """Minimal DB mock that returns predefined MediaItems."""
    def __init__(self, items):
        self._items = items

    def get_all(self):
        return list(self._items)


def _make_item(filepath="/m/a.flac", title="A", artist="Art", album="Alb",
               genre="Rock", year=2000, duration=180.0, ext=".flac",
               sample_rate=44100, bit_depth=16, channels=2, bitrate=1411,
               bpm=120, fid=1):
    return MediaItem(
        id=fid, filepath=filepath, title=title, artist=artist,
        album=album, genre=genre, year=year, duration=duration,
        ext=ext, sample_rate=sample_rate, bit_depth=bit_depth,
        channels=channels, bitrate=bitrate, bpm=bpm,
        filename="a.flac", directory="/m", kind="audio", size=1000000,
        mtime=0.0, track_number=1, composer="", albumartist="",
        disc_number=0, disc_total=0, track_total=0, mb_track_id="",
        mb_album_id="", mb_albumartist_id="", isrc="", label="",
        conductor="", compilation=False, media_type="", encoder="",
        copyright="", originaldate="", remixer="", grouping="", mood="",
        replaygain_track=0.0, replaygain_album=0.0,
        replaygain_track_peak=0.0, play_count=0, last_played=0.0,
        rating=0, created_at=0.0, updated_at=0.0, last_scanned=0.0,
        track_uid="",
    )


class TestSongsQueryService:

    def test_fetch_all(self):
        items = [_make_item(fid=1), _make_item(fid=2)]
        svc = SongsQueryService(_DummyDb(items))
        assert len(svc.fetch_all()) == 2

    def test_distinct_genres(self):
        items = [_make_item(fid=1, genre="Rock"),
                 _make_item(fid=2, genre="Jazz"),
                 _make_item(fid=3, genre="Rock")]
        svc = SongsQueryService(_DummyDb(items))
        genres = svc.distinct_genres(items)
        assert genres == ["Jazz", "Rock"]

    def test_distinct_formats(self):
        items = [_make_item(fid=1, ext=".flac"),
                 _make_item(fid=2, ext=".mp3")]
        svc = SongsQueryService(_DummyDb(items))
        fmts = svc.distinct_formats(items)
        assert "FLAC" in fmts
        assert "MP3" in fmts

    def test_filter_by_format(self):
        items = [_make_item(fid=1, ext=".flac"),
                 _make_item(fid=2, ext=".mp3")]
        svc = SongsQueryService(None)
        filtered = svc.filter(items, formats={"FLAC"})
        assert len(filtered) == 1
        assert filtered[0].ext == ".flac"

    def test_filter_by_year_min(self):
        items = [_make_item(fid=1, year=1990),
                 _make_item(fid=2, year=2020)]
        svc = SongsQueryService(None)
        filtered = svc.filter(items, year_min=2000)
        assert len(filtered) == 1
        assert filtered[0].year == 2020

    def test_filter_by_text(self):
        items = [_make_item(fid=1, title="Hello World"),
                 _make_item(fid=2, title="Goodbye")]
        svc = SongsQueryService(None)
        filtered = svc.filter(items, text_filter="hello")
        assert len(filtered) == 1
        assert "Hello" in filtered[0].title
