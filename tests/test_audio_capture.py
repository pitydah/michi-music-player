"""Tests for AudioCaptureService — lifecycle, monitor detection, sample rate."""
from unittest.mock import MagicMock, patch

import pytest

from recognition.audio_capture_service import AudioCaptureService


@pytest.fixture
def service():
    svc = AudioCaptureService()
    svc._pya_available = True
    return svc


class TestAudioCaptureService:
    def test_capture_initializes(self):
        svc = AudioCaptureService()
        assert svc.is_active is False
        assert svc.is_available is not None

    def test_capture_start_stop(self, service):
        service.start()
        assert service.is_active is True
        service.stop()
        assert service.is_active is False

    def test_monitor_auto_detection(self):
        mock_pa = MagicMock()
        mock_pa.get_device_count.return_value = 4
        devices = [
            {"name": "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor", "maxInputChannels": 2},
            {"name": "alsa_output.pci-0000_00_1f.3.analog-stereo", "maxInputChannels": 0},
            {"name": "alsa_input.pci-0000_00_1f.3.analog-stereo", "maxInputChannels": 2},
            {"name": "digital output", "maxInputChannels": 2},
        ]
        mock_pa.get_device_info_by_index.side_effect = devices

        idx = AudioCaptureService._find_monitor_device(mock_pa)
        assert idx == 0

    def test_capture_without_audio_server(self):
        svc = AudioCaptureService()
        svc._pya_available = False
        svc.start()
        assert svc.is_active is False

    def test_capture_sample_rate_22050(self):
        from recognition.audio_capture_service import SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH
        assert SAMPLE_RATE == 22050
        assert CHANNELS == 1
        assert SAMPLE_WIDTH == 2

    @pytest.mark.recognition
    def test_capture_once_with_pyaudio(self, service):
        pyaudio = pytest.importorskip("pyaudio")
        mock_pa = MagicMock()
        mock_pa.get_device_count.return_value = 1
        mock_pa.get_device_info_by_index.return_value = {
            "name": "default.monitor",
            "maxInputChannels": 2,
        }
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"\x00\x01" * 512
        mock_pa.open.return_value = mock_stream

        with patch("pyaudio.PyAudio", return_value=mock_pa):
            result = service._capture_chunk()

        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pa.terminate.assert_called_once()

    @pytest.mark.recognition
    def test_capture_once_no_monitor(self, service):
        pytest.importorskip("pyaudio")
        mock_pa = MagicMock()
        mock_pa.get_device_count.return_value = 0
        mock_pa.get_default_input_device_info.side_effect = OSError("No device")

        with patch("pyaudio.PyAudio", return_value=mock_pa):
            result = service._capture_chunk()

        assert result is None

    def test_capture_once_pyaudio_not_available(self):
        svc = AudioCaptureService()
        svc._pya_available = False
        assert svc.capture_once() is None

    def test_start_emits_signal(self, service):
        signals = []
        service.capture_started.connect(lambda: signals.append("started"))
        service.start()
        assert signals == ["started"]

    def test_stop_emits_signal(self, service):
        signals = []
        service.capture_stopped.connect(lambda: signals.append("stopped"))
        service.start()
        service.stop()
        assert signals == ["stopped"]

    def test_double_start_noop(self, service):
        service.start()
        assert service.is_active is True
        service.start()
        assert service.is_active is True

    def test_error_when_starting_without_pyaudio(self):
        svc = AudioCaptureService()
        svc._pya_available = False
        errors = []
        svc.error_occurred.connect(lambda m: errors.append(m))
        svc.start()
        assert errors == ["PyAudio not available"]
