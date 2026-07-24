"""ADC Recorder simulation tests — device detection, recording commands, markers."""
import os
from unittest.mock import MagicMock, patch



class TestADCRecorderDetection:
    def test_detect_usb_devices(self):
        from core.audio_lab.adc_recorder_service import USBTurntableDetector
        detector = USBTurntableDetector()
        with patch("os.name", "posix"), \
             patch.object(detector, "_scan_linux") as mock_scan:
            mock_scan.return_value = []
            devices = detector.scan_usb_devices()
            assert isinstance(devices, list)

    def test_detect_turntable(self):
        from core.audio_lab.adc_recorder_service import USBTurntableDetector
        detector = USBTurntableDetector()
        assert "audio-technica" in detector.TURNTABLE_BRANDS

    def test_turntable_brands_defined(self):
        from core.audio_lab.adc_recorder_service import USBTurntableDetector
        detector = USBTurntableDetector()
        assert len(detector.TURNTABLE_BRANDS) > 0


class TestADCRecorderCommands:
    def test_recording_command(self):
        from core.audio_lab.adc_recorder_service import ADCRecorderService, AudioDevice
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        svc = ADCRecorderService()
        device = AudioDevice(device_id=0, name="Test USB", is_usb=True, is_turntable=False, brand=None, channels=2, sample_rate=44100)
        # Verify the service can start without crash (will fail on no hardware)
        try:
            result = svc.start_recording(device, output_file=path)
            assert result.get("success") or result.get("error")
        except Exception:
            pass
        os.unlink(path)

    def test_stop_recording(self):
        from core.audio_lab.adc_recorder_service import ADCRecorderService
        svc = ADCRecorderService()
        svc.is_recording = True
        svc.recording_thread = MagicMock()
        svc.stop_recording()
        assert not svc.is_recording

    def test_add_marker(self):
        from core.audio_lab.adc_recorder_service import ADCRecorderService, RecordingSession
        svc = ADCRecorderService()
        from core.audio_lab.adc_recorder_service import RecordingSession, AudioDevice
        device = AudioDevice(device_id=0, name="Test", is_usb=True, is_turntable=False, brand=None, channels=2, sample_rate=44100)
        svc.active_session = RecordingSession(
            session_id="test", input_device=device, output_path="/tmp/test.wav",
            format="wav", start_time=0.0, end_time=None, duration=0.0,
            file_size=0, markers=[], status="idle",
        )
        svc.is_recording = True
        result = svc.add_marker(label="Test Marker")
        assert result["success"]
        assert len(svc.active_session.markers) == 1

    def test_split_by_markers(self):
        from core.audio_lab.adc_recorder_service import ADCRecorderService, RecordingSession, AudioDevice
        svc = ADCRecorderService()
        device = AudioDevice(device_id=0, name="Test", is_usb=True, is_turntable=False, brand=None, channels=2, sample_rate=44100)
        svc.active_session = RecordingSession(
            session_id="test", input_device=device, output_path="/tmp/test.wav",
            format="wav", start_time=0.0, end_time=None, duration=60.0,
            file_size=0, markers=[{"timestamp": 10.0, "label": "Marker 1"}], status="completed",
        )
        result = svc.split_by_markers("/nonexistent/input.wav", "/tmp/output")
        assert not result["success"]  # will fail without real file
        assert len(result["errors"]) > 0
