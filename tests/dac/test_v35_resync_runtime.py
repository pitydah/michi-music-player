"""DAC-V35-050/080: post-preroll resync hold, not a pre-open sleep."""

from dataclasses import replace
from pathlib import Path

import pytest

from michi.infrastructure.audio_engines.gstreamer import (
    _GstEvent,
    _GstEventKind,
)
from tests.dac.test_v35_strict_sink import _plan
from tests.test_gstreamer_audio_port import (
    FakeBindings,
    _deliver,
    _FakeMsgType,
    _msg,
    _strict_port,
)


def _preroll(port, bindings):
    message, generation = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
    _deliver(port, message, generation)


@pytest.mark.parametrize("delay", [100, 250, 500, 1000])
def test_resync_starts_only_after_verified_preroll_and_deadline(qapp, delay):
    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=delay))
        port.load(Path("/m/start-marker.wav"))
        pipeline = bindings.pipelines[-1]
        port.play()
        assert pipeline.state != bindings.STATE.PLAYING
        # Arbitrarily slow acquisition must not consume the post-open delay.
        now[0] = 9_000_000_000
        _preroll(port, bindings)
        assert pipeline.state != bindings.STATE.PLAYING
        tick = _GstEvent(port._generation, _GstEventKind.POSITION_TICK)
        now[0] += delay * 1_000_000 - 1
        port._on_backend_event(tick)
        assert pipeline.state != bindings.STATE.PLAYING
        now[0] += 1
        port._on_backend_event(tick)
        assert pipeline.state == bindings.STATE.PLAYING
    finally:
        port.close()


@pytest.mark.parametrize("direct", [False, True])
def test_zero_delay_and_shared_keep_immediate_play(qapp, direct):
    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    try:
        if direct:
            executor.prepare(_plan())
        port.load(Path("/m/default.wav"))
        port.play()
        assert bindings.pipelines[-1].state == bindings.STATE.PLAYING
    finally:
        port.close()


@pytest.mark.parametrize("cancel", ["pause", "stop", "close", "release", "supersede"])
def test_cancelled_or_stale_tick_never_starts_audio(qapp, cancel):
    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=250))
        port.load(Path("/m/old.wav"))
        port.play()
        _preroll(port, bindings)
        old_pipeline = bindings.pipelines[-1]
        tick = _GstEvent(port._generation, _GstEventKind.POSITION_TICK)
        if cancel == "release":
            executor.release("device_lost")
        elif cancel == "supersede":
            port.load(Path("/m/new-shared.wav"))
        else:
            getattr(port, cancel)()
        now[0] = 10_000_000_000
        port._on_backend_event(tick)
        assert old_pipeline.state != bindings.STATE.PLAYING
        assert bindings.pipelines[-1].state != bindings.STATE.PLAYING
    finally:
        port.close()


def test_duplicate_play_and_async_done_do_not_restart_deadline(qapp):
    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=100))
        port.load(Path("/m/marker.wav"))
        port.play()
        _preroll(port, bindings)
        now[0] = 99_000_000
        port.play()
        _preroll(port, bindings)
        now[0] = 100_000_000
        port._on_backend_event(_GstEvent(port._generation, _GstEventKind.POSITION_TICK))
        assert bindings.pipelines[-1].state == bindings.STATE.PLAYING
    finally:
        port.close()


def test_retained_source_replay_reacquires_before_delay_without_reacceptance(qapp):
    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    accepted = []
    port.subscribe_media_accepted(accepted.append)
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=100))
        port.load(Path("/m/marker.wav"))
        port.play()
        _preroll(port, bindings)
        now[0] = 100_000_000
        port._on_backend_event(_GstEvent(port._generation, _GstEventKind.POSITION_TICK))
        port.stop()
        port.play()
        assert bindings.pipelines[-1].state == bindings.STATE.PAUSED
        now[0] = 2_000_000_000
        _preroll(port, bindings)
        tick = _GstEvent(port._generation, _GstEventKind.POSITION_TICK)
        port._on_backend_event(tick)
        assert bindings.pipelines[-1].state == bindings.STATE.PAUSED
        now[0] += 100_000_000
        port._on_backend_event(tick)
        assert bindings.pipelines[-1].state == bindings.STATE.PLAYING
        assert accepted == [Path("/m/marker.wav")]
    finally:
        port.close()


@pytest.mark.parametrize("failure", ["error", "pump_death"])
def test_failure_during_hold_cancels_the_deferred_start(qapp, failure):
    """Error or pump death must retire the hold before any callback runs."""
    from tests.test_gstreamer_audio_port import _deliver, _FakeMsgType, _msg

    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=250))
        port.load(Path("/m/failing.wav"))
        port.play()
        _preroll(port, bindings)
        assert port._resync_ready_at_ns is not None

        if failure == "error":
            message, generation = _msg(
                port, _FakeMsgType.ERROR, bindings.pipelines[-1], error_text="boom"
            )
            _deliver(port, message, generation)
            # The error path retires the candidate and the deferred start.
            assert port._current_path is None
            assert port._pending_play is False
            assert port._resync_delay_ms == 0
            assert port._resync_ready_at_ns is None
        else:
            port._on_pump_died(port._generation, "pump died")
            assert port._pending_play is False
            assert port._resync_delay_ms == 0
            assert port._resync_ready_at_ns is None

        now[0] = 10_000_000_000
        port._on_backend_event(_GstEvent(port._generation, _GstEventKind.POSITION_TICK))
        assert bindings.pipelines[-1].state != bindings.STATE.PLAYING
    finally:
        port.close()


def test_eos_replay_with_delay_reacquires_before_starting(qapp):
    """An EOS replay must re-hold: fresh preroll then the full delay."""
    from tests.test_gstreamer_audio_port import _deliver, _FakeMsgType, _msg

    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    accepted: list[Path] = []
    port.subscribe_media_accepted(accepted.append)
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=100))
        port.load(Path("/m/marker.wav"))
        port.play()
        _preroll(port, bindings)
        now[0] = 100_000_000
        port._on_backend_event(_GstEvent(port._generation, _GstEventKind.POSITION_TICK))
        assert bindings.pipelines[-1].state == bindings.STATE.PLAYING

        message, generation = _msg(port, _FakeMsgType.EOS, bindings.pipelines[-1])
        _deliver(port, message, generation)

        port.play()
        assert bindings.pipelines[-1].state == bindings.STATE.PAUSED
        now[0] = 9_000_000_000
        _preroll(port, bindings)
        tick = _GstEvent(port._generation, _GstEventKind.POSITION_TICK)
        port._on_backend_event(tick)
        assert bindings.pipelines[-1].state == bindings.STATE.PAUSED
        now[0] += 100_000_000
        port._on_backend_event(tick)
        assert bindings.pipelines[-1].state == bindings.STATE.PLAYING
        assert accepted == [Path("/m/marker.wav")]
    finally:
        port.close()


def test_released_execution_cannot_start_and_reports_no_anomaly(qapp):
    """A retired executor must not be re-entered nor start audio."""
    bindings = FakeBindings()
    port, executor = _strict_port(bindings)
    now = [0]
    port._resync_clock_ns = lambda: now[0]
    anomalies: list[str] = []
    executor.record_runtime_anomaly = lambda handle, reason: anomalies.append(reason)
    try:
        executor.prepare(replace(_plan(), resync_delay_ms=250))
        port.load(Path("/m/old.wav"))
        port.play()
        _preroll(port, bindings)
        executor.release("device_lost")

        now[0] = 10_000_000_000
        port._on_backend_event(_GstEvent(port._generation, _GstEventKind.POSITION_TICK))
        assert bindings.pipelines[-1].state != bindings.STATE.PLAYING
        assert port._resync_complete is False
        assert port._pending_play is False
        assert port._resync_delay_ms == 0
        assert anomalies == [], "a retired execution is not re-entered"
    finally:
        port.close()
