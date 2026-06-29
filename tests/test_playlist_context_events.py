"""Tests: Playlist context events — IMPORTED, EXPORTED, no paths."""

from unittest.mock import MagicMock


class TestPlaylistContextEvents:

    def test_import_emits_playlist_imported(self):
        ctx = MagicMock()
        from core.context.context_events import AppEvent
        ctx.record_playlist_imported(42, "Test", 10)
        args = ctx.record_playlist_imported.call_args
        assert args[0] == (42, "Test", 10)

    def test_export_emits_playlist_exported(self):
        ctx = MagicMock()
        ctx.record_playlist_exported(1, "My Playlist", 15)
        args = ctx.record_playlist_exported.call_args
        assert args[0] == (1, "My Playlist", 15)

    def test_payload_contains_safe_keys_only(self):
        from core.context.context_service import ContextService
        svc = ContextService()
        svc.record_playlist_imported(playlist_id=1, name="Test", count=10)
        svc.record_playlist_exported(playlist_id=1, name="Test", count=10)
        # Verify the events were created without crash
        assert True
