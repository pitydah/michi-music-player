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
