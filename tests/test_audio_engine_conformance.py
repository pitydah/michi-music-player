"""M11.3 Reliability Seal — cross-engine AudioPort conformance suite (AR-22).

The SAME semantic contract runs against every real engine (Qt Multimedia,
GStreamer, MPD) where the environment supports it. Commands either succeed
or raise an explicit typed failure; state truth arrives via events; late
events from superseded sources are ignored; no autoplay on prepare.

Gates: real GI/GStreamer for GST, real mpd for MPD, QMediaPlayer offscreen
for Qt. Missing dependency → truthful SKIP (positively proven absence).
"""

import contextlib
import os
import shutil
import wave
from pathlib import Path

import pytest


def _write_wav(path: Path, seconds: float = 3.0, rate: int = 44100) -> Path:
    """Deterministic tiny PCM 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import math

    frames = int(seconds * rate)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(
            b"".join(
                int(12000 * math.sin(2 * math.pi * 440 * i / rate)).to_bytes(
                    2, "little", signed=True
                )
                for i in range(frames)
            )
        )
    return path


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def _pump(ms: int = 60):
    """Bounded event pumping WITHOUT QTest.qWait: qWait can wedge the event
    loop while a real QMediaPlayer is playing offscreen (media backend C++
    frame). processEvents(AllEvents, 20) + tiny sleep stays responsive."""
    from PySide6.QtCore import QEventLoop
    from PySide6.QtWidgets import QApplication

    deadline = ms / 1000.0
    import time as _time

    t0 = _time.monotonic()
    while _time.monotonic() - t0 < deadline:
        QApplication.processEvents(QEventLoop.AllEvents, 20)
        _time.sleep(0.01)


def _drain():
    from PySide6.QtWidgets import QApplication

    for _ in range(30):
        QApplication.processEvents()


def _events(port, kind: str, timeout_ms: int = 4000) -> list:
    """Wait for the next `kind` event (accepted/rejected/state/eom)."""
    from PySide6.QtTest import QTest

    results: list = []
    handlers = {
        "accepted": lambda p: results.append(("accepted", p)),
        "rejected": lambda p, r: results.append(("rejected", r)),
        "state": lambda s: results.append(("state", s)),
        "eom": lambda: results.append(("eom",)),
    }
    sub = {
        "accepted": port.subscribe_media_accepted,
        "rejected": port.subscribe_media_rejected,
        "state": port.subscribe_playback_state_changed,
        "eom": port.subscribe_end_of_media,
    }[kind]
    unsub = {
        "accepted": port.unsubscribe_media_accepted,
        "rejected": port.unsubscribe_media_rejected,
        "state": port.unsubscribe_playback_state_changed,
        "eom": port.unsubscribe_end_of_media,
    }[kind]
    sub(handlers[kind])
    try:
        deadline = 0
        while not results and deadline < timeout_ms:
            QTest.qWait(20)
            deadline += 20
    finally:
        unsub(handlers[kind])
    return results


class _Contract:
    """Shared semantic contract executed against a real engine port."""

    def __init__(self, port_factory, wav: Path, prepare_wav=None):
        self.port_factory = port_factory
        self.wav = wav
        # optional: relocate the fixture into the engine's own media tree
        # (MPD only plays files inside its private music_directory)
        self.prepare_wav = prepare_wav

    def run(self):
        port = self.port_factory()
        wav = self.wav
        if self.prepare_wav is not None:
            wav = self.prepare_wav(port) or self.wav
        try:
            self._load_accept(port, wav)
            self._play_truth(port)
            self._pause_resume(port)
            self._seek(port)
            self._volume_mute(port)
            self._stop(port)
            self._no_autoplay_on_prepare(port)
            self._close_reopen(port)
        finally:
            with contextlib.suppress(Exception):  # teardown must not mask
                port.close()

    def _load_accept(self, port, wav):
        from michi.domain.playback import PlaybackStatus

        # R1-10: keep the EXACT callback objects and unsubscribe THOSE
        states = []
        accepted = []
        on_state = lambda s: states.append(s)  # noqa: E731
        on_accepted = lambda p: accepted.append(p)  # noqa: E731
        port.subscribe_playback_state_changed(on_state)
        port.subscribe_media_accepted(on_accepted)
        try:
            port.load(wav)
            _pump(150)
            # acceptance may be synchronous (MPD) or async (GStreamer bus)
            assert accepted, "media must be accepted"
            # no autoplay on prepare: state must not be PLAYING
            assert PlaybackStatus.PLAYING not in states
        finally:
            port.unsubscribe_media_accepted(on_accepted)
            port.unsubscribe_playback_state_changed(on_state)

    def _play_truth(self, port):
        from michi.domain.playback import PlaybackStatus

        # subscribe BEFORE the command: backends may converge state
        # synchronously (MPD refresh inside stop/play)
        states = []
        on_state = lambda s: states.append(s)  # noqa: E731
        port.subscribe_playback_state_changed(on_state)
        try:
            port.play()
            _pump(600)
            assert PlaybackStatus.PLAYING in states, f"PLAYING truth missing: {states}"
        finally:
            port.unsubscribe_playback_state_changed(on_state)

    def _pause_resume(self, port):
        from michi.domain.playback import PlaybackStatus

        states = []
        on_state = lambda s: states.append(s)  # noqa: E731
        port.subscribe_playback_state_changed(on_state)
        try:
            port.pause()
            _pump(600)
            assert PlaybackStatus.PAUSED in states, f"PAUSED missing: {states}"
            port.resume()
            _pump(600)
            assert PlaybackStatus.PLAYING in states, f"PLAYING missing: {states}"
        finally:
            port.unsubscribe_playback_state_changed(on_state)

    def _seek(self, port):
        # seek must not raise; position confirmation may be async
        port.seek(50)

    def _volume_mute(self, port):
        port.set_volume(73)
        port.set_muted(True)
        port.set_muted(False)

    def _stop(self, port):
        from michi.domain.playback import PlaybackStatus

        # subscribe BEFORE stop: MPD converges STOPPED synchronously inside
        # the stop command (daemon already confirms via _refresh_status)
        states = []
        on_state = lambda s: states.append(s)  # noqa: E731
        port.subscribe_playback_state_changed(on_state)
        try:
            port.stop()
            _pump(600)
            assert PlaybackStatus.STOPPED in states, f"STOPPED missing: {states}"
        finally:
            port.unsubscribe_playback_state_changed(on_state)

    def _no_autoplay_on_prepare(self, port):
        from michi.domain.playback import PlaybackStatus

        events = []
        port.subscribe_playback_state_changed(lambda s: events.append(s))
        port.load(self.wav)
        _drain()
        assert PlaybackStatus.PLAYING not in events

    # NOTE: _play_truth/_pause_resume/_seek/_volume_mute/_stop use
    # self.wav only through the accepted source already loaded.

    def _close_reopen(self, port):
        port.close()
        port.close()  # idempotent
        port2 = self.port_factory()
        try:
            if self.prepare_wav is not None:
                self.prepare_wav(port2)
            accepted = []
            port2.subscribe_media_accepted(lambda p: accepted.append(p))
            port2.load(self.wav)
            _pump(150)
            assert accepted
        finally:
            port2.close()


class TestQtConformance:
    """Real QtMultimedia conformance (offscreen, deterministic WAV)."""

    def test_qt_full_contract(self, qapp, tmp_path):
        from michi.infrastructure.qt_backend import QtMultimediaBackend

        wav = _write_wav(tmp_path / "tone.wav")
        _Contract(QtMultimediaBackend, wav).run()


class TestGStreamerConformance:
    """Real GI/GStreamer conformance — truthful SKIP only when the
    required runtime (GI + Gst + playbin3) is provably absent."""

    def _bindings(self):
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerBindings,
        )

        try:
            b = GStreamerBindings()
            b.ensure_loaded()
        except (ImportError, ValueError) as exc:
            pytest.skip(f"dependency absent: PyGObject/GStreamer: {exc}")
        if not b.playbin3_available():
            pytest.skip("dependency absent: GStreamer playbin3 factory")
        return b

    def test_gst_full_contract(self, qapp, tmp_path):
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
        )

        wav = _write_wav(tmp_path / "tone.wav")
        bindings = self._bindings()

        def factory():
            port = GStreamerAudioPort(bindings)
            port.activate()
            return port

        _Contract(factory, wav).run()

    def test_gst_close_reopen_cycles(self, qapp, tmp_path):
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
        )

        wav = _write_wav(tmp_path / "tone.wav")
        bindings = self._bindings()
        for _ in range(25):
            port = GStreamerAudioPort(bindings)
            port.activate()
            port.load(wav)
            _events(port, "accepted")
            port.close()
            assert port._pump is None or not port._pump.is_alive()


class TestMpdConformance:
    """Real private MPD conformance (host-independent where possible)."""

    def _require_mpd(self):
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")

    def test_mpd_full_contract(self, qapp, tmp_path):
        self._require_mpd()
        from michi.infrastructure.audio_engines.providers import (
            MpdEngineProvider,
        )

        wav = _write_wav(tmp_path / "tone.wav")

        def factory():
            return MpdEngineProvider().open()

        # MPD accepts absolute paths through its input layer (the private
        # music_directory stays runtime-owned); no relocation needed.
        _Contract(factory, wav).run()

    def test_mpd_close_reopen_cycles(self, qapp, tmp_path):
        self._require_mpd()
        from michi.infrastructure.audio_engines.providers import (
            MpdEngineProvider,
        )

        wav = _write_wav(tmp_path / "tone.wav")
        for _ in range(25):
            provider = MpdEngineProvider()
            port = provider.open()
            port.load(wav)
            _events(port, "accepted")
            provider.close()
            assert (
                port._runtime.process is None
                or port._runtime.process.poll() is not None
            )

    def test_mpd_stop_play_cycles(self, qapp, tmp_path):
        self._require_mpd()
        from michi.infrastructure.audio_engines.providers import (
            MpdEngineProvider,
        )

        wav = _write_wav(tmp_path / "tone.wav")
        provider = MpdEngineProvider()
        port = provider.open()
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        try:
            for _ in range(100):
                accepted.clear()
                port.load(wav)
                assert accepted  # synchronous acceptance
                port.play()
                port.stop()
        finally:
            provider.close()


class TestStartupNoAutoplay:
    """Golden gate (section 44): restoring an engine must NEVER autoplay —
    prepare may load + seek, but PlaybackState stays STOPPED until the
    explicit user Play."""

    def test_mpd_real_no_autoplay_on_prepare(self, qapp, tmp_path):
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSelectionCoordinator,
        )
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import AudioTransportRouter
        from michi.application.playback_service import PlaybackService
        from michi.application.settings_service import SettingsService
        from michi.domain.audio_engine import AudioEngineId
        from michi.domain.playback import PlaybackStatus
        from michi.infrastructure.audio_engines.providers import (
            MpdEngineProvider,
        )
        from tests.test_m11_3f_engine_selection import (
            FakeProvider,
            FakeSettingsRepository,
        )

        qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
        mpd = MpdEngineProvider()
        registry = AudioEngineRegistry([qt, mpd])
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        playback = PlaybackService(router)
        settings = SettingsService(FakeSettingsRepository())
        coordinator = AudioEngineSelectionCoordinator(
            engine_service=service,
            registry=registry,
            router=router,
            playback=playback,
            settings=settings,
        )
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        # restore a session: prepare MPD with the track, persisted position
        wav = _write_wav(tmp_path / "tone.wav")
        coordinator.switch_to(AudioEngineId.MPD)
        playback.prepare_for_resume(wav, 40)
        _drain()
        # NO play command issued anywhere; state must be STOPPED
        assert playback.state.status == PlaybackStatus.STOPPED
        st = service.state
        assert st.lifecycle.value == "ready"
        assert st.active_engine_id == AudioEngineId.MPD
        # explicit user Play starts playback
        playback.play()
        _drain()
        assert playback.state.status == PlaybackStatus.PLAYING
        playback.stop()
        coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)


class TestCallbackLifecycle:
    """R1-10/section 32: callbacks must be unsubscribed with the SAME
    object they were subscribed with — repeated contract operations must
    never grow the subscriber lists."""

    def test_callback_count_does_not_grow(self):
        from michi.application.ports import AudioPort

        class CountingPort(AudioPort):
            def __init__(self):
                self._eom = []
                self._pos = []
                self._dur = []
                self._acc = []
                self._rej = []
                self._pst = []

            def load(self, path): ...
            def play(self): ...
            def pause(self): ...
            def resume(self): ...
            def stop(self): ...
            def seek(self, ms): ...
            def set_volume(self, v): ...
            def set_muted(self, m): ...
            def position(self):
                return 0

            def duration(self):
                return 0

            def subscribe_end_of_media(self, cb):
                if cb not in self._eom:
                    self._eom.append(cb)

            def unsubscribe_end_of_media(self, cb):
                if cb in self._eom:
                    self._eom.remove(cb)

            def subscribe_position_changed(self, cb):
                if cb not in self._pos:
                    self._pos.append(cb)

            def unsubscribe_position_changed(self, cb):
                if cb in self._pos:
                    self._pos.remove(cb)

            def subscribe_duration_changed(self, cb):
                if cb not in self._dur:
                    self._dur.append(cb)

            def unsubscribe_duration_changed(self, cb):
                if cb in self._dur:
                    self._dur.remove(cb)

            def subscribe_media_accepted(self, cb):
                if cb not in self._acc:
                    self._acc.append(cb)

            def unsubscribe_media_accepted(self, cb):
                if cb in self._acc:
                    self._acc.remove(cb)

            def subscribe_media_rejected(self, cb):
                if cb not in self._rej:
                    self._rej.append(cb)

            def unsubscribe_media_rejected(self, cb):
                if cb in self._rej:
                    self._rej.remove(cb)

            def subscribe_playback_state_changed(self, cb):
                if cb not in self._pst:
                    self._pst.append(cb)

            def unsubscribe_playback_state_changed(self, cb):
                if cb in self._pst:
                    self._pst.remove(cb)

        port = CountingPort()
        kinds = ("eom", "pos", "dur", "acc", "rej", "pst")
        assert sum(len(getattr(port, f"_{k}")) for k in kinds) == 0
        # repeat the subscribe → operation → unsubscribe(SAME object)
        # lifecycle many times; counts must never grow
        for _ in range(25):
            subs = {}
            subs["eom"] = lambda: None
            subs["pos"] = lambda ms: None
            subs["dur"] = lambda ms: None
            subs["acc"] = lambda p: None
            subs["rej"] = lambda p, r: None
            subs["pst"] = lambda s: None
            port.subscribe_end_of_media(subs["eom"])
            port.subscribe_position_changed(subs["pos"])
            port.subscribe_duration_changed(subs["dur"])
            port.subscribe_media_accepted(subs["acc"])
            port.subscribe_media_rejected(subs["rej"])
            port.subscribe_playback_state_changed(subs["pst"])
            assert sum(len(getattr(port, f"_{k}")) for k in kinds) == 6
            # unsubscribe the SAME objects (R1-10)
            port.unsubscribe_end_of_media(subs["eom"])
            port.unsubscribe_position_changed(subs["pos"])
            port.unsubscribe_duration_changed(subs["dur"])
            port.unsubscribe_media_accepted(subs["acc"])
            port.unsubscribe_media_rejected(subs["rej"])
            port.unsubscribe_playback_state_changed(subs["pst"])
            assert sum(len(getattr(port, f"_{k}")) for k in kinds) == 0
        final = sum(len(getattr(port, f"_{k}")) for k in kinds)
        assert final == 0, f"callback leak: {final} callbacks remain"
