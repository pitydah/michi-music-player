"""Tests for IdentifierController — source-aware listening, detection routing."""
from unittest.mock import MagicMock, patch

import pytest

from recognition.identifier_controller import (
    IdentifierController, LISTEN_SOURCES, LOCAL_SOURCES)


@pytest.fixture
def db():
    d = MagicMock()
    d.find_detected_track_recent = MagicMock(return_value=None)
    return d


@pytest.fixture
def detection_service():
    return MagicMock()


@pytest.fixture
def ctrl(qapp, db, detection_service):
    return IdentifierController(db, detection_service)


class TestInitialization:
    def test_starts_disabled(self, ctrl):
        assert ctrl.enabled is False
        assert ctrl.current_source_type == ""

    def test_wires_detection_signals(self, ctrl, detection_service):
        assert detection_service.track_detected.connect.called
        assert detection_service.detection_failed.connect.called
        assert detection_service.provider_changed.connect.called

    def test_creates_provider_manager(self, ctrl):
        assert ctrl._provider_mgr is not None

    def test_creates_matcher(self, ctrl):
        assert ctrl._matcher is not None

    def test_loads_api_keys_from_settings(self, db):
        with patch("core.settings_manager.get") as mock_get:
            mock_get.return_value = "test_key"
            with patch("recognition.identifier_controller.ProviderManager") as mock_pm:
                pm = MagicMock()
                mock_pm.return_value = pm
                IdentifierController(db, MagicMock())
                assert pm.set_api_key.call_count >= 1


class TestShouldListen:
    def test_radio_should_listen(self):
        assert IdentifierController._should_listen("radio") is True

    def test_navidrome_should_listen(self):
        assert IdentifierController._should_listen("navidrome") is True

    def test_local_file_should_not_listen(self):
        assert IdentifierController._should_listen("local_file") is False

    def test_device_file_should_not_listen(self):
        assert IdentifierController._should_listen("device_file") is False

    def test_unknown_source_should_not_listen(self):
        assert IdentifierController._should_listen("unknown") is False

    def test_empty_source_should_not_listen(self):
        assert IdentifierController._should_listen("") is False

    def test_listen_sources_complete(self):
        for s in ("radio", "navidrome", "jellyfin", "remote_stream"):
            assert s in LISTEN_SOURCES

    def test_local_sources_complete(self):
        for s in ("local_file", "device_file"):
            assert s in LOCAL_SOURCES


class TestSetCurrentTrack:
    def test_radio_source_starts_listening(self, ctrl, detection_service):
        ctrl.enabled = True
        ctrl.set_current_track(source_type="radio", source_label="My Radio",
                                uri="http://stream", title="Song", artist="A")
        detection_service.start.assert_called_with(
            source="radio", source_label="My Radio", source_uri="http://stream")

    def test_local_file_pauses(self, ctrl, detection_service):
        ctrl._current_source_type = "radio"
        ctrl.enabled = True
        detection_service.stop.reset_mock()
        ctrl.set_current_track(source_type="local_file")
        detection_service.stop.assert_called_once()

    def test_unchanged_source_type_does_not_start_when_disabled(self, ctrl, detection_service):
        detection_service.start.reset_mock()
        ctrl.set_current_track(source_type="radio")
        detection_service.start.assert_not_called()

    def test_emits_source_changed(self, ctrl):
        results = []
        ctrl.source_changed.connect(lambda t, lbl: results.append((t, lbl)))
        ctrl.set_current_track(source_type="radio", source_label="My Radio")
        assert len(results) == 1
        assert results[0] == ("radio", "My Radio")


class TestEnabledSetter:
    def test_enabling_starts_when_source_is_listenable(self, ctrl, detection_service):
        ctrl._current_source_type = "radio"
        ctrl.enabled = True
        detection_service.start.assert_called_once()

    def test_enabling_does_not_start_when_source_is_local(self, ctrl, detection_service):
        ctrl._current_source_type = "local_file"
        ctrl.enabled = True
        detection_service.start.assert_not_called()

    def test_disabling_stops(self, ctrl, detection_service):
        ctrl._current_source_type = "radio"
        ctrl.enabled = False
        detection_service.stop.assert_called_once()


class TestDetectionResults:
    def test_on_detection_result_emits_detected(self, ctrl):
        ctrl._current_source_type = "radio"
        ctrl._matcher.match = MagicMock(return_value={
            "filepath": "", "status": "not_found"})
        results = []
        ctrl.detected.connect(lambda r: results.append(r))
        track = MagicMock()
        track.title = "Detected Song"
        track.artist = "Detected Artist"
        track.album = "Detected Album"
        track.provider = "shazamio"
        ctrl._on_detection_result(track)
        assert len(results) == 1
        assert results[0]["title"] == "Detected Song"
        assert results[0]["artist"] == "Detected Artist"
        assert results[0]["provider"] == "shazamio"

    def test_on_detection_result_calls_matcher(self, ctrl):
        ctrl._current_source_type = "radio"
        ctrl._matcher.match = MagicMock(return_value={
            "filepath": "/found/song.flac", "status": "found"})
        track = MagicMock()
        track.title = "Song"
        track.artist = "Artist"
        track.album = ""
        ctrl._on_detection_result(track)
        ctrl._matcher.match.assert_called_with(
            "Song", "Artist", "", source_type="radio")

    def test_on_detection_result_uses_history_for_dedup(self, ctrl):
        ctrl._history = MagicMock()
        ctrl._history.get_recent.return_value = {"title": "Song"}
        track = MagicMock()
        track.title = "Song"
        track.artist = "Artist"
        results = []
        ctrl.detected.connect(lambda r: results.append(r))
        ctrl._on_detection_result(track)
        assert len(results) == 0

    def test_on_detection_failed_logs(self, ctrl):
        ctrl._on_detection_failed("error msg")


class TestSelectProvider:
    def test_select_provider_updates_both(self, ctrl, detection_service):
        pm = MagicMock()
        ctrl._provider_mgr = pm
        ctrl.select_provider("audd")
        pm.select_provider.assert_called_with("audd")
        detection_service.select_provider.assert_called_with("audd")


class TestStop:
    def test_stop_disables_and_stops(self, ctrl, detection_service):
        ctrl.stop()
        assert ctrl.enabled is False
        detection_service.stop.assert_called_once()


class TestIdentifyOnce:
    def test_identify_once_when_enabled(self, ctrl, detection_service):
        ctrl._enabled = True
        ctrl.identify_once()
        detection_service.identify_once.assert_called_once()

    def test_identify_once_when_disabled(self, ctrl, detection_service):
        ctrl._enabled = False
        ctrl.identify_once()
        detection_service.identify_once.assert_not_called()
