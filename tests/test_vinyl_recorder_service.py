"""Regression tests for the converged vinyl recorder service."""

from __future__ import annotations

from vinyl.vinyl_recorder_service import VinylRecorderService
from vinyl.vinyl_types import (
    CaptureDevice,
    CaptureRequest,
    RecordingSession,
    StereoLevels,
)


def _device() -> CaptureDevice:
    return CaptureDevice(
        device_id=100,
        name="USB Audio CODEC",
        backend="ffmpeg-alsa",
        source="hw:1,0",
        is_usb=True,
        is_turntable=True,
        channels=2,
        sample_rate=96000,
    )


def test_riaa_is_never_enabled_implicitly():
    request = CaptureRequest(
        device=_device(),
        output_path="/tmp/test.wav",
        sample_rate=96000,
        bit_depth=24,
        channels=2,
        dsp_filters=[],
    )
    command = VinylRecorderService.build_command(request)
    filter_chain = command[command.index("-af") + 1]
    assert "equalizer=" not in filter_chain


def test_explicit_riaa_alias_builds_filter_chain():
    request = CaptureRequest(
        device=_device(),
        output_path="/tmp/test.wav",
        sample_rate=96000,
        bit_depth=24,
        channels=2,
        dsp_filters=["riaa"],
    )
    command = VinylRecorderService.build_command(request)
    filter_chain = command[command.index("-af") + 1]
    assert "equalizer=f=50" in filter_chain


def test_wav_bit_depth_selects_correct_pcm_codec():
    for bit_depth, expected in (
        (16, "pcm_s16le"),
        (24, "pcm_s24le"),
        (32, "pcm_s32le"),
    ):
        request = CaptureRequest(
            device=_device(),
            output_path=f"/tmp/test-{bit_depth}.wav",
            bit_depth=bit_depth,
        )
        command = VinylRecorderService.build_command(request)
        assert expected in command


def test_marker_at_zero_is_not_replaced_by_elapsed_time():
    service = VinylRecorderService()
    service.active_session = RecordingSession(
        session_id="test",
        input_device=_device(),
        output_path="/tmp/test.wav",
        start_time=1.0,
        status="recording",
    )
    service.is_recording = True

    result = service.add_marker(timestamp=0.0, label="Inicio")

    assert result["success"]
    assert result["marker"]["timestamp"] == 0.0


def test_status_exposes_stereo_levels_and_legacy_scalar():
    service = VinylRecorderService()
    service.active_session = RecordingSession(
        session_id="test",
        input_device=_device(),
        output_path="/tmp/test.wav",
        status="recording",
        levels=StereoLevels(
            left_peak_dbfs=-3.0,
            right_peak_dbfs=-5.0,
            left_rms_dbfs=-18.0,
            right_rms_dbfs=-19.0,
        ),
    )
    service.is_recording = True

    status = service.get_recording_status()

    assert status["levels"]["left_peak_dbfs"] == -3.0
    assert status["levels"]["right_rms_dbfs"] == -19.0
    assert status["level"] == -3.0


def test_legacy_stop_clears_partial_session():
    service = VinylRecorderService()
    service.is_recording = True

    result = service.stop_recording()

    assert result["success"]
    assert service.is_recording is False
