from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from core.audio_lab.adc_recorder_service import AudioDevice
from core.audio_lab.audio_lab_service import AudioLabService
from core.audio_lab.cd_ripper_service import CDRipperService
from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from ui_qml_bridge.route_registry import ROUTES


class FakeRecorder:
    SUPPORTED_FORMATS = ("wav", "flac")
    DSP_FILTERS = ("riaa_eq", "declicker")

    def __init__(self):
        self.device = AudioDevice(
            device_id="alsa:2,0",
            name="USB Audio",
            backend="alsa",
            capture_spec="hw:2,0",
            is_usb=True,
        )
        self.calls: list[tuple] = []
        self.active = False

    def available(self):
        return True

    def detect_devices(self):
        self.calls.append(("detect",))
        return [self.device]

    def get_recommended_device(self):
        self.calls.append(("recommended",))
        return self.device

    def start_recording(self, **kwargs):
        self.calls.append(("start", kwargs))
        self.active = True
        return {"success": True, "session_id": "session-1"}

    def pause_recording(self):
        self.calls.append(("pause",))
        return {"success": True, "status": "paused"}

    def resume_recording(self):
        self.calls.append(("resume",))
        return {"success": True, "status": "recording"}

    def stop_recording(self):
        self.calls.append(("stop",))
        self.active = False
        return {"success": True, "status": "completed"}

    def add_marker(self, timestamp=None, label=""):
        self.calls.append(("marker", timestamp, label))
        return {"success": True, "marker": {"timestamp": 0.0, "label": label or "Pista 1"}}

    def split_by_markers(self, input_file, output_dir):
        self.calls.append(("split", input_file, output_dir))
        return {"success": True, "tracks": []}

    def get_recording_status(self):
        return {"active": self.active, "status": "recording" if self.active else "idle"}


class FakeRipper:
    def capability(self):
        return {"available": True, "formats": ["flac"]}

    def detect_drives(self):
        return []

    def cancel(self):
        return {"success": True}


class FakeAudioLabService:
    def __init__(self):
        self.adc_recorder = FakeRecorder()
        self.cd_ripper = FakeRipper()
        self.started = 0

    def start(self):
        self.started += 1
        return self

    def capability_map(self):
        return {"adc_recording": True, "cd_ripping": True}

    def get_overview_data(self):
        return {"areas": {}, "dependencies": {}, "active_jobs": 0}


class FakeNavigation:
    def __init__(self):
        self.currentRoute = "audio_lab"
        self.routes: list[str] = []

    def navigate(self, route):
        self.routes.append(route)
        self.currentRoute = route


def test_audio_lab_start_is_idempotent():
    service = AudioLabService()
    service.setup = MagicMock(return_value=service)

    service.start()
    service.start()

    service.setup.assert_called_once_with()
    assert service.status()["started"] is True


def test_cddb_toc_parser_creates_real_track_count_and_durations():
    info = CDRipperService._parse_cddb_toc("deadbeef 2 150 15150 400")

    assert info is not None
    assert info.disc_id == "deadbeef"
    assert info.total_tracks == 2
    assert len(info.tracks) == 2
    assert info.tracks[0].track_number == 1
    assert info.tracks[0].duration == 200.0
    assert info.tracks[1].duration == 198.0


def test_full_cd_never_reports_success_without_toc(monkeypatch, tmp_path):
    ripper = CDRipperService()
    monkeypatch.setattr(ripper, "get_cd_info", lambda _device: None)

    result = ripper.rip_full_cd("/dev/sr0", str(tmp_path))

    assert result["success"] is False
    assert result["tracks_completed"] == 0
    assert "CD_TOC_UNAVAILABLE_OR_EMPTY" in result["errors"]


def test_bridge_reuses_same_adc_recorder_for_whole_session(tmp_path):
    service = FakeAudioLabService()
    bridge = AudioLabBridge(audio_lab_service=service)
    recorder = service.adc_recorder

    devices = bridge.detectAudioDevices()
    started = bridge.startRecording(
        devices[0]["device_id"],
        str(tmp_path / "capture.wav"),
        "wav",
        44100,
        16,
        2,
        [],
    )
    paused = bridge.pauseRecording()
    marker = bridge.addMarker("Cara A")
    stopped = bridge.stopRecording()

    assert started["ok"] is True
    assert paused["ok"] is True
    assert marker["ok"] is True
    assert stopped["ok"] is True
    assert [call[0] for call in recorder.calls] == ["detect", "detect", "start", "pause", "marker", "stop"]


def test_bridge_area_navigation_uses_registered_routes():
    service = FakeAudioLabService()
    navigation = FakeNavigation()
    bridge = AudioLabBridge(audio_lab_service=service, navigation_bridge=navigation)

    result = bridge.navigateToArea("backup")

    assert result["ok"] is True
    assert navigation.routes[-1] == "audio_lab.backup"
    assert "audio_lab.backup" in ROUTES
    assert ROUTES["audio_lab.backup"]["status"] == "experimental"


def test_capture_capabilities_are_truthful():
    bridge = AudioLabBridge(audio_lab_service=FakeAudioLabService())

    result = bridge.getCaptureCapabilities()

    assert result == {
        "available": True,
        "formats": ["wav", "flac"],
        "dsp_filters": ["riaa_eq", "declicker"],
    }


def test_audio_lab_overview_uses_real_components_and_retry_signal():
    source = Path("ui_qml/pages/audio_lab/AudioLabOverviewPage.qml").read_text(encoding="utf-8")

    assert 'import "../../components"' in source
    assert "AudioLabAreaCard" in source
    assert "onRetryRequested" in source
    assert "AreaCard {" not in source
    assert "status:" not in source or "StatusBadge" not in source  # no invalid StatusBadge.status binding


def test_notification_center_has_real_model_and_timer_contract():
    source = Path("ui_qml/components/NotificationCenter.qml").read_text(encoding="utf-8")

    assert "property var notificationItems" in source
    assert "Timer {" in source
    assert "Qt.callLater" not in source
    assert "notificationModel" not in source


def test_notification_item_dismisses_specific_id():
    source = Path("ui_qml/components/NotificationItem.qml").read_text(encoding="utf-8")

    assert "root.bridge.dismiss(root.notificationId())" in source
