"""Tests: Songs status service — favorites, quality classification, refresh."""

from unittest.mock import patch

from library.media_item import MediaItem
from library.songs_status_service import SongsStatusService


class _FakeDb:
    def __init__(self, favs=None):
        self._favs = favs or []

    def get_favorites(self):
        return self._favs


def _make_item(fid=1, filepath="/nonexistent/audio.flac", title="A", artist="Art",
               album="Alb", genre="Rock", ext=".flac",
               sample_rate=44100, bit_depth=16):
    return MediaItem(
        id=fid, filepath=filepath, title=title, artist=artist,
        album=album, genre=genre, ext=ext,
        sample_rate=sample_rate, bit_depth=bit_depth,
        duration=180.0, filename="a.flac", directory="/nonexistent",
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


class TestSongsStatusService:

    def test_refresh_favorites_string_ids(self):
        db = _FakeDb(["42", "99"])
        svc = SongsStatusService(db)
        svc.refresh_favorites()
        assert 42 in svc.favorite_ids()
        assert 99 in svc.favorite_ids()

    def test_refresh_favorites_empty(self):
        svc = SongsStatusService(_FakeDb([]))
        svc.refresh_favorites()
        assert svc.favorite_ids() == set()

    def test_favorite_ids_property(self):
        svc = SongsStatusService(None)
        assert svc.favorite_ids() == set()

    @patch("library.songs_status_service.SongsStatusService._get_diag_badge",
           return_value=None)
    @patch("library.songs_status_service.SongsStatusService._has_cover",
           return_value=True)
    def test_classify_hires(self, *_):
        item = _make_item(ext=".flac", sample_rate=96000, bit_depth=24)
        svc = SongsStatusService(None)
        st = svc.compute_status(item)
        assert st["quality_category"] == "hires"
        assert "Hi-Res" in st["quality_label"]

    @patch("library.songs_status_service.SongsStatusService._get_diag_badge",
           return_value=None)
    @patch("library.songs_status_service.SongsStatusService._has_cover",
           return_value=True)
    def test_classify_lossless(self, *_):
        item = _make_item(ext=".flac", sample_rate=44100, bit_depth=16)
        svc = SongsStatusService(None)
        st = svc.compute_status(item)
        assert st["quality_category"] == "lossless"

    @patch("library.songs_status_service.SongsStatusService._get_diag_badge",
           return_value=None)
    @patch("library.songs_status_service.SongsStatusService._has_cover",
           return_value=True)
    def test_classify_lossy(self, *_):
        item = _make_item(ext=".mp3", bitrate=320000)
        svc = SongsStatusService(None)
        st = svc.compute_status(item)
        assert st["quality_category"] == "lossy"

    @patch("library.songs_status_service.SongsStatusService._get_diag_badge",
           return_value=None)
    @patch("library.songs_status_service.SongsStatusService._has_cover",
           return_value=True)
    def test_classify_dsd(self, *_):
        item = _make_item(ext=".dsf")
        svc = SongsStatusService(None)
        st = svc.compute_status(item)
        assert st["quality_category"] == "dsd"

    @patch("library.songs_status_service.SongsStatusService._get_diag_badge",
           return_value=None)
    @patch("library.songs_status_service.SongsStatusService._has_cover",
           return_value=True)
    def test_missing_metadata_badge(self, *_):
        item = _make_item(title="", artist="")
        svc = SongsStatusService(None)
        st = svc.compute_status(item)
        badges = st.get("badges", [])
        assert any("Sin" in b for b in badges)

    @patch("library.songs_status_service.SongsStatusService._get_diag_badge",
           return_value=None)
    @patch("library.songs_status_service.SongsStatusService._has_cover",
           return_value=True)
    def test_compute_batch(self, *_):
        items = [_make_item(fid=1), _make_item(fid=2)]
        svc = SongsStatusService(None)
        result = svc.compute_batch(items)
        assert len(result) == 2
        assert 1 in result
        assert 2 in result
