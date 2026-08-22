"""M11.3A: AudioTransportRouter gates.

Stable identity across engine switches: consumers subscribe ONCE to the
router; binding changes re-route events without duplicate delivery, stale
callbacks or loss. Deterministic unavailable failure without backend.
"""

from pathlib import Path

import pytest

from michi.application.audio_transport_router import (
    AudioTransportRouter,
    AudioTransportUnavailableError,
)
from michi.application.ports import AudioPort
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus


class RecordingBackend(AudioPort):
    """Fake AudioPort: records commands; can fire events on demand."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.commands: list[str] = []
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._st: list = []

    def load(self, file_path: Path) -> None:
        self.commands.append(f"load:{file_path.name}")

    def play(self) -> None:
        self.commands.append("play")

    def pause(self) -> None:
        self.commands.append("pause")

    def resume(self) -> None:
        self.commands.append("resume")

    def stop(self) -> None:
        self.commands.append("stop")

    def set_volume(self, value: int) -> None:
        self.commands.append(f"volume:{value}")

    def set_muted(self, muted: bool) -> None:
        self.commands.append(f"muted:{muted}")

    def seek(self, position_ms: int) -> None:
        self.commands.append(f"seek:{position_ms}")

    def position(self) -> int:
        self.commands.append("position")
        return 100

    def duration(self) -> int:
        self.commands.append("duration")
        return 200

    def subscribe_end_of_media(self, cb) -> None:
        self._eom.append(cb)

    def unsubscribe_end_of_media(self, cb) -> None:
        if cb in self._eom:
            self._eom.remove(cb)

    def subscribe_position_changed(self, cb) -> None:
        self._pos.append(cb)

    def unsubscribe_position_changed(self, cb) -> None:
        if cb in self._pos:
            self._pos.remove(cb)

    def subscribe_duration_changed(self, cb) -> None:
        self._dur.append(cb)

    def unsubscribe_duration_changed(self, cb) -> None:
        if cb in self._dur:
            self._dur.remove(cb)

    def subscribe_media_accepted(self, cb) -> None:
        self._acc.append(cb)

    def unsubscribe_media_accepted(self, cb) -> None:
        if cb in self._acc:
            self._acc.remove(cb)

    def subscribe_media_rejected(self, cb) -> None:
        self._rej.append(cb)

    def unsubscribe_media_rejected(self, cb) -> None:
        if cb in self._rej:
            self._rej.remove(cb)

    def subscribe_playback_state_changed(self, cb) -> None:
        self._st.append(cb)

    def unsubscribe_playback_state_changed(self, cb) -> None:
        if cb in self._st:
            self._st.remove(cb)

    # event faking
    def fire_end_of_media(self) -> None:
        for cb in list(self._eom):
            cb()

    def fire_position(self, ms: int) -> None:
        for cb in list(self._pos):
            cb(ms)

    def fire_media_accepted(self, path: Path) -> None:
        for cb in list(self._acc):
            cb(path)

    def fire_media_rejected(self, path: Path, reason: str) -> None:
        for cb in list(self._rej):
            cb(path, reason)

    def fire_state(self, status: PlaybackStatus) -> None:
        for cb in list(self._st):
            cb(status)


class TestCommandDelegation:
    def test_bound_commands_delegate_to_backend(self):
        router = AudioTransportRouter()
        a = RecordingBackend("A")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        router.load(Path("/m/x.mp3"))
        router.play()
        router.pause()
        router.seek(42)
        router.set_volume(80)
        router.set_muted(True)
        assert a.commands == [
            "load:x.mp3",
            "play",
            "pause",
            "seek:42",
            "volume:80",
            "muted:True",
        ]
        assert router.position() == 100
        assert router.duration() == 200

    def test_switch_routes_commands_only_to_new_backend(self):
        router = AudioTransportRouter()
        a = RecordingBackend("A")
        b = RecordingBackend("B")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        router.play()
        router.bind(AudioEngineId.GSTREAMER, b)
        router.pause()
        router.seek(1)
        assert a.commands == ["play"]
        assert b.commands == ["pause", "seek:1"]

    def test_no_backend_raises_deterministically(self):
        router = AudioTransportRouter()
        with pytest.raises(AudioTransportUnavailableError):
            router.play()
        with pytest.raises(AudioTransportUnavailableError):
            router.load(Path("/m/x.mp3"))
        with pytest.raises(AudioTransportUnavailableError):
            router.seek(10)
        with pytest.raises(AudioTransportUnavailableError):
            router.position()
        with pytest.raises(AudioTransportUnavailableError):
            router.duration()

    def test_unbind_raises_afterwards(self):
        router = AudioTransportRouter()
        a = RecordingBackend("A")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        router.unbind()
        with pytest.raises(AudioTransportUnavailableError):
            router.play()


class TestEventRouting:
    def _router_with_consumer(self):
        router = AudioTransportRouter()
        events = []
        router.subscribe_end_of_media(lambda: events.append("eom"))
        router.subscribe_position_changed(lambda ms: events.append(f"pos:{ms}"))
        router.subscribe_media_accepted(lambda p: events.append(f"acc:{p.name}"))
        router.subscribe_media_rejected(lambda p, r: events.append(f"rej:{p.name}:{r}"))
        router.subscribe_playback_state_changed(lambda s: events.append(f"st:{s.name}"))
        return router, events

    def test_events_flow_from_bound_backend(self):
        router, events = self._router_with_consumer()
        a = RecordingBackend("A")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        a.fire_end_of_media()
        a.fire_position(5)
        a.fire_media_accepted(Path("/m/x.mp3"))
        a.fire_media_rejected(Path("/m/y.mp3"), "boom")
        a.fire_state(PlaybackStatus.PLAYING)
        assert events == [
            "eom",
            "pos:5",
            "acc:x.mp3",
            "rej:y.mp3:boom",
            "st:PLAYING",
        ]

    def test_switch_detaches_old_backend_callbacks(self):
        router, events = self._router_with_consumer()
        a = RecordingBackend("A")
        b = RecordingBackend("B")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        router.bind(AudioEngineId.GSTREAMER, b)
        a.fire_end_of_media()  # old engine: MUST NOT reach the consumer
        b.fire_end_of_media()  # new engine: MUST reach exactly once
        assert events == ["eom"]

    def test_rebind_same_backend_no_duplicates(self):
        router, events = self._router_with_consumer()
        a = RecordingBackend("A")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)  # idempotent
        a.fire_media_accepted(Path("/m/x.mp3"))
        assert events == ["acc:x.mp3"]

    def test_unbind_blocks_all_callbacks(self):
        router, events = self._router_with_consumer()
        a = RecordingBackend("A")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        router.unbind()
        a.fire_end_of_media()
        a.fire_position(1)
        a.fire_media_accepted(Path("/m/x.mp3"))
        assert events == []

    def test_consumer_subscription_survives_switch(self):
        """PlaybackService-style: register ONCE, keep receiving after switch."""
        router, events = self._router_with_consumer()
        a = RecordingBackend("A")
        b = RecordingBackend("B")
        router.bind(AudioEngineId.QT_MULTIMEDIA, a)
        a.fire_position(1)
        router.bind(AudioEngineId.GSTREAMER, b)
        b.fire_position(2)
        assert events == ["pos:1", "pos:2"]

    def test_bound_engine_id_tracked(self):
        router = AudioTransportRouter()
        router.bind(AudioEngineId.MPD, RecordingBackend("M"))
        assert router.bound_engine_id == AudioEngineId.MPD
        router.unbind()
        assert router.bound_engine_id is None


class TestRouterArchitecture:
    def test_router_is_audio_port_and_binding_port(self):
        router = AudioTransportRouter()
        from michi.application.audio_transport_router import (
            AudioTransportBindingPort,
        )

        assert isinstance(router, AudioPort)
        assert isinstance(router, AudioTransportBindingPort)

    def test_binding_not_part_of_audio_port(self):
        assert not hasattr(AudioPort, "bind")
        assert not hasattr(AudioPort, "unbind")

    def test_router_framework_free(self):
        import inspect

        from michi.application import audio_transport_router as mod

        src = inspect.getsource(mod)
        for forbidden in ("PySide6", "gi.", "sqlite3", "subprocess", "socket"):
            assert forbidden not in src
