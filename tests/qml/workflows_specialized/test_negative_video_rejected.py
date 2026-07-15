"""MX: Negative — video files rejected in audio-only workflows."""
from __future__ import annotations

from ui_qml_bridge.devices_bridge import DevicesBridge


def test_video_mp4_rejected():
    bridge = DevicesBridge()
    result = bridge.validateAudioFile("/path/video.mp4")
    assert result.get("ok") is False
    assert result.get("error") == "VIDEO_NOT_SUPPORTED"


def test_video_avi_rejected():
    bridge = DevicesBridge()
    result = bridge.validateAudioFile("/path/video.avi")
    assert result.get("ok") is False
    assert result.get("error") == "VIDEO_NOT_SUPPORTED"


def test_video_mkv_rejected():
    from ui_qml_bridge.devices_bridge import _VIDEO_EXTS, _AUDIO_EXTS
    assert ".mp4" in _VIDEO_EXTS
    assert ".avi" in _VIDEO_EXTS
    assert ".mkv" in _VIDEO_EXTS
    assert ".mov" in _VIDEO_EXTS
    assert ".webm" in _VIDEO_EXTS
    assert ".m4v" in _VIDEO_EXTS
    assert ".wmv" in _VIDEO_EXTS
    assert ".flac" in _AUDIO_EXTS
    assert ".mp3" in _AUDIO_EXTS
    assert ".wav" in _AUDIO_EXTS


def test_audio_accepted():
    bridge = DevicesBridge()
    result = bridge.validateAudioFile("/path/track.flac")
    assert result.get("ok") is True


def test_audio_mp3_accepted():
    bridge = DevicesBridge()
    result = bridge.validateAudioFile("/path/track.mp3")
    assert result.get("ok") is True
