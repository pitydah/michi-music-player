"""DAC-V35-100R1.3.2 — native closure final corrective gates.

These gates exercise the PRODUCTIVE paths, never a test-side replica of the
desired semantics:

- ``nc132_01_*`` RUNNING context-command commit authority (real port fields)
- ``nc132_02_*`` residual native ownership cannot fake closure
- ``nc132_03_*`` single-flight leader failure fan-out
- ``nc132_04_*`` startup resume transient position readiness
"""

from __future__ import annotations

import contextlib
import threading
from pathlib import Path

import pytest
from test_gstreamer_audio_port import FakeBindings

from michi.infrastructure.audio_engines.gstreamer import (
    ContextCommandTimeoutError,
    GStreamerAudioPort,
)


class _BlockingBindings(FakeBindings):
    """Fake bindings whose native creation/removal can be held open."""

    def __init__(self) -> None:
        super().__init__()
        self.bus_create_entered = threading.Event()
        self.bus_create_release = threading.Event()
        self.watch_remove_entered = threading.Event()
        self.watch_remove_release = threading.Event()
        self.block_bus_create = False
        self.block_watch_remove = False

    def create_bus_source(self, bus, callback, context=None):
        if self.block_bus_create:
            self.bus_create_entered.set()
            self.bus_create_release.wait(timeout=15)
        return super().create_bus_source(bus, callback, context)

    def remove_bus_watch(self, bus) -> bool:
        if self.block_watch_remove:
            self.watch_remove_entered.set()
            self.watch_remove_release.wait(timeout=15)
        return super().remove_bus_watch(bus)


def _drain_pump(port) -> None:
    """Deterministic barrier: the pump is single-threaded FIFO, so a no-op
    command returns only after every earlier pump callback finished."""
    port._run_on_pump(lambda: None)


def _live_port(*, block_bus_create: bool = False, block_watch_remove: bool = False):
    bindings = _BlockingBindings()
    bindings.block_bus_create = block_bus_create
    bindings.block_watch_remove = block_watch_remove
    port = GStreamerAudioPort(bindings=bindings)
    port._ensure_pump()
    return bindings, port


def _attach_in_background(port, bus, *, generation: int = 1):
    """Run the PRODUCTIVE attach path on a worker; return (thread, errors).

    Mirrors the production call site: the owning bus is installed before the
    sources are attached.
    """
    port._bus = bus
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            port._attach_pipeline_sources(object(), bus, generation)
        except BaseException as exc:  # noqa: BLE001 — asserted by the test
            errors.append(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread, errors


def _detach_in_background(port):
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            port._detach_pipeline_sources()
        except BaseException as exc:  # noqa: BLE001 — asserted by the test
            errors.append(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread, errors


# ── Phase 1 — RUNNING context-command commit authority ─────────────────────


def test_nc132_01_a_blocked_attach_cannot_commit_after_caller_timeout() -> None:
    """A native creation that outlives the caller's wait must not install."""
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        thread, errors = _attach_in_background(port, bus)
        assert bindings.bus_create_entered.wait(timeout=10), (
            "the productive attach never reached create_bus_source"
        )

        # The caller's bounded wait expires while the native creation is held.
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        # The native creation finally returns — long after the revocation.
        bindings.bus_create_release.set()
        assert not thread.is_alive()
        _drain_pump(port)

        assert port._bus_source is None, "a revoked command installed a bus source"
        assert port._bus_source_attached is False
        assert port._timer_source is None, "a revoked command installed a timer"
    finally:
        bindings.block_bus_create = False
        bindings.bus_create_release.set()
        with contextlib.suppress(Exception):
            port.close()


def test_nc132_01_b_retry_after_revoked_attach_stays_authoritative() -> None:
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        thread, errors = _attach_in_background(port, bus)
        assert bindings.bus_create_entered.wait(timeout=10)
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        # A newer generation retries with a responsive native layer.
        bindings.block_bus_create = False
        bindings.bus_create_release.set()
        assert not thread.is_alive()
        _drain_pump(port)

        port._attach_pipeline_sources(object(), bus, 2)

        assert port._bus_source is not None
        assert port._bus_source_attached is True
        assert port._timer_source is not None
    finally:
        bindings.block_bus_create = False
        bindings.bus_create_release.set()
        with contextlib.suppress(Exception):
            port.close()


def test_nc132_01_c_stale_detach_cannot_clear_a_newer_bus_source() -> None:
    bindings, port = _live_port(block_watch_remove=True)
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        port._bus = bus
        port._attach_pipeline_sources(object(), bus, 1)
        assert port._bus_source is not None

        thread, errors = _detach_in_background(port)
        assert bindings.watch_remove_entered.wait(timeout=10), (
            "the productive detach never reached remove_bus_watch"
        )
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        # A newer generation re-installs a fresh bus source before the stale
        # detach finally returns.
        bindings.block_watch_remove = False
        bindings.watch_remove_release.set()
        assert not thread.is_alive()
        _drain_pump(port)
        fresh_bus = bindings.get_bus(bindings.make_playbin3())
        port._bus = fresh_bus
        port._attach_pipeline_sources(object(), fresh_bus, 2)
        assert port._bus_source is not None

        assert port._bus_source_attached is True, (
            "a stale detach cleared ownership that a newer generation installed"
        )
        assert port._bus is not None
    finally:
        bindings.block_watch_remove = False
        bindings.watch_remove_release.set()
        with contextlib.suppress(Exception):
            port.close()


# ── Phase 2 — residual native ownership cannot fake closure ────────────────


class _Executor:
    """Direct-executor double with injectable release failure."""

    def __init__(self, *, fail: bool = False) -> None:
        self.handle = None
        self.releases: list[str] = []
        self.fail = fail

    def release(self, reason: str) -> None:
        self.releases.append(reason)
        if self.fail:
            raise RuntimeError("synthetic release failure")

    def mark_previous_source_released(self) -> None:
        return None

    def abort(self, *_args, **_kwargs):
        return None

    def record_runtime_anomaly(self, *_args, **_kwargs) -> None:
        return None

    def discard_staged_load(self, *_args, **_kwargs) -> None:
        return None


def _loaded_port(tmp_path: Path, *, executor=None):
    bindings = FakeBindings()
    port = GStreamerAudioPort(bindings=bindings, direct_executor=executor)
    port.load(tmp_path / "r132.flac")
    return bindings, port


def _assert_full_closure(port) -> None:
    assert port._closed is True
    assert port._pipeline is None
    assert port._bus_source is None
    assert port._bus is None
    assert port._timer_source is None
    assert port._loop is None
    assert port._context is None
    assert port._pump is None or not port._pump.is_alive()
    assert port._close_residual_ownership() == ()


def test_nc132_02_a_close_retry_releases_residual_bus_and_pump(
    qapp, tmp_path: Path
) -> None:
    """A successful NULL must not hide a still-attached bus watch."""
    bindings, port = _loaded_port(tmp_path)
    assert port._bus_source is not None
    port._bus.fail_remove_watch = True

    with pytest.raises(RuntimeError, match="bus watch"):
        port.close()

    # The residual ownership stays observable and retryable.
    assert port._closed is False
    assert port._bus_source is not None
    assert port._bus is not None
    assert port._pump is not None and port._pump.is_alive()
    assert "bus_source" in port._close_residual_ownership()

    port._bus.fail_remove_watch = False
    port.close()

    _assert_full_closure(port)


def test_nc132_02_b_residual_gate_blocks_a_fake_closure(qapp, tmp_path: Path) -> None:
    """No residual obligation may coexist with a closed port."""
    _bindings_unused, port = _loaded_port(tmp_path)
    # Keep the pump ownership while removing every other obligation: the gate
    # must still refuse to claim closure.
    port._pipeline = None
    port._bus_source = None
    port._timer_source = None

    residual = port._close_residual_ownership()

    assert "pump" in residual
    assert port._closed is False


def test_nc132_02_c_first_error_wins_and_release_still_attempted(
    qapp, tmp_path: Path
) -> None:
    executor = _Executor(fail=True)
    _bindings_unused, port = _loaded_port(tmp_path, executor=executor)
    port._bus.fail_remove_watch = True

    with pytest.raises(RuntimeError, match="bus watch"):
        port.close()

    # The first chronological failure wins, and the Direct executor release is
    # still attempted even though an earlier cleanup failed.
    assert executor.releases == ["gstreamer_close"]
    assert port._closed is False
    assert port._bus_source is not None

    # Repairing both obligations must converge to a full terminal closure.
    port._bus.fail_remove_watch = False
    executor.fail = False
    port.close()

    _assert_full_closure(port)
    assert executor.releases == ["gstreamer_close", "gstreamer_close"]


# ── Phase 3 — single-flight leader failure fan-out ─────────────────────────


_UNSET = object()


class _FailingGatedProbe:
    """Probe that blocks until every follower joined, then fails or succeeds."""

    def __init__(self, *, failure: object = _UNSET) -> None:
        self.calls: list[dict] = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.failure: BaseException | None = (
            RuntimeError("synthetic probe failure") if failure is _UNSET else failure
        )

    def probe_exact(self, **kwargs):
        from michi.domain.audio_evidence import ExactProbeResult, PcmTuple

        self.calls.append(kwargs)
        self.entered.set()
        self.release.wait(timeout=15)
        if self.failure is not None:
            raise self.failure
        requested = PcmTuple(
            kwargs["rate_hz"], kwargs["transport_format"], kwargs["channels"], 16
        )
        return ExactProbeResult(
            requested, requested, "OPENED", None, None, "probe:fan-out"
        )


def _qualification_service(probe, *, follower_timeout_s: float = 10.0):
    from michi.application.dac_qualification_service import DacQualificationService

    return DacQualificationService(
        probe,
        environment_fingerprint=lambda: "env:a",
        single_flight_timeout_s=follower_timeout_s,
    )


def _probe_once(service):
    return service.probe_for_play(
        stable_device_id="usb:2622:0105:DX5ABC123",
        locator="hw:CARD=DX5,DEV=0",
        rate_hz=44_100,
        transport_format="S16_LE",
        channels=2,
        binding_generation=1,
    )


def test_nc132_03_a_leader_failure_fans_out_to_every_follower() -> None:
    probe = _FailingGatedProbe()
    service = _qualification_service(probe)
    outcomes: list[object] = []
    failures: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            outcome = _probe_once(service)
        except BaseException as exc:  # noqa: BLE001 — asserted below
            with lock:
                failures.append(exc)
        else:
            with lock:
                outcomes.append(outcome)

    leader = threading.Thread(target=worker)
    leader.start()
    assert probe.entered.wait(timeout=10), "the leader never probed"

    followers = [threading.Thread(target=worker) for _ in range(20)]
    for follower in followers:
        follower.start()
    assert _await(
        lambda: (
            bool(service._flights)
            and next(iter(service._flights.values())).waiters == 20
        )
    ), "followers did not coalesce"

    probe.release.set()
    leader.join(timeout=15)
    for follower in followers:
        follower.join(timeout=15)

    assert len(probe.calls) == 1, "the flight probed more than once"
    assert outcomes == [], "a follower received an accidental result"
    assert len(failures) == 21
    assert all(isinstance(item, RuntimeError) for item in failures)
    assert all("synthetic probe failure" in str(item) for item in failures)
    assert all(not isinstance(item, AttributeError) for item in failures)
    assert service._flights == {}, "the failed flight did not retire"


def test_nc132_03_b_repaired_adapter_forms_a_new_flight() -> None:
    probe = _FailingGatedProbe()
    service = _qualification_service(probe)

    with pytest.raises(RuntimeError, match="synthetic probe failure"):
        _probe_once(service)
    assert service._flights == {}

    probe.failure = None
    probe.release.set()
    outcome = _probe_once(service)

    assert outcome.evidence.supported is True
    assert len(probe.calls) == 2


def test_nc132_03_c_follower_timeout_still_never_starts_a_second_probe() -> None:
    from michi.application.dac_qualification_service import (
        QualificationSingleFlightTimeoutError,
    )

    probe = _FailingGatedProbe(failure=None)
    service = _qualification_service(probe, follower_timeout_s=0.2)
    leader_results: list[object] = []
    follower_errors: list[BaseException] = []

    def leader() -> None:
        leader_results.append(_probe_once(service))

    def follower() -> None:
        try:
            _probe_once(service)
        except BaseException as exc:  # noqa: BLE001 — asserted below
            follower_errors.append(exc)

    leader_thread = threading.Thread(target=leader)
    leader_thread.start()
    assert probe.entered.wait(timeout=10)

    followers = [threading.Thread(target=follower) for _ in range(5)]
    for thread in followers:
        thread.start()
    for thread in followers:
        thread.join(timeout=10)

    assert probe.release.is_set() is False
    assert len(probe.calls) == 1
    assert len(follower_errors) == 5
    assert all(
        isinstance(item, QualificationSingleFlightTimeoutError)
        for item in follower_errors
    )

    probe.release.set()
    leader_thread.join(timeout=15)
    assert len(leader_results) == 1
    assert len(probe.calls) == 1


def _await(predicate, *, timeout_s: float = 5.0) -> bool:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return bool(predicate())


# ── Phase 4 — startup resume transient position readiness ──────────────────


class _TransientPositionPort:
    """Audio port whose post-seek position query is temporarily unavailable."""

    def __init__(self, *, before: int = 0, target_confirmed: bool = False) -> None:
        self._position = before
        self._position_calls = 0
        self.seek_calls: list[int] = []
        self.play_calls = 0
        self.unavailable_on_second_query = True
        self._accepted_callbacks: list = []
        self._position_changed_callbacks: list = []
        self._target_confirmed = target_confirmed

    # -- surface used by PlaybackService --------------------------------
    def load(self, path) -> None:
        return None

    def play(self) -> None:
        self.play_calls += 1

    def pause(self) -> None:
        return None

    def resume(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def set_volume(self, value) -> None:
        return None

    def set_muted(self, value) -> None:
        return None

    def seek(self, position_ms: int) -> None:
        self.seek_calls.append(position_ms)
        if self._target_confirmed:
            self._position = position_ms

    def position(self) -> int:
        from michi.application.ports import AudioTransportUnavailableError

        self._position_calls += 1
        if self.unavailable_on_second_query and self._position_calls >= 2:
            raise AudioTransportUnavailableError(
                "GStreamer position query failed on a live pipeline"
            )
        return self._position

    def duration(self) -> int:
        return 0

    def subscribe_end_of_media(self, callback) -> None:
        return None

    def unsubscribe_end_of_media(self, callback) -> None:
        return None

    def subscribe_position_changed(self, callback) -> None:
        self._position_changed_callbacks.append(callback)

    def unsubscribe_position_changed(self, callback) -> None:
        return None

    def subscribe_duration_changed(self, callback) -> None:
        return None

    def unsubscribe_duration_changed(self, callback) -> None:
        return None

    def subscribe_media_accepted(self, callback) -> None:
        self._accepted_callbacks.append(callback)

    def unsubscribe_media_accepted(self, callback) -> None:
        return None

    def subscribe_playback_state_changed(self, callback) -> None:
        return None

    def unsubscribe_playback_state_changed(self, callback) -> None:
        return None

    def subscribe_media_rejected(self, callback) -> None:
        return None

    def unsubscribe_media_rejected(self, callback) -> None:
        return None

    def accept_media(self, path) -> None:
        for callback in list(self._accepted_callbacks):
            callback(path)

    def emit_position_changed(self, position_ms: int) -> None:
        for callback in list(self._position_changed_callbacks):
            callback(position_ms)


def _resume_playback(*, target_confirmed: bool = False):
    from michi.application.playback_service import PlaybackService

    port = _TransientPositionPort(before=0, target_confirmed=target_confirmed)
    playback = PlaybackService(port)
    fired: list[tuple] = []
    playback.subscribe_resume_prepared(lambda path, pos: fired.append((path, pos)))
    return port, playback, fired


def test_nc132_04_a_transient_post_seek_position_cannot_escape() -> None:
    media = Path("/tmp/r132-resume.flac")
    port, playback, fired = _resume_playback()

    playback.prepare_for_resume(media, 30_000)
    port.accept_media(media)

    # The transient readiness failure must not escape and must not fabricate a
    # confirmation: the latch stays armed for the normal backend event.
    assert port.seek_calls == [30_000]
    assert fired == []
    assert playback._resume_prepared_pending is True
    assert playback.state.error_message is None

    # The normal backend event: PlaybackCoordinator._on_position_changed
    # forwards the observed position into the playback authority.
    playback.update_position(30_000)

    assert fired == [(media, 30_000)]
    assert playback._resume_prepared_pending is False


def test_nc132_04_b_immediate_confirmation_is_preserved() -> None:
    """A backend that answers immediately keeps the current semantics."""
    media = Path("/tmp/r132-resume-immediate.flac")
    port, playback, fired = _resume_playback(target_confirmed=False)
    port.unavailable_on_second_query = False

    playback.prepare_for_resume(media, 0)
    port.accept_media(media)

    # seek-to-0 with an unchanged, already-matching backend position confirms
    # once, with the backend-reported value.
    assert fired == [(media, 0)]
    assert playback._resume_prepared_pending is False
