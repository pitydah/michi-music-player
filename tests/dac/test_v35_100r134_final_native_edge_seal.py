"""DAC-V35-100R1.3.4 — final native edge seal gates.

- ``fne134_01_*`` remove_watch exception preserves UNKNOWN native ownership
- ``fne134_02_*`` add_watch zero is an unowned acquisition (never claimed,
  never compensated by removing a pre-existing watch)
"""

from __future__ import annotations

import contextlib
import threading

import pytest
from test_gstreamer_audio_port import FakeBindings

from michi.infrastructure.audio_engines.gstreamer import (
    BusWatchNotAcquiredError,
    ContextCommandTimeoutError,
    GStreamerAudioPort,
)


class _OpaqueBus:
    """A bus that does NOT expose its native watch state (real Gst.Bus shape)."""

    def __init__(self, *, fail_remove: bool = True) -> None:
        self.add_watch_count = 0
        self.remove_attempts = 0
        self.fail_remove = fail_remove
        self.released = False

    def add_watch(self, _priority, _callback):
        self.add_watch_count += 1
        return 42

    def remove_watch(self):
        self.remove_attempts += 1
        if self.fail_remove:
            raise RuntimeError("opaque synthetic remove_watch failure")
        self.released = True
        return True


class _BlockingBindings(FakeBindings):
    """Fake bindings whose native bus-watch creation can be held open."""

    def __init__(self) -> None:
        super().__init__()
        self.block_bus_create = False
        self.bus_create_entered = threading.Event()
        self.bus_create_release = threading.Event()

    def create_bus_source(self, bus, callback, context=None):
        if self.block_bus_create:
            self.bus_create_entered.set()
            self.bus_create_release.wait(timeout=15)
        return super().create_bus_source(bus, callback, context)


def _live_port(**blocks):
    bindings = _BlockingBindings()
    for name, value in blocks.items():
        setattr(bindings, name, value)
    port = GStreamerAudioPort(bindings=bindings)
    port._ensure_pump()
    return bindings, port


def _revoked_attach(port, bus, bindings):
    """Drive a productive attach whose commit is revoked by a caller timeout."""
    port._bus = bus
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            port._attach_pipeline_sources(object(), bus, 1)
        except BaseException as exc:  # noqa: BLE001 — asserted by the caller
            errors.append(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    assert bindings.bus_create_entered.wait(timeout=10), (
        "attach never reached add_watch"
    )
    thread.join(timeout=10)
    assert errors and isinstance(errors[0], ContextCommandTimeoutError)
    bindings.block_bus_create = False
    bindings.bus_create_release.set()
    port._run_on_pump(lambda: None)  # deterministic pump barrier


# ── Phase 1 — remove_watch exception keeps uncertain ownership ─────────────


def test_fne134_01_a_opaque_bus_exception_retains_the_receipt() -> None:
    """An exception means the release was NOT proven — even without introspection."""
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = _OpaqueBus(fail_remove=True)
        _revoked_attach(port, bus, bindings)

        assert bus.remove_attempts == 1
        assert port._residual_bus_watches == [(bus, 42)], (
            "an UNKNOWN native state was collapsed into REMOVED"
        )

        # close() retries the receipt; while the release keeps failing, closure
        # must be refused.
        with pytest.raises(RuntimeError):
            port.close()
        assert port._closed is False
        assert port._residual_bus_watches == [(bus, 42)]

        # Repairing the native layer lets close() converge.
        bus.fail_remove = False
        port.close()

        assert bus.released is True
        assert port._residual_bus_watches == []
        assert port._closed is True
    finally:
        bindings.block_bus_create = False
        bindings.bus_create_release.set()
        with contextlib.suppress(Exception):
            port.close()


def test_fne134_01_b_introspectable_fake_exception_retains_the_receipt() -> None:
    """Exception handling must not depend on optional native introspection."""
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        bus.remove_watch_exception = RuntimeError("synthetic remove failure")
        _revoked_attach(port, bus, bindings)

        assert port._residual_bus_watches == [(bus, 42)]

        bus.remove_watch_exception = None
        port.close()

        assert port._residual_bus_watches == []
        assert bus.watch_installed is False
        assert port._closed is True
    finally:
        bindings.block_bus_create = False
        bindings.bus_create_release.set()
        with contextlib.suppress(Exception):
            port.close()


def test_fne134_01_c_proven_removal_retains_nothing() -> None:
    """A PROVEN release (True) must not leave a residual receipt."""
    bindings, port = _live_port(block_bus_create=True)
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        _revoked_attach(port, bus, bindings)

        assert bus.watch_installed is False
        assert port._residual_bus_watches == []
        assert port._bus_source is None
    finally:
        bindings.block_bus_create = False
        with contextlib.suppress(Exception):
            port.close()


# ── Phase 2 — add_watch zero is an unowned acquisition ─────────────────────


def test_fne134_02_c_preexisting_watch_is_never_claimed_nor_removed() -> None:
    """A zero acquisition must not become ownership nor destroy a foreign watch."""
    bindings, port = _live_port()
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        # Another owner already installed a native watch on this bus.
        bus.watch_installed = True
        port._bus = bus

        with pytest.raises(BusWatchNotAcquiredError):
            port._attach_pipeline_sources(object(), bus, 1)

        assert bus.watch_installed is True, "removed a watch Michi never owned"
        assert bus.remove_watch_count == 0, "compensated an unowned watch"
        assert bus.add_watch_count == 1
        assert port._bus_source is None
        assert port._bus_source_attached is False
        assert port._timer_source is None
        assert port._residual_bus_watches == []
    finally:
        with contextlib.suppress(Exception):
            bus.watch_installed = False
            port.close()


def test_fne134_02_d_normal_acquisition_and_release_unchanged() -> None:
    """No pre-existing watch: acquisition, ownership, timer and release work."""
    bindings, port = _live_port()
    try:
        bus = bindings.get_bus(bindings.make_playbin3())
        port._bus = bus

        port._attach_pipeline_sources(object(), bus, 1)

        assert bus.add_watch_count == 1
        assert port._bus_source == 42
        assert port._bus_source_attached is True
        assert port._timer_source is not None
        assert port._timer_source.attached is True

        port._detach_pipeline_sources()

        assert bus.watch_installed is False
        assert bus.remove_watch_count == 1, "exactly Michi's own watch was removed"
        assert port._bus_source is None
        assert port._residual_bus_watches == []

        port.close()
        assert port._closed is True
    finally:
        with contextlib.suppress(Exception):
            port.close()
