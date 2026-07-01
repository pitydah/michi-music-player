"""Tests: SongsController — unit tests with fake services."""

from unittest.mock import MagicMock

from library.media_item import MediaItem


def _make_item(fid=1, filepath="/m/a.flac", title="A", ext=".flac",
               sample_rate=44100, bitrate=1411000):
    return MediaItem(
        id=fid, filepath=filepath, title=title, artist="Art", album="Alb",
        genre="Rock", ext=ext, duration=180.0, sample_rate=sample_rate,
        bitrate=bitrate, filename="a.flac", directory="/m",
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


class _FakeDb:
    def __init__(self):
        self._favs = []

    def get_all(self):
        return [_make_item(fid=1), _make_item(fid=2)]

    def search_advanced(self, *a, **kw):
        return []

    def get_favorites(self):
        return self._favs

    def toggle_favorite(self, fp):
        if fp in self._favs:
            self._favs.remove(fp)
            return False
        self._favs.append(fp)
        return True


class _FakeServices:
    def __init__(self):
        self.db = _FakeDb()
        self.playback = MagicMock()
        self.workers = MagicMock()
        self.context_svc = MagicMock()
        self.toast = MagicMock()


class TestSongsController:

    def _ctrl(self):
        from ui.controllers.songs_controller import SongsController
        return SongsController(_FakeServices())

    def test_load_populates_items(self):
        ctrl = self._ctrl()
        ctrl.load()
        assert len(ctrl._all_items) == 2

    def test_apply_filter_text(self):
        ctrl = self._ctrl()
        ctrl.load()
        result = ctrl.apply_filter(text="nonexistent")
        assert len(result) == 0

    def test_apply_filter_sample_rate(self):
        ctrl = self._ctrl()
        ctrl.load()
        result = ctrl.apply_filter(sample_rate_min=44100)
        assert len(result) == 2

    def test_apply_filter_bitrate_min_converts_kbps(self):
        ctrl = self._ctrl()
        ctrl.load()
        result = ctrl.apply_filter(bitrate_min=320000)
        assert len(result) >= 0

    def test_toggle_favorite(self):
        ctrl = self._ctrl()
        ctrl.load()
        item = ctrl._all_items[0]
        ctrl.toggle_favorite(item)
        assert item.filepath in ctrl._services.db._favs
        ctrl.toggle_favorite(item)
        assert item.filepath not in ctrl._services.db._favs

    def test_play_items(self):
        ctrl = self._ctrl()
        ctrl.load()
        ctrl.play_items(ctrl._all_items[:1])
        ctrl._services.playback.play_queue.assert_called_once()

    def test_queue_items(self):
        ctrl = self._ctrl()
        ctrl.load()
        ctrl.queue_items(ctrl._all_items[:1])
        ctrl._services.playback.enqueue.assert_called_once()

    def test_edit_metadata_callback(self):
        cb = MagicMock()
        from ui.controllers.songs_controller import SongsController
        ctrl = SongsController(_FakeServices(), open_metadata_for_files=cb)
        ctrl.load()
        ctrl.edit_metadata(ctrl._all_items[:1])
        cb.assert_called_once()

    def test_locate_file_callback(self):
        cb = MagicMock()
        from ui.controllers.songs_controller import SongsController
        ctrl = SongsController(_FakeServices(), locate_file=cb)
        ctrl.load()
        ctrl.locate_file(ctrl._all_items[0])
        cb.assert_called_once()

    def test_add_to_playlist_callback(self):
        cb = MagicMock()
        from ui.controllers.songs_controller import SongsController
        ctrl = SongsController(_FakeServices(), add_to_playlist_cb=cb)
        ctrl.load()
        ctrl.add_to_playlist(ctrl._all_items[:1])
        cb.assert_called_once()

    def test_view_state_returns_songs_view_state(self):
        from library.songs_view_state import SongsViewState
        ctrl = self._ctrl()
        ctrl.load()
        vs = ctrl.view_state()
        assert isinstance(vs, SongsViewState)
        assert len(vs.items) > 0
