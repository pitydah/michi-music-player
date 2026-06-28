"""Tests for DetectionService — lifecycle, identify, capture orchestration."""
from unittest.mock import MagicMock

import pytest

from recognition.detection_service import DetectionService


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def provider_mgr():
    from recognition.provider_manager import ProviderManager
    mgr = ProviderManager()
    mgr._recognizer = MagicMock()
    # Set current_provider without signals
    mgr._current_provider = "test_provider"
    return mgr


@pytest.fixture
def service(qapp, db, provider_mgr):
    return DetectionService(db, provider_mgr)


class TestInitialization:
    def test_starts_idle(self, service):
        assert service.status == "idle"
        assert service.is_active is False

    def test_provider_name_delegates(self, service, provider_mgr):
        assert service.provider_name == "test_provider"

    def test_recognizer_property(self, service, provider_mgr):
        assert service.recognizer is provider_mgr.recognizer

    def test_provider_changed_signal_wired(self, service, provider_mgr):
        results = []
        service.provider_changed.connect(lambda n, ok: results.append((n, ok)))
        provider_mgr.provider_changed.emit("shazamio", True)
        assert len(results) == 1
        assert results[0] == ("shazamio", True)

    def test_set_recognizer(self, service):
        recognizer = MagicMock()
        service.set_recognizer(recognizer)
        assert service._provider_mgr._recognizer is recognizer


class TestLifecycle:
    def test_start_sets_active(self, service):
        service.start(source="radio")
        assert service.is_active is True
        assert service.status == "listening"

    def test_start_creates_capture_timer(self, service):
        service.start(source="radio")
        assert service._capture_timer is not None
        assert service._capture_timer.isActive() is True

    def test_stop_clears_active(self, service):
        service.start(source="radio")
        service.stop()
        assert service.is_active is False
        assert service.status == "idle"

    def test_stop_stops_timer(self, service):
        service.start(source="radio")
        service.stop()
        assert service._capture_timer.isActive() is False

    def test_toggle_starts_when_stopped(self, service):
        service.toggle(source="radio")
        assert service.is_active is True

    def test_toggle_stops_when_active(self, service):
        service.start(source="radio")
        service.toggle()
        assert service.is_active is False

    def test_second_start_is_idempotent(self, service):
        service._capture = MagicMock()
        service.start(source="radio")
        timer = service._capture_timer
        service.start(source="radio")
        assert service._capture_timer is timer

    def test_select_provider(self, service, provider_mgr):
        service.select_provider("audd")
        assert provider_mgr.current_provider == "audd"


class TestIdentifyOnce:
    def test_skips_when_inactive(self, service):
        service._identifying = False
        service.identify_once()
        assert service._identifying is False

    def test_skips_when_already_identifying(self, service):
        service._active = True
        service._identifying = True
        service.identify_once()
        assert service._identifying is True

    def test_uses_worker_manager_if_available(self, service):
        service._active = True
        service._capture = MagicMock()
        worker_mgr = MagicMock()
        service.set_worker_manager(worker_mgr)
        service.identify_once()
        worker_mgr.identify.assert_called_once()

    def test_sync_fallback_identifies(self, service):
        service._active = True
        service._capture = MagicMock()
        service._capture.is_available = True
        service._capture.capture_once.return_value = b"fake_audio"
        service.recognizer.identify.return_value = {"title": "Song", "artist": "A"}
        service.identify_once()
        assert service._identifying is False
        assert service._detections_total == 1

    def test_sync_fallback_no_match(self, service):
        service._active = True
        service._capture = MagicMock()
        service._capture.is_available = True
        service._capture.capture_once.return_value = b"fake_audio"
        service.recognizer.identify.return_value = None
        results = []
        service.detection_failed.connect(lambda e: results.append(e))
        service.identify_once()
        assert len(results) == 1
        assert "Sin coincidencia" in results[0]

    def test_sync_fallback_capture_unavailable(self, service):
        service._active = True
        service._capture = MagicMock()
        service._capture.is_available = False
        service.recognizer.identify.return_value = {"title": "Song", "artist": "A"}
        service.identify_once()
        assert service._detections_total == 1


class TestWorkerManager:
    def test_set_worker_manager_connects_signals(self, service):
        mgr = MagicMock()
        service.set_worker_manager(mgr)
        assert mgr.identify_done.connect.called
        assert mgr.identify_error.connect.called

    def test_on_worker_identify_with_result(self, service):
        result = {"title": "T", "artist": "A", "provider": "test"}
        service._on_worker_identify(result)
        assert service._detections_total == 1

    def test_on_worker_identify_no_result(self, service):
        results = []
        service.detection_failed.connect(lambda e: results.append(e))
        service._on_worker_identify(None)
        assert len(results) == 1
        assert results[0] == "Sin coincidencia"

    def test_on_worker_identify_clears_flag(self, service):
        service._identifying = True
        service._on_worker_identify({"title": "T", "artist": "A"})
        assert service._identifying is False


class TestHandleIdentified:
    def test_creates_detected_track(self, service):
        service._handle_identified({"title": "T", "artist": "A", "album": "Al",
                                    "source": "radio", "provider": "shazam",
                                    "confidence": 0.9})
        assert service._detections_total == 1

    def test_saves_to_db(self, service, db):
        service._handle_identified({"title": "T", "artist": "A"})
        db.add_detected_track.assert_called_once()

    def test_emits_track_detected(self, service):
        results = []
        service.track_detected.connect(lambda t: results.append(t))
        service._handle_identified({"title": "T", "artist": "A"})
        assert len(results) == 1
        assert results[0].title == "T"

    def test_save_track_fallback_on_exception(self, service, db):
        db.add_detected_track.side_effect = [Exception("first fail"), None]
        service._save_track(MagicMock(title="T", artist="A"))
        assert db.add_detected_track.call_count == 2


class TestManualDetection:
    def test_add_manual_creates_track(self, service, db):
        db.find_detected_track_recent.return_value = None
        service.add_manual_detection("Manual Song", "Manual Artist")
        db.add_detected_track.assert_called_once()

    def test_add_manual_skips_duplicate(self, service, db):
        db.find_detected_track_recent.return_value = {"title": "Manual Song"}
        service.add_manual_detection("Manual Song", "Manual Artist")
        db.add_detected_track.assert_not_called()
        assert service._duplicates_avoided == 1

    def test_add_manual_emits_track_detected(self, service, db):
        db.find_detected_track_recent.return_value = None
        results = []
        service.track_detected.connect(lambda t: results.append(t))
        service.add_manual_detection("Manual Song", "Manual Artist")
        assert len(results) == 1
        assert results[0].provider == "manual"


class TestDiagnostics:
    def test_diagnostics_returns_dict(self, service):
        diag = service.diagnostics()
        assert isinstance(diag, dict)
        assert "status" in diag
        assert "active" in diag
        assert "provider" in diag
        assert "detections_total" in diag
        assert "duplicates_avoided" in diag

    def test_diagnostics_tracks_counts(self, service):
        service._detections_total = 5
        service._duplicates_avoided = 2
        diag = service.diagnostics()
        assert diag["detections_total"] == 5
        assert diag["duplicates_avoided"] == 2
