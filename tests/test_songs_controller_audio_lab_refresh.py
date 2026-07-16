"""Tests: SongsController.refresh_audio_lab_badges()."""

from unittest.mock import MagicMock, patch

from library.media_item import MediaItem


def _make_item(id: int, fp: str):
    item = MediaItem()
    item.id = id
    item.filepath = fp
    item.title = "t"
    item.artist = "a"
    item.album = "al"
    return item


class TestSongsControllerAudioLabRefresh:

    def test_refresh_audio_lab_badges_existe(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        songs = SongsController(svc)
        assert hasattr(songs, 'refresh_audio_lab_badges')

    def test_refresh_llama_invalidate_cache_for_paths(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        songs = SongsController(svc)
        with (
            patch.object(songs._status_svc, 'invalidate_cache_for_paths') as mock_inv,
            patch.object(songs._status_svc, 'compute_batch'),
        ):
            songs.refresh_audio_lab_badges(["/p1.flac"])
            mock_inv.assert_called_once_with(["/p1.flac"])

    def test_refresh_llama_compute_batch(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        songs = SongsController(svc)
        with patch.object(songs._status_svc, 'compute_batch') as mock_batch:
            songs.refresh_audio_lab_badges()
            mock_batch.assert_called_once()

    def test_refresh_no_crash_empty_list(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        songs = SongsController(svc)
        songs.refresh_audio_lab_badges([])

    def test_refresh_no_crash_none(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        songs = SongsController(svc)
        songs.refresh_audio_lab_badges()
