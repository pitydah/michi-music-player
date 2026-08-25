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
        # conservative defaults: UNKNOWN != TRUE — implemented adapters
        # explicitly supply truthful capabilities
        assert caps.local_file_playback is False
        assert caps.seek is False
        assert caps.pause is False
        assert caps.volume is False
        assert caps.mute is False
        # M11.4/M11.5 capabilities must NOT exist here
        for forbidden in ("dsd", "bit_perfect", "exclusive", "sample_rates"):
            assert not hasattr(caps, forbidden)
            assert not hasattr(AudioEngineState(), forbidden)

    def test_implemented_adapter_supplies_truthful_capabilities(self):
        from michi.infrastructure.audio_engines.providers import QtEngineProvider

        caps = QtEngineProvider().probe().capabilities
        assert caps.local_file_playback is True
        assert caps.seek is True
        assert caps.pause is True
        assert caps.volume is True
        assert caps.mute is True


class TestActivationSemantics:
    """AVAILABLE != IMPLEMENTED != ACTIVATABLE — regression-locked."""

    def test_available_not_implemented_not_activatable(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.GSTREAMER,
            display_name="GStreamer",
            available=True,
            implemented=False,
            implementation_reason="adapter pendiente (M11.3C)",
        )
        assert desc.available is True
        assert desc.implemented is False
        assert desc.can_activate is False
        assert "M11.3C" in desc.activation_blocker

    def test_unavailable_implemented_not_activatable(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.MPD,
            display_name="MPD",
            available=False,
            unavailable_reason="mpd executable no encontrado",
            implemented=True,
        )
        assert desc.can_activate is False
        assert "mpd" in desc.activation_blocker

    def test_available_implemented_activatable(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.QT_MULTIMEDIA,
            display_name="Qt Multimedia",
            available=True,
            implemented=True,
        )
        assert desc.can_activate is True
        assert desc.activation_blocker is None

    def test_can_activate_implies_no_blocker(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.QT_MULTIMEDIA,
            display_name="Qt",
            available=True,
            implemented=True,
        )
        assert desc.can_activate is True
        assert desc.activation_blocker is None

    def test_unavailable_default_reason(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.GSTREAMER,
            display_name="GStreamer",
            available=False,
        )
        assert desc.activation_blocker == "runtime unavailable"

    def test_unimplemented_default_reason(self):
        desc = AudioEngineDescriptor(
            engine_id=AudioEngineId.GSTREAMER,
            display_name="GStreamer",
            available=True,
            implemented=False,
        )
        assert desc.activation_blocker == "engine adapter not implemented"


class TestStateImmutability:
    def test_state_is_frozen(self):
        state = AudioEngineState()
        with __import__("pytest").raises(Exception):
            state.selected_engine_id = AudioEngineId.MPD

    def test_default_selected_is_qt(self):
        assert AudioEngineState().selected_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_default_active_is_none(self):
        assert AudioEngineState().active_engine_id is None

    def test_initial_lifecycle_is_uninitialized(self):
        """Startup before activation — NOT 'Qt unavailable'."""
        state = AudioEngineState()
        assert state.lifecycle == AudioEngineLifecycle.UNINITIALIZED
        assert AudioEngineLifecycle.UNINITIALIZED.value == "uninitialized"

    def test_lifecycle_is_engine_slot_not_playback(self):
        """The lifecycle axis never describes PlaybackStatus."""
        assert AudioEngineLifecycle.UNINITIALIZED not in PlaybackStatus
        assert AudioEngineLifecycle.READY.value == "ready"
        # READY + STOPPED playback is a valid combination (documented)
        state = AudioEngineState(
            selected_engine_id=AudioEngineId.QT_MULTIMEDIA,
            active_engine_id=AudioEngineId.QT_MULTIMEDIA,
            lifecycle=AudioEngineLifecycle.READY,
        )
        assert state.lifecycle == AudioEngineLifecycle.READY


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


class TestObserverIsolation:
    """AR-18: a failing state observer must not corrupt engine transactions."""

    def test_failing_subscriber_does_not_break_transaction(self):
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService

        service = AudioEngineService(AudioEngineRegistry([]))
        seen = []

        def boom():
            raise RuntimeError("qml bridge hiccup")

        service.subscribe_changed(boom)
        service.subscribe_changed(lambda: seen.append(1))
        # commit must succeed and remaining observers still run
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        assert seen == [1]
        assert service.state.lifecycle == AudioEngineLifecycle.READY
        assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_multiple_failing_subscribers_all_isolated(self):
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService

        service = AudioEngineService(AudioEngineRegistry([]))

        def boom1():
            raise RuntimeError("boom1")

        def boom2():
            raise RuntimeError("boom2")

        seen = []
        service.subscribe_changed(boom1)
        service.subscribe_changed(boom2)
        service.subscribe_changed(lambda: seen.append("ok"))
        service.mark_initializing(AudioEngineId.MPD)
        assert seen == ["ok"]
