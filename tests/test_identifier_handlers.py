"""Tests for IdentifierHandlers."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def win():
    w = MagicMock()
    w._identifier_ctrl = MagicMock()
    w._identifier_view = MagicMock()
    w._db = MagicMock()
    w._db.delete_detected_track = MagicMock()
    w._detection = MagicMock()
    w._play_file = MagicMock()
    w._search = MagicMock()
    w._search_ctrl = MagicMock()
    w._fade_content = MagicMock()
    w._toast_svc = MagicMock()
    return w


@pytest.fixture
def handlers(win):
    from legacy_widgets.ui.controllers.legacy_controllers.identifier_handlers import IdentifierHandlers
    return IdentifierHandlers(win)


class TestIdentifierHandlers:
    def test_toggle_enables(self, handlers, win):
        handlers.toggle(True)
        assert win._identifier_ctrl.enabled is True
        win._identifier_view.set_identifier_enabled.assert_called_with(True)

    def test_toggle_disables(self, handlers, win):
        handlers.toggle(False)
        assert win._identifier_ctrl.enabled is False
        win._identifier_view.set_identifier_enabled.assert_called_with(False)
        win._identifier_ctrl.stop.assert_called_once()

    def test_clear_detected(self, handlers, win):
        handlers.clear_detected()
        win._db.clear_detected_tracks.assert_called_once()
        win._identifier_view.set_detected_tracks.assert_called_with([])

    def test_on_track_detected_updates_view(self, handlers, win):
        win._db.get_detected_tracks.return_value = ["t1"]
        handlers.on_track_detected("track")
        win._identifier_view.set_detected_tracks.assert_called_with(["t1"])

    def test_on_detection_failed_sets_status(self, handlers, win):
        handlers.on_detection_failed("error msg")
        win._identifier_view.set_status_message.assert_called_with("error msg")

    def test_on_track_selected_with_filepath(self, handlers, win):
        with patch("os.path.exists", return_value=True):
            handlers.on_track_selected({"filepath": "/path/to/song.flac"})
            win._play_file.assert_called_with("/path/to/song.flac")

    def test_on_track_selected_without_filepath_searches(self, handlers, win):
        handlers.on_track_selected({"title": "Song", "artist": "Artist"})
        win._search.setText.assert_called_with("Song Artist")
        win._search_ctrl.set_active.assert_called_with("local")
        win._search_ctrl.search.assert_called_with("Song Artist")

    def test_on_track_selected_no_title_or_artist(self, handlers, win):
        handlers.on_track_selected({"filepath": "", "title": "", "artist": ""})
        win._search.setText.assert_not_called()

    def test_on_settings_shows_preferences(self, handlers, win):
        win._show_preferences = MagicMock()
        handlers.on_settings()
        win._show_preferences.assert_called_with("identifier")

    def test_on_play_with_matched_filepath(self, handlers, win):
        with patch("os.path.isfile", return_value=True):
            handlers.on_play({"matched_filepath": "/path/to/song.flac"})
            win._play_file.assert_called_with("/path/to/song.flac")

    def test_on_play_with_filepath(self, handlers, win):
        with patch("os.path.isfile", return_value=True):
            handlers.on_play({"filepath": "/path/to/song.flac"})
            win._play_file.assert_called_with("/path/to/song.flac")

    def test_on_play_not_found(self, handlers, win):
        with patch("os.path.isfile", return_value=False):
            handlers.on_play({"filepath": "/nonexistent.flac"})
            win._toast_svc.show.assert_called()

    def test_on_search_sets_search(self, handlers, win):
        handlers.on_search({"title": "T", "artist": "A"})
        win._search.setText.assert_called_with("T A")
        win._search_ctrl.set_active.assert_called_with("local")
        win._search_ctrl.search.assert_called_with("T A")

    def test_on_search_no_title_or_artist(self, handlers, win):
        handlers.on_search({"title": "", "artist": ""})
        win._search.setText.assert_not_called()

    def test_on_delete_calls_db(self, handlers, win):
        win._db.get_detected_tracks.return_value = ["t1"]
        handlers.on_delete({"id": 42})
        win._db.delete_detected_track.assert_called_with(42)
        win._identifier_view.set_detected_tracks.assert_called_with(["t1"])

    def test_on_delete_no_delete_method(self, handlers, win):
        win._db = MagicMock()
        handlers.on_delete({"id": 42})

    def test_wire_signals_connects_view(self, handlers, win):
        handlers.wire_signals()
        v = win._identifier_view
        assert v.toggle_requested.connect.called
        assert v.clear_requested.connect.called
        assert v.track_selected.connect.called
        assert v.identify_once_requested.connect.called
        assert v.settings_requested.connect.called
        assert v.play_track_requested.connect.called
        assert v.search_track_requested.connect.called
        assert v.delete_track_requested.connect.called
        win._detection.track_detected.connect.assert_called()
        win._detection.detection_failed.connect.assert_called()
        win._identifier_ctrl.state_changed.connect.assert_called()
        win._identifier_ctrl.source_changed.connect.assert_called()
        win._identifier_ctrl.provider_changed.connect.assert_called()

    def test_wire_signals_no_detection(self, handlers, win):
        win._detection = None
        handlers.wire_signals()

    def test_wire_signals_no_identifier_ctrl(self, handlers, win):
        win._identifier_ctrl = None
        handlers.wire_signals()

    def test_show_loads_and_fades(self, handlers, win):
        win._db.get_detected_tracks.return_value = ["t1"]
        handlers.show("identifier")
        win._identifier_view.set_detected_tracks.assert_called_with(["t1"])
        win._fade_content.assert_called_with("identifier")
