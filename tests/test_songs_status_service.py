"""Tests: SongsStatusService — favorites, quality, cache, Audio Lab warnings."""

from unittest.mock import patch

from library.media_item import MediaItem
from library.songs_status_service import SongsStatusService


class _FakeDb:
    def __init__(self, favs=None):
        self._favs = favs or []

    def get_favorites(self):
        return self._favs


def _make_item(fid=1, filepath="/m/a.flac", title="A", artist="Art",
               album="Alb", genre="Rock", ext=".flac",
               sample_rate=44100, bit_depth=16):
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


class TestSongsStatusService:

    def test_refresh_favorites_string_ids(self):
        svc = SongsStatusService(_FakeDb(["42", "99"]))
        svc.refresh_favorites()
        f = svc.favorite_track_ids()
        assert "42" in f
        assert "99" in f

    def test_refresh_favorites_empty(self):
        svc = SongsStatusService(_FakeDb([]))
        svc.refresh_favorites()
        assert svc.favorite_track_ids() == set()

    def test_status_cache_public_copy(self):
        svc = SongsStatusService(None)
        item = _make_item(fid=1)
        svc.compute_status(item)
        cache = svc.status_cache()
        assert 1 in cache
        assert cache[1].get("quality_label") is not None
        # Verify it's a copy, not the internal dict
        cache[999] = "test"
        assert 999 not in svc._quality_cache

    def test_invalidate_cache_clears_both(self):
        svc = SongsStatusService(None)
        svc._quality_cache[1] = {}
        svc._cover_cache["/x.flac"] = True
        svc.invalidate_cache()
        assert len(svc._quality_cache) == 0
        assert len(svc._cover_cache) == 0

    def test_invalidate_cache_for_paths(self):
        svc = SongsStatusService(None)
        svc._cover_cache["/a.flac"] = True
        svc._cover_cache["/b.flac"] = True
        svc.invalidate_cache_for_paths(["/a.flac"])
        assert "/a.flac" not in svc._cover_cache
        assert "/b.flac" in svc._cover_cache

    @patch.object(SongsStatusService, "_get_diag_badge", return_value=None)
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_classify_hires(self, *_):
        svc = SongsStatusService(None)
        item = _make_item(ext=".flac", sample_rate=96000, bit_depth=24)
        st = svc.compute_status(item)
        assert st["quality_category"] == "hires"

    @patch.object(SongsStatusService, "_get_diag_badge", return_value=None)
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_classify_lossless(self, *_):
        svc = SongsStatusService(None)
        st = svc.compute_status(_make_item(ext=".flac"))
        assert st["quality_category"] == "lossless"

    @patch.object(SongsStatusService, "_get_diag_badge", return_value=None)
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_classify_lossy(self, *_):
        svc = SongsStatusService(None)
        st = svc.compute_status(_make_item(ext=".mp3"))
        assert st["quality_category"] == "lossy"

    @patch.object(SongsStatusService, "_get_diag_badge", return_value=None)
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_classify_dsd(self, *_):
        svc = SongsStatusService(None)
        st = svc.compute_status(_make_item(ext=".dsf"))
        assert st["quality_category"] == "dsd"

    @patch.object(SongsStatusService, "_get_diag_badge", return_value=None)
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_missing_metadata(self, *_):
        svc = SongsStatusService(None)
        st = svc.compute_status(_make_item(title="", artist=""))
        assert st["missing_metadata"] is True
        badges = st.get("badges", [])
        assert any("Sin" in b for b in badges)

    @patch.object(SongsStatusService, "_get_diag_badge",
                  return_value={"label": "Sospechoso", "kind": "warning"})
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_audio_lab_warning_from_diag_badge(self, *_):
        svc = SongsStatusService(None)
        st = svc.compute_status(_make_item())
        assert st["has_audio_lab_warning"] is True

    @patch.object(SongsStatusService, "_get_diag_badge", return_value=None)
    @patch.object(SongsStatusService, "_has_cover", return_value=True)
    def test_spectral_warning(self, *_):
        svc = SongsStatusService(None)
        item = _make_item()
        setattr(item, 'spectral_verdict', "SUSPICIOUS_UPSAMPLING")
        st = svc.compute_status(item)
        assert st["has_audio_lab_warning"] is True
        assert any("sospechoso" in b.lower() for b in st.get("badges", []))

    def test_favorite_set(self):
        svc = SongsStatusService(None)
        svc._fav_track_ids.add("/m/a.flac")
        assert "/m/a.flac" in svc.favorite_track_ids()
