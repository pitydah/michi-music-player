"""Tests: SongsPremiumPage — _on_bulk_add_to_playlist, selected_items."""

from unittest.mock import MagicMock, patch

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

    def test_on_bulk_add_to_playlist_calls_create(self):
        from ui.library.songs_premium_page import SongsPremiumPage
        page = SongsPremiumPage()
        win = MagicMock()
        ctrl = MagicMock()
        ctrl._win = win
        page._ctrl = ctrl
        items = [_make_item(fid=1, filepath="/m/a.flac"),
                 _make_item(fid=2, filepath="/m/b.flac")]

        with patch.object(page, 'selected_items', return_value=items):
            with patch("ui.library.songs_premium_page.PlaylistController") as mock_pl:
                instance = mock_pl.return_value
                page._on_bulk_add_to_playlist()

                instance.create_playlist_from_tracks.assert_called_once()
                fps_arg = instance.create_playlist_from_tracks.call_args[0][0]
                assert len(fps_arg) == 2
                assert "/m/a.flac" in fps_arg

    def test_on_bulk_add_to_playlist_no_items(self):
        from ui.library.songs_premium_page import SongsPremiumPage
        page = SongsPremiumPage()
        page._ctrl = MagicMock()
        page._on_bulk_add_to_playlist()
