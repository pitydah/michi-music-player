from unittest.mock import MagicMock

from audio.player_service import PlayerService


class TestPlayerService:
    def test_create(self):
        svc = PlayerService(engine=MagicMock(), event_bus=MagicMock())
        assert not svc._current_title

    def test_volume_default(self):
        svc = PlayerService(engine=MagicMock(), event_bus=MagicMock())
        svc.set_volume(50)
        assert svc._current_title == ""


class TestLibraryTrackContextMigration:
    """C5 — PlayerService reads track context via fetch_track_context, not db.conn."""

    def test_uses_fetch_track_context_on_library_db(self):
        library_db = MagicMock()
        library_db.fetch_track_context.return_value = {
            "title": "Genesis", "artist": "Phil", "album": "Face",
            "album_key": "k", "track_uid": "u", "year": 1981, "genre": "Prog",
            "duration": 200.0, "format": "flac", "sample_rate": 44100,
            "bit_depth": 16, "bitrate": 1411,
        }
        svc = PlayerService(
            engine=MagicMock(), event_bus=MagicMock(), library_db=library_db)

        ctx = svc._library_track_context("/music/track.flac")

        library_db.fetch_track_context.assert_called_once_with("/music/track.flac")
        # The raw SQLite connection must never be touched by the service.
        library_db.conn.assert_not_called()
        assert ctx["title"] == "Genesis"
        assert ctx["sample_rate"] == 44100

    def test_returns_empty_when_library_db_lacks_fetch_method(self):
        # A legacy db object without the new method must degrade to {} rather
        # than raising. Plain object (not MagicMock) so getattr returns None.
        class LegacyDb:
            pass

        svc = PlayerService(
            engine=MagicMock(), event_bus=MagicMock(), library_db=LegacyDb())

        assert svc._library_track_context("/music/track.flac") == {}

    def test_returns_empty_without_library_db(self):
        svc = PlayerService(engine=MagicMock(), event_bus=MagicMock())
        assert svc._library_track_context("/music/track.flac") == {}
        assert svc._library_track_context("") == {}

    def test_swallows_exceptions_from_fetch(self):
        library_db = MagicMock()
        library_db.fetch_track_context.side_effect = RuntimeError("db locked")
        svc = PlayerService(
            engine=MagicMock(), event_bus=MagicMock(), library_db=library_db)

        assert svc._library_track_context("/music/track.flac") == {}
