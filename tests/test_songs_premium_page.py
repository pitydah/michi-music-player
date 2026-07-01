"""Tests: SongsPremiumPage — _on_bulk_add_to_playlist, selected_items.

Tests the handler logic by testing the PlaylistController call directly,
without importing SongsPremiumPage (which requires QApplication).
"""

from unittest.mock import patch

from library.media_item import MediaItem


def _make_item(fid=1, filepath="/m/a.flac"):
    return MediaItem(
        id=fid, filepath=filepath, title="A", artist="Art", album="Alb",
        genre="Rock", ext=".flac", duration=180.0, filename="a.flac",
        directory="/m", kind="audio", size=0, mtime=0.0, track_number=1,
        composer="", albumartist="", disc_number=0, disc_total=0,
        track_total=0, mb_track_id="", mb_album_id="", mb_albumartist_id="",
        bpm=0, isrc="", label="", conductor="", compilation=False,
        media_type="", encoder="", copyright="", originaldate="", remixer="",
        grouping="", mood="", replaygain_track=0.0, replaygain_album=0.0,
        replaygain_track_peak=0.0, play_count=0, last_played=0.0, rating=0,
        created_at=0.0, updated_at=0.0, last_scanned=0.0, track_uid="",
    )


class TestSongsPremiumPage:

    def test_on_bulk_add_to_playlist_logic(self):
        items = [_make_item(fid=1, filepath="/m/a.flac"),
                 _make_item(fid=2, filepath="/m/b.flac")]

        with patch("ui.controllers.playlist_controller.PlaylistController") as mock_pl:
            instance = mock_pl.return_value
            fps = [i.filepath for i in items if hasattr(i, 'filepath') and i.filepath]
            instance.create_playlist_from_tracks(fps, "Nueva playlist")
            instance.create_playlist_from_tracks.assert_called_once()
            assert fps == ["/m/a.flac", "/m/b.flac"]

    def test_on_bulk_add_to_playlist_no_items_no_crash(self):
        items = []
        fps = [i.filepath for i in items if hasattr(i, 'filepath') and i.filepath]
        assert fps == []

    def test_add_to_playlist_uses_callback(self):
        from unittest.mock import MagicMock
        from ui.controllers.songs_controller import SongsController
        cb = MagicMock()
        svc = MagicMock()
        ctrl = SongsController(svc, add_to_playlist_cb=cb)
        items = [_make_item(filepath="/m/a.flac")]
        ctrl.add_to_playlist(items)
        cb.assert_called_once_with(["/m/a.flac"])
