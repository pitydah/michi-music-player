"""DAC-V35-100R1.3.3 — native source ownership seal gates.

Every gate observes NATIVE truth (``bus.watch_installed``,
``bus.remove_watch_count``, ``bus.add_watch_count``, ``source.attached``,
``source.destroyed``) in addition to the Python bookkeeping, and exercises the
PRODUCTIVE paths — never a test-side replica of the intended semantics.

- ``nso133_01_*`` native bus watch ownership
- ``nso133_02_*`` native timer source ownership
- ``nso133_03_*`` stale detach reconciliation
- ``nso133_04_*`` terminal close convergence
"""

from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path

import pytest
from test_gstreamer_audio_port import FakeBindings

from michi.infrastructure.audio_engines.gstreamer import (
    ContextCommandTimeoutError,
    GStreamerAudioPort,
)


class _NativeBlockingBindings(FakeBindings):
    """Fake bindings whose native primitives can be held open by the test."""

    def __init__(self) -> None:
        super().__init__()
        self.block_bus_create = False
        self.bus_create_entered = threading.Event()
        self.bus_create_release = threading.Event()
        self.block_watch_remove = False
        self.watch_remove_entered = threading.Event()
        self.watch_remove_release = threading.Event()
        self.block_attach_source = False
        self.attach_source_entered = threading.Event()
        self.attach_source_release = threading.Event()

    def create_bus_source(self, bus, callback, context=None):
        if self.block_bus_create:
            self.bus_create_entered.set()
            self.bus_create_release.wait(timeout=15)
        return super().create_bus_source(bus, callback, context)

    def remove_bus_watch(self, bus):
        if self.block_watch_remove:
            self.watch_remove_entered.set()
            self.watch_remove_release.wait(timeout=15)
        return super().remove_bus_watch(bus)

    def attach_source(self, source, context):
        if self.block_attach_source:
            self.attach_source_entered.set()
            self.attach_source_release.wait(timeout=15)
        return super().attach_source(source, context)


def _await(predicate, *, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return bool(predicate())


def _live_port(**blocks):
    bindings = _NativeBlockingBindings()
    for name, value in blocks.items():
        setattr(bindings, name, value)
    port = GStreamerAudioPort(bindings=bindings)
    port._ensure_pump()
    return bindings, port


def _bus(bindings):
    return bindings.get_bus(bindings.make_playbin3())


def _attach(port, bus, *, generation: int = 1) -> None:
    """Attach through the productive path with the production call-site shape.

    The load path installs the owning bus BEFORE attaching its sources, so the
    test mirrors that: `_bus` must belong to the port for a truthful detach.
    """
    port._bus = bus
    port._attach_pipeline_sources(object(), bus, generation)


def _attach_in_background(port, bus, *, generation: int = 1):
    """Run the PRODUCTIVE attach path on a worker (production call-site shape)."""
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


def _drain_pump(port) -> None:
    """Deterministic barrier: a no-op command returns after earlier callbacks."""
    port._run_on_pump(lambda: None)


def _release_and_drain(bindings, port) -> None:
    bindings.bus_create_release.set()
    bindings.watch_remove_release.set()
    bindings.attach_source_release.set()
    _drain_pump(port)


def _assert_full_native_closure(port, bus) -> None:
    """Native + logical closure, not merely the ``_closed`` flag (R1.3.3 §34)."""
    assert port._closed is True
    assert bus.watch_installed is False
    assert port._residual_bus_watches == []
    assert port._residual_timer_sources == []
    assert port._pipeline is None
    assert port._bus is None
    assert port._bus_source is None
    assert port._timer_source is None
    assert port._loop is None
    assert port._context is None
    assert port._pump is None or not port._pump.is_alive()


# ── Phase 1 — native bus watch ownership ───────────────────────────────────


def test_nso133_01_a_revoked_add_watch_removes_the_native_watch() -> None:
    """The native registration must be compensated with bus.remove_watch()."""
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = _bus(bindings)
        thread, errors = _attach_in_background(port, bus)
        assert bindings.bus_create_entered.wait(timeout=10), (
            "the productive attach never reached bus.add_watch"
        )
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        bindings.block_bus_create = False
        _release_and_drain(bindings, port)

        # NATIVE truth first, then the bookkeeping.
        assert bus.watch_installed is False, "a native bus watch stayed installed"
        assert bus.remove_watch_count == 1, "the canonical removal was not used"
        assert port._bus_source is None
        assert port._residual_bus_watches == []
    finally:
        bindings.block_bus_create = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)
            port.close()


def test_nso133_01_b_failed_compensation_stays_observable_and_retryable() -> None:
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = _bus(bindings)
        thread, errors = _attach_in_background(port, bus)
        assert bindings.bus_create_entered.wait(timeout=10)
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        # The compensating removal is refused while the watch is still native.
        bus.fail_remove_watch = True
        bindings.block_bus_create = False
        _release_and_drain(bindings, port)

        assert bus.watch_installed is True
        assert port._residual_bus_watches != [], "residual ownership became invisible"
        with pytest.raises(RuntimeError):
            port.close()
        assert port._closed is False

        # Repair: close() retries the residual receipt and converges.
        bus.fail_remove_watch = False
        port.close()

        _assert_full_native_closure(port, bus)
    finally:
        bindings.block_bus_create = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)


def test_nso133_01_c_retry_after_revoked_add_watch_has_one_active_watch() -> None:
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = _bus(bindings)
        thread, errors = _attach_in_background(port, bus)
        assert bindings.bus_create_entered.wait(timeout=10)
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        bindings.block_bus_create = False
        _release_and_drain(bindings, port)
        assert bus.watch_installed is False

        # A newer generation attaches on the same bus.
        _attach(port, bus, generation=2)

        assert bus.watch_installed is True
        assert bus.add_watch_count == 2
        assert bus.remove_watch_count == 1, "the stale watch was not compensated"
        assert port._bus_source is not None
        assert port._residual_bus_watches == []
    finally:
        bindings.block_bus_create = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)
            port.close()


# ── Phase 2 — native timer source ownership ────────────────────────────────


def test_nso133_02_a_stale_timer_attach_is_compensated() -> None:
    bindings, port = _live_port(block_attach_source=True)
    try:
        bus = _bus(bindings)
        thread, errors = _attach_in_background(port, bus)
        assert bindings.attach_source_entered.wait(timeout=10), (
            "the productive attach never reached the native timer attach"
        )
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        bindings.block_attach_source = False
        _release_and_drain(bindings, port)

        timers = bindings.timer_sources
        assert len(timers) == 1
        assert timers[0].attached is True, "the native attach never happened"
        assert timers[0].destroyed is True, "the stale attached timer survived"
        assert port._timer_source is None
        assert port._residual_timer_sources == []
    finally:
        bindings.block_attach_source = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)
            port.close()


def test_nso133_02_b_failed_timer_compensation_stays_residual() -> None:
    bindings, port = _live_port(block_attach_source=True)
    try:
        bus = _bus(bindings)
        thread, errors = _attach_in_background(port, bus)
        assert bindings.attach_source_entered.wait(timeout=10)
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        # The compensating destruction cannot be proven.
        bindings.fail_destroy_source = True
        bindings.block_attach_source = False
        _release_and_drain(bindings, port)

        timers = bindings.timer_sources
        assert len(timers) == 1
        assert timers[0].destroyed is False
        assert port._residual_timer_sources == [timers[0]]
        assert port._timer_source is None

        with pytest.raises(RuntimeError):
            port.close()
        assert port._closed is False

        bindings.fail_destroy_source = False
        port.close()

        assert timers[0].destroyed is True
        assert port._residual_timer_sources == []
        assert port._closed is True
    finally:
        bindings.fail_destroy_source = False
        bindings.block_attach_source = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)


def test_nso133_02_c_timer_ownership_publishes_only_after_attach() -> None:
    """A successful attach publishes the timer; the callback belongs to it."""
    bindings, port = _live_port()
    try:
        bus = _bus(bindings)
        _attach(port, bus, generation=1)

        assert port._timer_source is not None
        assert port._timer_source is bindings.timer_sources[0]
        assert port._timer_source.attached is True
        assert port._residual_timer_sources == []
    finally:
        with contextlib.suppress(Exception):
            port.close()


# ── Phase 3 — stale detach reconciliation ──────────────────────────────────


def test_nso133_03_a_stale_successful_removal_reconciles_bookkeeping() -> None:
    """CASO 1: the native removal succeeded → the old receipt must clear."""
    bindings, port = _live_port()
    try:
        bus = _bus(bindings)
        _attach(port, bus, generation=1)
        assert bus.watch_installed is True

        bindings.block_watch_remove = True
        thread, errors = _detach_in_background(port)
        assert bindings.watch_remove_entered.wait(timeout=10)
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)
        assert bus.watch_installed is True  # still held by the native primitive

        bindings.block_watch_remove = False
        _release_and_drain(bindings, port)

        assert bus.watch_installed is False
        assert bus.remove_watch_count == 1
        assert port._bus_source is None, "a removed native watch stayed logical"
        assert port._bus is None

        port.close()
        _assert_full_native_closure(port, bus)
    finally:
        bindings.block_watch_remove = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)


def test_nso133_03_b_stale_removal_cannot_clear_a_newer_watch() -> None:
    """CASO 2: resource identity protects the newer generation's watch."""
    bindings, port = _live_port()
    try:
        old_bus = _bus(bindings)
        _attach(port, old_bus, generation=1)

        bindings.block_watch_remove = True
        thread, errors = _detach_in_background(port)
        assert bindings.watch_remove_entered.wait(timeout=10)
        thread.join(timeout=10)
        assert errors and isinstance(errors[0], ContextCommandTimeoutError)

        bindings.block_watch_remove = False
        _release_and_drain(bindings, port)

        # The stale removal reconciled only ITS OWN resource.
        assert old_bus.watch_installed is False
        assert port._bus_source is None

        # A newer generation installs its own native watch.
        fresh_bus = _bus(bindings)
        _attach(port, fresh_bus, generation=2)
        assert fresh_bus.watch_installed is True
        fresh_id = port._bus_source

        # The stale receipt can never clear the newer generation's ownership:
        # the PRODUCTIVE reconciliation is identity-based, not authority-based.
        assert port._reconcile_bus_removal(old_bus, 42) is False
        assert port._bus is fresh_bus
        assert port._bus_source == fresh_id
        assert fresh_bus.watch_installed is True, "the newer native watch was lost"
    finally:
        bindings.block_watch_remove = False
        with contextlib.suppress(Exception):
            _release_and_drain(bindings, port)
            port.close()


def test_nso133_03_c_already_absent_watch_does_not_block_convergence() -> None:
    """A physically absent watch is not a removal failure (§27)."""
    bindings, port = _live_port()
    try:
        bus = _bus(bindings)
        _attach(port, bus, generation=1)
        # The native watch disappears behind our back (external teardown).
        bus.watch_installed = False

        port._detach_pipeline_sources()

        assert port._bus_source is None
        assert port._bus is None
        port.close()
        _assert_full_native_closure(port, bus)
    finally:
        with contextlib.suppress(Exception):
            port.close()


# ── Phase 4 — terminal close convergence ───────────────────────────────────


def test_nso133_04_a_close_converges_from_pipeline_null_plus_residual_source() -> None:
    bindings, port = _live_port()
    try:
        bus = _bus(bindings)
        _attach(port, bus, generation=1)
        # The pipeline already reached NULL, but the watch is still native.
        port._pipeline = None

        port.close()

        _assert_full_native_closure(port, bus)
    finally:
        with contextlib.suppress(Exception):
            port.close()


def test_nso133_04_b_repeated_close_is_idempotent_after_convergence() -> None:
    bindings, port = _live_port()
    try:
        bus = _bus(bindings)
        _attach(port, bus, generation=1)

        port.close()
        port.close()

        _assert_full_native_closure(port, bus)
        assert bus.remove_watch_count == 1, "close re-entered the native removal"
    finally:
        with contextlib.suppress(Exception):
            port.close()


def test_nso133_04_c_close_refuses_closure_with_a_residual_watch_receipt() -> None:
    bindings, port = _live_port()
    try:
        bus = _bus(bindings)
        _attach(port, bus, generation=1)
        # Every other obligation is released cleanly first, so ONLY the
        # residual receipt can refuse closure.
        port._detach_pipeline_sources()
        assert port._bus_source is None

        # A residual receipt is the OBSERVABLE form of unproven native
        # ownership: the watch is back and its release cannot be proven.
        bus.watch_installed = True
        bus.fail_remove_watch = True
        port._residual_bus_watches.append((bus, 42))

        with pytest.raises(RuntimeError, match="retained native ownership"):
            port.close()

        assert port._closed is False
        assert port._residual_bus_watches != []
        assert bus.watch_installed is True

        # Repairing the native layer lets the same close() converge.
        bus.fail_remove_watch = False
        port.close()

        assert bus.watch_installed is False
        _assert_full_native_closure(port, bus)
    finally:
        bus.fail_remove_watch = False
        with contextlib.suppress(Exception):
            port.close()


def test_nso133_04_d_native_watch_without_bus_is_an_explicit_error() -> None:
    bindings, port = _live_port()
    try:
        port._bus_source = 42
        port._bus = None

        with pytest.raises(RuntimeError, match="without owning bus"):
            port._detach_pipeline_sources()
    finally:
        with contextlib.suppress(Exception):
            port.close()


def _unused(path: Path) -> None:
    return None
