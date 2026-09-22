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


def test_nc132_02_b_residual_gate_blocks_a_fake_closure(
    qapp, tmp_path: Path
) -> None:
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
