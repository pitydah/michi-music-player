"""DAC-V35-100R1.2 native GStreamer/GLib lifecycle gates."""

from __future__ import annotations

import threading
import time
import wave
from pathlib import Path

import pytest
from test_gstreamer_audio_port import FakeBindings, _deliver, _FakeMsgType, _msg

from michi.application.ports import AudioLoadError
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.gstreamer import (
    GStreamerAudioPort,
    GStreamerBindings,
    _probe_missing_runtime_dependencies,
)


class _ThreadTrackingBindings(FakeBindings):
    def __init__(self) -> None:
        super().__init__()
        self.lifecycle_threads: list[tuple[str, int]] = []
        self.context_threads: list[tuple[str, int]] = []

    def _record(self, operation: str) -> None:
        self.lifecycle_threads.append((operation, threading.get_ident()))

    def create_bus_source(self, bus, callback, context=None):
        self._record("create_bus_source")
        return super().create_bus_source(bus, callback, context)

    def remove_bus_watch(self, bus):
        self._record("remove_bus_watch")
        return super().remove_bus_watch(bus)

    def create_timeout_source(self, interval_ms, callback):
        self._record("create_timeout_source")
        return super().create_timeout_source(interval_ms, callback)

    def attach_source(self, source, context):
        self._record("attach_source")
        return super().attach_source(source, context)

    def destroy_source(self, source):
        self._record("destroy_source")
        return super().destroy_source(source)

    def push_thread_default(self, context):
        self.context_threads.append(("push", threading.get_ident()))
        return super().push_thread_default(context)

    def pop_thread_default(self, context):
        self.context_threads.append(("pop", threading.get_ident()))
        return super().pop_thread_default(context)


def test_gst100r12_01_source_lifecycle_is_owned_by_single_pump_thread(
    qapp,
    tmp_path: Path,
) -> None:
    """Caller threads never attach, detach, or destroy custom-context sources."""
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    caller_thread = threading.get_ident()

    port.load(tmp_path / "track.flac")
    pump_thread = port._pump.ident
    port.close()

    assert pump_thread is not None and pump_thread != caller_thread
    assert [name for name, _thread in bindings.lifecycle_threads] == [
        "create_bus_source",
        "create_timeout_source",
        "attach_source",
        "remove_bus_watch",
        "destroy_source",
    ]
    assert {thread for _name, thread in bindings.lifecycle_threads} == {pump_thread}


def test_gst100r12_02_thread_default_is_pushed_and_popped_once(qapp) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.activate()
    pump_thread = port._pump.ident

    port.close()

    assert bindings.context_threads == [("push", pump_thread), ("pop", pump_thread)]


def test_gst100r12_03_replacements_keep_source_operations_on_pump(
    qapp, tmp_path: Path
) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    for name in ("a.flac", "b.flac", "c.flac"):
        port.load(tmp_path / name)
    pump_thread = port._pump.ident
    port.close()

    assert {thread for _name, thread in bindings.lifecycle_threads} == {pump_thread}
    assert [name for name, _thread in bindings.lifecycle_threads].count(
        "create_bus_source"
    ) == 3
    assert [name for name, _thread in bindings.lifecycle_threads].count(
        "remove_bus_watch"
    ) == 3


def test_gst100r12_04_failed_detach_retains_pump_for_retry(
    qapp, tmp_path: Path
) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.load(tmp_path / "track.flac")
    bindings.fail_remove_watch = True
    port._bus.fail_remove_watch = True

    with pytest.raises(RuntimeError, match="bus watch"):
        port.close()

    assert port._pump is not None and port._pump.is_alive()
    # R1.3.2 §16: a failed detach must leave real ownership observable.
    assert port._bus_source is not None
    assert port._bus is not None
    assert port._closed is False
    port._bus.fail_remove_watch = False
    port.close()
    # R1.3.2 §20: closure is proven by released ownership, not by the flag.
    assert port._closed is True
    assert port._pipeline is None
    assert port._bus_source is None
    assert port._bus is None
    assert port._timer_source is None
    assert port._loop is None
    assert port._context is None
    assert port._pump is None or not port._pump.is_alive()


def test_failed_replacement_detach_converges_stopped_and_source_lost(
    qapp, tmp_path: Path
) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    states = []
    port.subscribe_playback_state_changed(states.append)
    port.load(tmp_path / "a.flac")
    message, generation = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
    _deliver(port, message, generation)
    port.play()
    port._deliver_state_if(PlaybackStatus.PLAYING)
    bindings.pipelines[-1].bus.fail_remove_watch = True

    with pytest.raises(AudioLoadError) as caught:
        port.load(tmp_path / "b.flac")

    assert caught.value.previous_source_preserved is False
    assert port._current_path is None
    assert states[-1] is PlaybackStatus.STOPPED
    bindings.pipelines[-1].bus.fail_remove_watch = False
    port.close()


def test_gst100r12_05_pump_command_exception_is_visible(qapp) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.activate()

    def fail():
        raise ValueError("native command failed")

    with pytest.raises(ValueError, match="native command failed"):
        port._run_on_pump(fail)
    port.close()


def test_gst100r12_06_caller_never_pushes_custom_context(qapp) -> None:
    bindings = _ThreadTrackingBindings()
    caller = threading.get_ident()
    port = GStreamerAudioPort(bindings)
    port.activate()
    port.close()

    assert all(thread != caller for _operation, thread in bindings.context_threads)


def test_gst100r12_07_timer_destruction_is_pump_owned(qapp, tmp_path: Path) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.load(tmp_path / "track.flac")
    pump_thread = port._pump.ident
    port.close()

    destroys = [
        thread
        for operation, thread in bindings.lifecycle_threads
        if operation == "destroy_source"
    ]
    assert destroys == [pump_thread]


def test_gst100r12_08_close_is_idempotent_without_native_reentry(
    qapp, tmp_path: Path
) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.load(tmp_path / "track.flac")
    port.close()
    operations = tuple(bindings.lifecycle_threads)

    port.close()

    assert tuple(bindings.lifecycle_threads) == operations


def test_gst100r12_09_stale_source_callback_after_close_is_inert(
    qapp, tmp_path: Path
) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.load(tmp_path / "track.flac")
    callback = bindings.pipelines[-1].bus.watch_callback
    port.close()

    assert callback(bindings.pipelines[-1].bus, None) is True
    assert port._closed is True


def test_unexpected_pump_exit_cleans_sources_before_thread_default_pop(
    qapp, tmp_path: Path
) -> None:
    bindings = _ThreadTrackingBindings()
    port = GStreamerAudioPort(bindings)
    port.load(tmp_path / "track.flac")
    pump_thread = port._pump.ident

    bindings.quit_loop(port._loop)
    port._pump.join(timeout=2.0)
    assert port._pump.is_alive() is False
    port.close()

    lifecycle = [
        (operation, thread)
        for operation, thread in bindings.lifecycle_threads
        if operation in {"remove_bus_watch", "destroy_source"}
    ]
    assert lifecycle == [
        ("remove_bus_watch", pump_thread),
        ("destroy_source", pump_thread),
    ]
    assert port._closed is True


def test_gst100r12_10_real_repeated_lifecycle_has_no_context_assertions(
    qapp, tmp_path: Path, capfd
) -> None:
    try:
        bindings = GStreamerBindings()
        bindings.ensure_loaded()
    except (ImportError, ValueError):
        pytest.skip("GI/GStreamer runtime unavailable")
    missing = _probe_missing_runtime_dependencies(bindings)
    if missing is not None:
        pytest.skip(f"dependency absent: {missing}")

    class _FakeSinkBindings(GStreamerBindings):
        def make_playbin3(self):
            pipeline = super().make_playbin3()
            sink = self._gst.ElementFactory.make("fakesink", None)
            if pipeline is None or sink is None:
                pytest.skip("real playbin3/fakesink unavailable")
            pipeline.set_property("audio-sink", sink)
            return pipeline

    source = tmp_path / "silence.wav"
    with wave.open(str(source), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8_000)
        wav.writeframes(b"\x00\x00" * 800)
    port = GStreamerAudioPort(_FakeSinkBindings())
    accepted = []
    port.subscribe_media_accepted(accepted.append)
    try:
        for expected in range(1, 4):
            port.load(source)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and len(accepted) < expected:
                qapp.processEvents()
                time.sleep(0.01)
            assert len(accepted) == expected
    finally:
        port.close()

    stderr = capfd.readouterr().err.casefold()
    assert "g_main_context_push_thread_default" not in stderr
    assert "g_main_context_pop_thread_default" not in stderr
    assert "assertion 'acquired_context' failed" not in stderr
