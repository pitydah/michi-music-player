"""M11.3A: multi-engine audio domain contract gates.

AudioEngineId canonical + persistence-safe; lifecycle distinct from
PlaybackStatus; descriptor honesty (installed != implemented); state
distinguishes SELECTED from ACTIVE; domain imports nothing outside stdlib.
"""

import inspect

from michi.domain.audio_engine import (
    AudioEngineCapabilities,
    AudioEngineDescriptor,
    AudioEngineId,
    AudioEngineLifecycle,
    AudioEngineState,
)
from michi.domain.playback import PlaybackStatus


class TestAudioEngineId:
    def test_canonical_ids(self):
        assert AudioEngineId.QT_MULTIMEDIA.value == "qt_multimedia"
        assert AudioEngineId.GSTREAMER.value == "gstreamer"
        assert AudioEngineId.MPD.value == "mpd"

    def test_three_and_only_three(self):
        assert {e.value for e in AudioEngineId} == {
            "qt_multimedia",
            "gstreamer",
            "mpd",
        }


class TestLifecycle:
    def test_distinct_from_playback_status(self):
        """Engine lifecycle is a different axis than PlaybackStatus."""
        lifecycle_values = {e.value for e in AudioEngineLifecycle}
        playback_values = {e.value for e in PlaybackStatus}
        assert not lifecycle_values & playback_values
        assert "ready" in lifecycle_values
        assert "failed" in lifecycle_values

    def test_valid_combinations(self):
        # READY engine + STOPPED playback is valid (documented contract)
        state = AudioEngineState(
            selected_engine_id=AudioEngineId.GSTREAMER,
            active_engine_id=AudioEngineId.QT_MULTIMEDIA,
            lifecycle=AudioEngineLifecycle.READY,
        )
        assert state.active_engine_id == AudioEngineId.QT_MULTIMEDIA


class TestDescriptor:
    def test_selected_differs_from_active(self):
        """SELECTED GSTREAMER + unavailable + active QT is a valid state."""
        state = AudioEngineState(
            selected_engine_id=AudioEngineId.GSTREAMER,
            active_engine_id=AudioEngineId.QT_MULTIMEDIA,
            lifecycle=AudioEngineLifecycle.READY,
        )
        assert state.selected_engine_id == AudioEngineId.GSTREAMER
        assert state.active_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_installed_not_implemented(self):
        """installed != implemented — a provider may be present but its
        adapter not yet built."""
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.GSTREAMER,
            display_name="GStreamer",
            available=True,
            implemented=False,
        )
        assert desc.available is True
        assert desc.implemented is False

    def test_unavailable_has_honest_reason(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.MPD,
            display_name="MPD",
            available=False,
            unavailable_reason="mpd executable not found",
        )
        assert desc.available is False
        assert "mpd" in desc.unavailable_reason

    def test_capabilities_are_transport_only(self):
        caps = AudioEngineCapabilities()
        assert caps.local_file_playback is True
        assert caps.seek and caps.pause and caps.volume and caps.mute
        # M11.4/M11.5 capabilities must NOT exist here
        for forbidden in ("dsd", "bit_perfect", "exclusive", "sample_rates"):
            assert not hasattr(caps, forbidden)
            assert not hasattr(AudioEngineState(), forbidden)


class TestStateImmutability:
    def test_state_is_frozen(self):
        state = AudioEngineState()
        with __import__("pytest").raises(Exception):
            state.selected_engine_id = AudioEngineId.MPD

    def test_default_selected_is_qt(self):
        assert AudioEngineState().selected_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_default_active_is_none(self):
        assert AudioEngineState().active_engine_id is None


class TestDomainPurity:
    def test_domain_imports_no_framework(self):
        import michi.domain.audio_engine as mod

        src = inspect.getsource(mod)
        for forbidden in ("PySide6", "gi.", "Gst", "sqlite3", "subprocess", "socket"):
            assert forbidden not in src, f"domain leaked {forbidden}"

    def test_no_engine_selection_on_audio_port(self):
        """AudioPort stays transport-only — no engine-selection methods."""
        from michi.application.ports import AudioPort

        for name in (
            "select_engine",
            "available_engines",
            "set_device",
            "set_output_profile",
            "set_dsd",
            "set_bitperfect",
            "engine_capabilities",
            "bind",
            "unbind",
        ):
            assert not hasattr(AudioPort, name), f"AudioPort ganó {name}"
