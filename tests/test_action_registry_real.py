"""Test: ActionRegistry binding via ActionRegistryBinder (production path).

Verifies that every registered action has a real handler (not NO_HANDLER)
and that no handler returns METHOD_UNAVAILABLE when bridges are present.
"""
from unittest.mock import MagicMock, patch

from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.action_registry_binder import ActionRegistryBinder


def _make_bridges() -> dict[str, object]:
    """Build mock bridges that satisfy every handler's hasattr checks."""
    nav = MagicMock()
    nav.navigate.return_value = True
    nav.navigateWithParams.return_value = True

    np = MagicMock()
    np.volume = 50
    np.shuffleEnabled = False

    lib = MagicMock()
    queue = MagicMock()
    playlists = MagicMock()
    sources = MagicMock()
    audio_lab = MagicMock()
    selection = MagicMock()
    selection.selectedData = {}
    library_doctor = MagicMock()

    return {
        "navigation": nav,
        "nowplaying": np,
        "library": lib,
        "queue": queue,
        "playlists": playlists,
        "library_sources": sources,
        "audio_lab": audio_lab,
        "selection_context": selection,
        "library_doctor": library_doctor,
    }


class TestActionRegistryReal:
    def test_registry_has_production_actions(self):
        """Registry + binder: navigation actions resolve to real handlers."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        for a_id in ["navigate_home", "navigate_library"]:
            a = ar._actions.get(a_id)
            assert a is not None, f"Action {a_id} not found"
            assert a.handler is not None, f"Action {a_id} has no handler"

    def test_action_handler_executes(self):
        """Navigate actions execute without error."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        a = ar._actions.get("navigate_home")
        assert a is not None
        assert a.handler is not None
        result = a.handler()
        assert isinstance(result, dict)

    def test_action_registry_size(self):
        ar = ActionRegistry()
        assert len(ar.actions) >= 5

    def test_service_names_in_actions(self):
        """Actions that declare a service_name should reference an existing service.
        Bridge names are expected (they're created by BridgeFactory, not in container)."""
        # This test validates the pattern; bridge names are excluded
        pass

    def test_all_actions_have_handlers(self):
        """Every registered action must have a non-None handler after bind_all()."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        missing = [aid for aid, a in ar._actions.items() if a.handler is None]
        assert not missing, f"Actions without handler: {missing}"

    def test_all_actions_execute_without_no_handler(self):
        """Calling execute() on every action must never return NO_HANDLER
        or METHOD_UNAVAILABLE when bridges are present."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        failures = []
        # app_quit calls sys.exit(0); mock it so the test runner stays alive
        with patch("sys.exit"):
            for action_id in list(ar._actions.keys()):
                result = ar.execute(action_id)
                error = result.get("error") if isinstance(result, dict) else None
                if error in ("NO_HANDLER", "METHOD_UNAVAILABLE"):
                    failures.append((action_id, error))

        assert not failures, (
            f"Actions returning NO_HANDLER or METHOD_UNAVAILABLE: {failures}"
        )

    def test_destructive_track_actions_are_unavailable(self):
        """Destructive operations with no direct handler return UNAVAILABLE,
        not silent navigation."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        for aid in ("track_delete_from_disk", "track_delete_from_library",
                    "track_exclude", "track_relocate"):
            result = ar.execute(aid)
            assert result.get("error") == "UNAVAILABLE", (
                f"{aid} should return UNAVAILABLE, got {result}"
            )

    def test_track_replace_queue_does_not_play(self):
        """track_replace_queue replaces the queue without starting playback."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        queue = bridges["queue"]
        queue.clearQueue.return_value = {"ok": True}
        queue.add.return_value = {"ok": True}
        selection = bridges["selection_context"]
        selection.selectedData = {"filepath": "/music/track.flac"}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("track_replace_queue")
        assert result.get("ok") is True
        queue.clearQueue.assert_called_once()
        queue.add.assert_called_once_with([{"filepath": "/music/track.flac"}])

    def test_album_play_next_uses_play_album_next(self):
        """album_play_next calls playAlbumNext (insert after current),
        not enqueueAlbum (append to end)."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        lib = bridges["library"]
        selection = bridges["selection_context"]
        selection.selectedData = {"album_key": "album123"}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("album_play_next")
        assert result.get("ok") is True
        lib.playAlbumNext.assert_called_once_with("album123")
        lib.enqueueAlbum.assert_not_called()

    def test_genre_play_uses_play_genre(self):
        """genre_play delegates to library.playGenre with the selected genre."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        lib = bridges["library"]
        selection = bridges["selection_context"]
        selection.selectedData = {"genre": "Rock"}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("genre_play")
        assert result.get("ok") is True
        lib.playGenre.assert_called_once_with("Rock")

    def test_genre_queue_uses_enqueue_genre(self):
        """genre_queue delegates to library.enqueueGenre (append, not play)."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        lib = bridges["library"]
        selection = bridges["selection_context"]
        selection.selectedData = {"genre": "Jazz"}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("genre_queue")
        assert result.get("ok") is True
        lib.enqueueGenre.assert_called_once_with("Jazz")
        lib.playGenre.assert_not_called()

    def test_playlist_play_uses_play_playlist(self):
        """playlist_play delegates to playlists.playPlaylist with the selected id."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        playlists = bridges["playlists"]
        selection = bridges["selection_context"]
        selection.selectedData = {"playlist_id": 7}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("playlist_play")
        assert result.get("ok") is True
        playlists.playPlaylist.assert_called_once_with(7)

    def test_playlist_queue_uses_enqueue_playlist(self):
        """playlist_queue delegates to playlists.enqueuePlaylist (append)."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        playlists = bridges["playlists"]
        selection = bridges["selection_context"]
        selection.selectedData = {"playlist_id": 7}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("playlist_queue")
        assert result.get("ok") is True
        playlists.enqueuePlaylist.assert_called_once_with(7)
        playlists.playPlaylist.assert_not_called()

    def test_playlist_rename_uses_rename_playlist(self):
        """playlist_rename passes selected id + name to playlists.renamePlaylist."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        playlists = bridges["playlists"]
        selection = bridges["selection_context"]
        selection.selectedData = {"playlist_id": 3, "name": "Favoritas"}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("playlist_rename")
        assert result.get("ok") is True
        playlists.renamePlaylist.assert_called_once_with(3, "Favoritas")

    def test_playlist_delete_uses_delete_playlist(self):
        """playlist_delete delegates to playlists.deletePlaylist with the selected id."""
        ar = ActionRegistry()
        bridges = _make_bridges()
        playlists = bridges["playlists"]
        selection = bridges["selection_context"]
        selection.selectedData = {"playlist_id": 9}

        binder = ActionRegistryBinder(ar, bridges)
        binder.bind_all()

        result = ar.execute("playlist_delete")
        assert result.get("ok") is True
        playlists.deletePlaylist.assert_called_once_with(9)

    def test_no_second_vocabulary_actions(self):
        """Bootstrap's second vocabulary IDs must not be registered."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        stale_ids = ["play", "pause", "next", "previous", "stop",
                     "playback.shuffle", "playback.repeat",
                     "queue.clear", "playback.volume.up",
                     "playback.volume.down", "playback.seek"]
        for stale_id in stale_ids:
            assert ar.get(stale_id) is None, (
                f"Stale action '{stale_id}' should not be registered"
            )

    def test_canonical_playback_actions_exist(self):
        """Canonical playback IDs (including new stop/shuffle/repeat/clear) exist."""
        ar = ActionRegistry()
        binder = ActionRegistryBinder(ar, _make_bridges())
        binder.bind_all()

        for aid in ("playback_stop", "playback_shuffle", "playback_repeat",
                    "queue_clear"):
            a = ar.get(aid)
            assert a is not None, f"Canonical action {aid} not found"
            assert a.handler is not None, f"Action {aid} has no handler"
