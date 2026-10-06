"""Parent-side hosted AudioPort proxy.

Implements the canonical AudioPort contract by forwarding typed commands to
the supervised GStreamer output host and dispatching host events on the
parent owner thread. It owns semantic LOCAL intent (subscriptions, last
observed state, generation fences) — never a GstPipeline, GstBus, GstElement,
GLib context or native state: the productive parent process keeps ZERO
native GStreamer objects for the active transport.

All app callbacks are delivered through the owner queue: the IPC reader
thread never invokes application callbacks directly. During a bounded
command wait the owner drains the queue itself (the supervisor's owner-drain
hook), so a child blocked in a reverse callback can never deadlock us.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from michi.application.ports import (
    AudioLoadError,
    AudioPort,
    AudioTransportCommandError,
    AudioTransportUnavailableError,
)
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    EXITED_BEFORE,
    GRACEFUL,
    REAP_PENDING,
    GStreamerHostSupervisor,
    OutputHostCommandError,
    OutputHostError,
    OutputHostLostError,
    OutputHostShutdownError,
    OutputHostTimeoutError,
)
from michi.infrastructure.audio_engines.gstreamer_host_direct import (
    CB_ABORT,
    CB_BEGIN_RUNTIME,
    CB_MARK_PREVIOUS_SOURCE_RELEASED,
    CB_OBSERVE_RUNTIME,
    CB_RECORD_RUNTIME_ANOMALY,
    CB_RELEASE,
    CB_VERIFY_PREROLL,
    handle_from_wire,
    handle_to_wire,
    preparation_to_wire,
    snapshot_from_wire,
)
from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    HostEvent,
    HostOperation,
)

_logger = logging.getLogger(__name__)


class GStreamerHostedAudioPort(AudioPort):
    """Canonical AudioPort over the hosted GStreamer runtime."""

    def __init__(
        self,
        supervisor: GStreamerHostSupervisor,
        *,
        owner_dispatch: Callable[[Callable[[], None]], None] | None = None,
        command_deadline_s: float = 10.0,
        load_deadline_s: float = 20.0,
        direct_executor: object | None = None,
    ) -> None:
        super().__init__()
        self._supervisor = supervisor
        self._direct_executor = direct_executor
        self._callback_deadline_s = 10.0
        self._owner_dispatch = owner_dispatch
        self._command_deadline_s = max(0.05, float(command_deadline_s))
        self._load_deadline_s = max(0.05, float(load_deadline_s))
        self._lock = threading.RLock()
        self._command_generation = 0
        self._closed = False
        self._closing = False
        self._activated = False
        self._hello: dict[str, Any] | None = None
        self._host_lost_reason: str | None = None
        self._last_state: PlaybackStatus | None = None
        self._termination_kind: str | None = None
        self._runtime_failure_callback: Callable[[int, str], None] | None = None
        self._owner_invoker: object | None = None
        self._qt_app: object | None = None
        self._owner_thread_ident: int | None = None
        self._owner_queue: list[Callable[[], None]] = []
        self._latest_work: dict[str, Callable[[], None]] = {}
        self._latest_queued: set[str] = set()
        self._stale_callbacks = 0
        self._eom: list[Callable[[], None]] = []
        self._pos: list[Callable[[int], None]] = []
        self._dur: list[Callable[[int], None]] = []
        self._acc: list[Callable[[Path], None]] = []
        self._rej: list[Callable[[Path, str], None]] = []
        self._pst: list[Callable[[PlaybackStatus], None]] = []
        self._stale_events = 0

    # ── activación / cierre ───────────────────────────────────────────
    def activate(self) -> None:
        """Start the host, handshake, open the engine inside the child."""
        with self._lock:
            if self._activated and not self._closed:
                return
        self._supervisor.set_event_sink(self._on_host_event)
        self._supervisor.set_lost_sink(self._on_host_lost)
        self._supervisor.set_owner_drain(self._owner_wait_tick)
        self._supervisor.set_callback_handler(self._handle_host_callback)
        self._ensure_owner_invoker()
        self._capture_owner_runtime()
        try:
            hello = self._supervisor.start()
        except OutputHostError as exc:
            raise AudioTransportUnavailableError(
                f"GStreamer output host unavailable: {exc.detail}"
            ) from exc
        try:
            self._submit(
                HostOperation.OPEN,
                {},
                deadline_s=self._command_deadline_s,
                bump_generation=False,
            )
        except OutputHostError as exc:
            with contextlib.suppress(Exception):
                self._supervisor.shutdown()
            raise AudioTransportUnavailableError(
                f"GStreamer engine open failed in host: {exc.detail}"
            ) from exc
        with self._lock:
            self._hello = dict(hello)
            self._activated = True
            self._closed = False
            self._host_lost_reason = None

    def close(self) -> None:
        """Bounded terminal close: native truth ends at process death.

        The parent never waits forever for pipeline NULL / bus detach / loop
        exit. A host that cannot be reaped is a truthful shutdown failure.
        """
        with self._lock:
            if self._closed:
                return
            # Not closed yet: the Direct release may still need to reach the
            # live child; only the closing flag gates the dead-host path.
            self._closing = True
            self._activated = False
            self._command_generation += 1
        # Direct truth is invalidated FIRST, while the live child can still
        # receive the discard; a host that is already gone needs no discard
        # (the native staged state died with its process).
        cleanup_error: Exception | None = None
        executor = self._direct_executor
        if executor is not None:
            try:
                executor.release("gstreamer_close")
            except Exception as exc:  # noqa: BLE001 - re-raised after invalidation
                cleanup_error = exc
        kind = self._supervisor.shutdown()
        with self._lock:
            self._closed = True
            self._closing = False
            self._termination_kind = kind
        if cleanup_error is not None:
            # Truth was invalidated; keep the port retryable for the provider.
            with self._lock:
                self._closed = False
                self._closing = False
            raise OutputHostShutdownError(
                f"Direct execution release failed during host close: {cleanup_error}"
            ) from cleanup_error
        if kind == REAP_PENDING:
            raise OutputHostShutdownError(
                "GStreamer output host could not be reaped after SIGKILL"
            )

    @property
    def termination_kind(self) -> str | None:
        with self._lock:
            return self._termination_kind

    @property
    def host_hello(self) -> dict[str, Any] | None:
        with self._lock:
            return None if self._hello is None else dict(self._hello)

    def set_runtime_failure_callback(
        self, callback: Callable[[int, str], None] | None
    ) -> None:
        with self._lock:
            self._runtime_failure_callback = callback

    # ── seam asíncrono (el owner NUNCA espera el deadline) ────────────
    def submit_async(
        self,
        operation: HostOperation,
        payload: dict[str, Any] | None = None,
        *,
        on_done: Callable[[dict[str, Any]], None] | None = None,
        on_failed: Callable[[Exception], None] | None = None,
        deadline_s: float | None = None,
        bump_generation: bool = False,
    ) -> None:
        """Execute one command on a worker; completion lands on the owner.

        The owner thread is free while the host command is in flight: the
        completion callback is enqueued through the canonical owner queue
        (Qt dispatch in production, explicit drain in tests). Failures are
        delivered as the original typed exception — never swallowed.
        """
        deadline = self._command_deadline_s if deadline_s is None else deadline_s

        def work() -> dict[str, Any]:
            return self._submit(
                operation,
                payload or {},
                deadline_s=deadline,
                bump_generation=bump_generation,
            )

        self._run_worker(
            work, on_done=on_done, on_failed=on_failed, name=str(operation)
        )

    def load_async(
        self,
        file_path: Path,
        *,
        on_done: Callable[[dict[str, Any]], None] | None = None,
        on_failed: Callable[[Exception], None] | None = None,
    ) -> None:
        """Async load: owner-free; the failure carries the SAME typed
        AudioLoadError (with previous_source_preserved) as the sync path."""
        path = Path(file_path)
        self._run_worker(
            lambda: self._load_once(path, deadline_s=self._load_deadline_s),
            on_done=on_done,
            on_failed=on_failed,
            name=str(HostOperation.LOAD),
        )

    def play_async(self, *, on_done=None, on_failed=None) -> None:
        self._command_async(HostOperation.PLAY, None, on_done, on_failed)

    def pause_async(self, *, on_done=None, on_failed=None) -> None:
        self._command_async(HostOperation.PAUSE, None, on_done, on_failed)

    def resume_async(self, *, on_done=None, on_failed=None) -> None:
        self._command_async(HostOperation.RESUME, None, on_done, on_failed)

    def stop_async(self, *, on_done=None, on_failed=None) -> None:
        def work() -> dict[str, Any]:
            with self._lock:
                self._command_generation += 1
            return self._command(HostOperation.STOP)

        self._run_worker(work, on_done=on_done, on_failed=on_failed, name="stop")

    def seek_async(
        self,
        position_ms: int,
        *,
        on_done=None,
        on_failed=None,
    ) -> None:
        self._command_async(
            HostOperation.SEEK, {"position_ms": int(position_ms)}, on_done, on_failed
        )

    def _command_async(self, operation, payload, on_done, on_failed) -> None:
        self._run_worker(
            lambda: self._command(operation, payload),
            on_done=on_done,
            on_failed=on_failed,
            name=str(operation),
        )

    def _run_worker(self, work, *, on_done, on_failed, name: str) -> None:
        def run() -> None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - typed completion boundary
                # Bind before the lambda: Python clears `exc` when the except
                # block exits, and the closure runs later on the owner thread.
                error = exc
                if on_failed is not None:
                    self._enqueue(lambda: on_failed(error))
            else:
                if on_done is not None:
                    value = result
                    self._enqueue(lambda: on_done(value))

        threading.Thread(
            target=run,
            name=f"gst-host-cmd-{name}",
            daemon=True,
        ).start()

    # ── comandos de transporte ────────────────────────────────────────
    def load(self, file_path: Path) -> None:
        self._load_once(Path(file_path), deadline_s=self._load_deadline_s)

    def _load_once(self, path: Path, *, deadline_s: float) -> dict[str, Any]:
        with self._lock:
            self._command_generation += 1
        try:
            return self._submit(
                HostOperation.LOAD,
                {"path": str(path)},
                deadline_s=deadline_s,
            )
        except OutputHostCommandError as exc:
            payload = exc.payload
            if "previous_source_preserved" in payload:
                raise AudioLoadError(
                    path,
                    exc.detail,
                    previous_source_preserved=bool(
                        payload["previous_source_preserved"]
                    ),
                ) from exc
            raise AudioTransportCommandError(str(exc)) from exc
        except (OutputHostTimeoutError, OutputHostLostError) as exc:
            # The native pipeline died with the host incarnation: the previous
            # source is NOT preserved and nothing may claim it is.
            raise AudioLoadError(
                path, exc.detail, previous_source_preserved=False
            ) from exc
        except OutputHostError as exc:
            raise AudioTransportUnavailableError(str(exc)) from exc

    def play(self) -> None:
        self._command(HostOperation.PLAY)

    def pause(self) -> None:
        self._command(HostOperation.PAUSE)

    def resume(self) -> None:
        self._command(HostOperation.RESUME)

    def stop(self) -> None:
        with self._lock:
            self._command_generation += 1
        self._command(HostOperation.STOP)

    def seek(self, position_ms: int) -> None:
        self._command(HostOperation.SEEK, {"position_ms": int(position_ms)})

    def set_volume(self, value: int) -> None:
        self._command(HostOperation.SET_VOLUME, {"value": int(value)})

    def set_muted(self, muted: bool) -> None:
        self._command(HostOperation.SET_MUTED, {"muted": bool(muted)})

    def position(self) -> int:
        payload = self._command(HostOperation.QUERY_POSITION)
        return int(payload.get("value") or 0)

    def duration(self) -> int:
        payload = self._command(HostOperation.QUERY_DURATION)
        return int(payload.get("value") or 0)

    def backend_state(self) -> str | None:
        with self._lock:
            return None if self._last_state is None else self._last_state.name.lower()

    def resync_evidence(self) -> dict[str, int | None]:
        """Configured and MEASURED resync hold of the current Direct execution.

        The evidence is produced by the native port inside the host and
        transported verbatim (parity with the in-process port). A host that
        cannot answer truthfully yields NO evidence (empty dict + a warning),
        never fabricated values.
        """
        try:
            payload = self._submit(
                HostOperation.QUERY_RESYNC_EVIDENCE,
                {},
                deadline_s=min(2.0, self._command_deadline_s),
            )
        except OutputHostError as exc:
            _logger.warning("resync evidence unavailable: %s", exc)
            return {}
        evidence = payload.get("evidence")
        if not isinstance(evidence, dict):
            return {}
        return {
            str(key): value
            for key, value in evidence.items()
            if value is None or isinstance(value, (int, str))
        }

    # ── Direct staging (transport only; authority stays in the parent) ─
    def stage_direct_load(self, preparation: object, *, executor: object) -> None:
        self._require_direct_executor(executor)
        try:
            self._submit(
                HostOperation.STAGE_DIRECT,
                {"preparation": preparation_to_wire(preparation)},  # type: ignore[arg-type]
                deadline_s=self._command_deadline_s,
            )
        except OutputHostCommandError as exc:
            raise self._direct_error(exc.code, exc.detail) from exc
        except OutputHostError as exc:
            raise self._direct_error(
                "OUTPUT_HOST_DIRECT_TRANSPORT_FAILED", exc.detail
            ) from exc

    def discard_direct_load(self, handle: object, *, executor: object) -> bool:
        self._require_direct_executor(executor)
        try:
            payload = self._submit(
                HostOperation.DISCARD_DIRECT,
                {"handle": handle_to_wire(handle)},  # type: ignore[arg-type]
                deadline_s=self._command_deadline_s,
            )
        except OutputHostCommandError as exc:
            raise self._direct_error(exc.code, exc.detail) from exc
        except (OutputHostError, AudioTransportUnavailableError) as exc:
            if self._closing:
                # The host is gone: the staged native state died with it. A
                # close must not fail because a dead process cannot answer.
                return False
            raise self._direct_error(
                "OUTPUT_HOST_DIRECT_TRANSPORT_FAILED", str(exc)
            ) from exc
        return bool(payload.get("discarded", False))

    def _require_direct_executor(self, executor: object) -> None:
        if self._direct_executor is None or executor is not self._direct_executor:
            raise self._direct_error(
                "DIRECT_EXECUTOR_IDENTITY_MISMATCH",
                "the Direct executor is not bound to this hosted port",
            )

    @staticmethod
    def _direct_error(code: str, detail: str):
        from michi.infrastructure.audio_output.direct_output_executor import (
            DirectExecutorError,
        )

        return DirectExecutorError(code, detail)

    # ── reverse callbacks (child -> parent) ───────────────────────────
    def _handle_host_callback(
        self, frame: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """Reader-thread entry: marshal to the owner and wait (bounded).

        The owner processes this either in its Qt dispatch loop or inside a
        bounded command wait (owner-drain hook), so the child can never
        deadlock against the parent.
        """
        # Two-domain fence for REVERSE callbacks too: a callback from a
        # superseded command generation can never mutate parent authority.
        # During close the child may still answer the release handoff with
        # the generation it last processed, which is intentionally allowed.
        with self._lock:
            generation = frame.get("command_generation")
            closing = self._closing
        if generation != self._command_generation and not closing:
            with self._lock:
                self._stale_callbacks += 1
            return (
                False,
                {
                    "code": "OUTPUT_HOST_STALE_RESULT",
                    "detail": ("callback belongs to a superseded command generation"),
                },
            )
        import threading

        holder: dict[str, Any] = {
            "done": threading.Event(),
            "result": (
                False,
                {
                    "code": "OUTPUT_HOST_CALLBACK_TIMEOUT",
                    "detail": "parent did not process the callback in time",
                },
            ),
        }

        def work() -> None:
            try:
                payload = self._execute_callback(frame)
            except Exception as exc:  # noqa: BLE001 - typed rejection boundary
                code = getattr(exc, "code", None) or type(exc).__name__
                holder["result"] = (
                    False,
                    {"code": str(code), "detail": str(exc)[:1000]},
                )
            else:
                holder["result"] = (True, payload)
            finally:
                holder["done"].set()

        self._enqueue(work)
        if not holder["done"].wait(self._callback_deadline_s):
            return (
                False,
                {
                    "code": "OUTPUT_HOST_CALLBACK_TIMEOUT",
                    "detail": "parent owner did not drain the callback queue",
                },
            )
        return holder["result"]

    def _execute_callback(self, frame: dict[str, Any]) -> dict[str, Any]:
        payload = frame.get("payload") or {}
        name = payload.get("callback")
        executor = self._direct_executor
        if executor is None:
            # Shared-only composition: the child attaches the coordinator
            # unconditionally, so the harmless sidecar hooks must be accepted
            # as no-ops (an in-process port without direct_executor would
            # never call them). Direct classification still fails closed.
            if name == CB_VERIFY_PREROLL:
                raise self._direct_error(
                    "OUTPUT_HOST_DIRECT_UNBOUND",
                    "no Direct executor is bound to this hosted port",
                )
            if name in (CB_OBSERVE_RUNTIME, CB_RECORD_RUNTIME_ANOMALY):
                return {"recorded": False}
            return {}
        if name == CB_MARK_PREVIOUS_SOURCE_RELEASED:
            executor.mark_previous_source_released()
            return {}
        if name == CB_BEGIN_RUNTIME:
            executor.begin_runtime(
                handle_from_wire(payload.get("handle")),
                port_generation=int(payload.get("port_generation") or 0),
            )
            return {}
        if name == CB_VERIFY_PREROLL:
            executor.verify_preroll(
                handle_from_wire(payload.get("handle")),
                snapshot_from_wire(payload.get("snapshot")),
            )
            return {}
        if name == CB_OBSERVE_RUNTIME:
            recorded = executor.observe_runtime(
                handle_from_wire(payload.get("handle")),
                snapshot_from_wire(payload.get("snapshot")),
            )
            return {"recorded": bool(recorded)}
        if name == CB_RECORD_RUNTIME_ANOMALY:
            recorded = executor.record_runtime_anomaly(
                handle_from_wire(payload.get("handle")),
                str(payload.get("detail") or ""),
            )
            return {"recorded": bool(recorded)}
        if name == CB_ABORT:
            executor.abort(
                handle_from_wire(payload.get("handle")),
                str(payload.get("reason") or ""),
            )
            return {}
        if name == CB_RELEASE:
            executor.release(str(payload.get("reason") or ""))
            return {}
        raise self._direct_error(
            "OUTPUT_HOST_CALLBACK_UNKNOWN", f"unknown callback {name!r}"
        )

    # ── subscriptions (canonical AudioPort) ───────────────────────────
    def subscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if callback not in self._eom:
            self._eom.append(callback)

    def unsubscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if callback in self._eom:
            self._eom.remove(callback)

    def subscribe_position_changed(self, callback: Callable[[int], None]) -> None:
        if callback not in self._pos:
            self._pos.append(callback)

    def unsubscribe_position_changed(self, callback: Callable[[int], None]) -> None:
        if callback in self._pos:
            self._pos.remove(callback)

    def subscribe_duration_changed(self, callback: Callable[[int], None]) -> None:
        if callback not in self._dur:
            self._dur.append(callback)

    def unsubscribe_duration_changed(self, callback: Callable[[int], None]) -> None:
        if callback in self._dur:
            self._dur.remove(callback)

    def subscribe_media_accepted(self, callback: Callable[[Path], None]) -> None:
        if callback not in self._acc:
            self._acc.append(callback)

    def unsubscribe_media_accepted(self, callback: Callable[[Path], None]) -> None:
        if callback in self._acc:
            self._acc.remove(callback)

    def subscribe_media_rejected(self, callback: Callable[[Path, str], None]) -> None:
        if callback not in self._rej:
            self._rej.append(callback)

    def unsubscribe_media_rejected(self, callback: Callable[[Path, str], None]) -> None:
        if callback in self._rej:
            self._rej.remove(callback)

    def subscribe_playback_state_changed(
        self, callback: Callable[[PlaybackStatus], None]
    ) -> None:
        if callback not in self._pst:
            self._pst.append(callback)

    def unsubscribe_playback_state_changed(
        self, callback: Callable[[PlaybackStatus], None]
    ) -> None:
        if callback in self._pst:
            self._pst.remove(callback)

    def _capture_owner_runtime(self) -> None:
        """Owner identity + Qt application for responsive bounded waits."""
        self._owner_thread_ident = threading.get_ident()
        try:
            from PySide6.QtCore import QCoreApplication
        except Exception:  # noqa: BLE001 - Qt is optional for the transport
            self._qt_app = None
            return
        self._qt_app = QCoreApplication.instance()

    def _owner_wait_tick(self) -> None:
        """Owner-runtime tick while a parent-owned deadline elapses.

        Drains the port owner queue AND pumps the real Qt event loop when the
        caller IS the Qt owner thread, so timers, input, animation and paint
        keep running during a bounded host wait instead of freezing them.
        """
        self._drain_all()
        app = self._qt_app
        if app is None:
            return
        if threading.get_ident() != self._owner_thread_ident:
            return
        try:
            app.processEvents()
        except Exception:  # noqa: BLE001 - never let pumping break the wait
            _logger.debug("Qt event pumping failed during host wait", exc_info=True)

    def _ensure_owner_invoker(self) -> None:
        """Production Qt dispatch: queued signal into the owner thread.

        Only created when a QCoreApplication already exists; tests without a
        Qt loop drain explicitly through ``dispatch_pending()``.
        """
        if self._owner_dispatch is not None:
            return
        try:
            from PySide6.QtCore import QCoreApplication, QObject, Qt, Signal
        except Exception:  # noqa: BLE001 - Qt is optional for the transport
            return
        if QCoreApplication.instance() is None:
            return
        drain = self._drain_all

        class _OwnerInvoker(QObject):
            # Zero-argument wake signal: the queued delivery runs the drain on
            # the owner thread. The dispatcher callback argument (the drain
            # itself in every composition) is intentionally ignored on this
            # path; emitting a callback through a zero-arg signal was a real
            # dispatch bug (silently swallowed by an over-broad suppression).
            wake = Signal()

            def __init__(self) -> None:
                super().__init__()
                self.wake.connect(drain, Qt.QueuedConnection)

        invoker = _OwnerInvoker()
        self._owner_invoker = invoker  # ownership: keep the QObject alive

        def dispatch_on_owner(_callback: Callable[[], None]) -> None:
            invoker.wake.emit()

        self._owner_dispatch = dispatch_on_owner

    # ── owner queue ───────────────────────────────────────────────────
    def dispatch_pending(self) -> None:
        """Run queued owner work (tests without a Qt loop)."""
        self._drain_all()

    def _drain_all(self) -> None:
        while True:
            with self._lock:
                if not self._owner_queue:
                    return
                work = self._owner_queue.pop(0)
            with contextlib.suppress(Exception):
                work()

    def _enqueue_latest(self, key: str, work: Callable[[], None]) -> None:
        """Latest-value coalescing for high-frequency observation events.

        Only position/duration ride this path (latest-wins semantics); every
        critical event (EOS, ERROR, MEDIA_ACCEPTED/REJECTED, HOST_FAULT,
        state changes) keeps its individual queue entry and is NEVER merged
        or dropped.
        """
        with self._lock:
            self._latest_work[key] = work
            if key in self._latest_queued:
                return
            self._latest_queued.add(key)

        def run() -> None:
            with self._lock:
                pending = self._latest_work.pop(key, None)
                self._latest_queued.discard(key)
            if pending is not None:
                with contextlib.suppress(Exception):
                    pending()

        self._enqueue(run)

    def _enqueue(self, work: Callable[[], None]) -> None:
        with self._lock:
            self._owner_queue.append(work)
        dispatch = self._owner_dispatch
        if dispatch is not None:
            try:
                dispatch(self._drain_all)
            except Exception:  # noqa: BLE001 - reported, never silently lost
                _logger.warning(
                    "owner dispatch failed; the event stays queued",
                    exc_info=True,
                )

    # ── IPC entrante ──────────────────────────────────────────────────
    def _on_host_event(self, frame: dict[str, Any]) -> None:
        payload = frame.get("payload") or {}
        kind = payload.get("event")
        generation = frame.get("command_generation")
        with self._lock:
            if self._closed or generation != self._command_generation:
                self._stale_events += 1
                return
        if kind == HostEvent.STATE_CHANGED.value:
            status = PlaybackStatus[str(payload.get("status"))]
            self._enqueue(lambda: self._commit_state(status))
        elif kind == HostEvent.MEDIA_ACCEPTED.value:
            path = Path(str(payload.get("path")))
            self._enqueue(lambda: self._commit_accepted(path))
        elif kind == HostEvent.MEDIA_REJECTED.value:
            path = Path(str(payload.get("path")))
            reason = str(payload.get("reason"))
            self._enqueue(lambda: self._commit_rejected(path, reason))
        elif kind == HostEvent.EOS.value:
            self._enqueue(self._commit_eos)
        elif kind == HostEvent.POSITION.value:
            ms = int(payload.get("ms") or 0)
            self._enqueue_latest("position", lambda: self._commit_position(ms))
        elif kind == HostEvent.DURATION.value:
            ms = int(payload.get("ms") or 0)
            self._enqueue_latest("duration", lambda: self._commit_duration(ms))
        elif kind == HostEvent.HOST_FAULT.value:
            reason = str(payload.get("reason"))
            self._enqueue(lambda: self._relay_runtime_failure(reason))

    def _on_host_lost(self, generation: int, code: str, detail: str) -> None:
        with self._lock:
            if self._closed:
                return
            self._host_lost_reason = f"{code}: {detail}"
        reason = f"{code}: {detail}"
        self._enqueue(lambda: self._commit_host_loss(reason))

    def _commit_host_loss(self, reason: str) -> None:
        """Owner-thread host-loss commit.

        Parity with the in-process pump death: record the anomaly on the
        CURRENT execution (when one exists) and then publish the canonical
        runtime failure so convergence policy is unchanged. The Direct truth
        itself is invalidated on close(), never silently kept alive here.
        """
        executor = self._direct_executor
        if executor is not None:
            handle = getattr(executor, "handle", None)
            if handle is not None:
                with contextlib.suppress(Exception):
                    executor.record_runtime_anomaly(
                        handle, f"output host lost: {reason}"
                    )
        self._relay_runtime_failure(reason)

    # ── commits owner ─────────────────────────────────────────────────
    def _commit_state(self, status: PlaybackStatus) -> None:
        with self._lock:
            self._last_state = status
            callbacks = list(self._pst)
        for callback in callbacks:
            with contextlib.suppress(Exception):
                callback(status)

    def _commit_accepted(self, path: Path) -> None:
        for callback in list(self._acc):
            with contextlib.suppress(Exception):
                callback(path)

    def _commit_rejected(self, path: Path, reason: str) -> None:
        for callback in list(self._rej):
            with contextlib.suppress(Exception):
                callback(path, reason)

    def _commit_eos(self) -> None:
        for callback in list(self._eom):
            with contextlib.suppress(Exception):
                callback()

    def _commit_position(self, ms: int) -> None:
        for callback in list(self._pos):
            with contextlib.suppress(Exception):
                callback(ms)

    def _commit_duration(self, ms: int) -> None:
        for callback in list(self._dur):
            with contextlib.suppress(Exception):
                callback(ms)

    def _relay_runtime_failure(self, reason: str) -> None:
        with self._lock:
            callback = self._runtime_failure_callback
            generation = self._command_generation
        if callback is not None:
            with contextlib.suppress(Exception):
                callback(generation, reason)

    # ── internos ──────────────────────────────────────────────────────
    def _command(
        self, operation: HostOperation, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            return self._submit(
                operation, payload or {}, deadline_s=self._command_deadline_s
            )
        except OutputHostCommandError as exc:
            raise AudioTransportCommandError(str(exc)) from exc
        except OutputHostError as exc:
            raise AudioTransportUnavailableError(str(exc)) from exc

    def _submit(
        self,
        operation: HostOperation,
        payload: dict[str, Any],
        *,
        deadline_s: float,
        bump_generation: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            if self._closed:
                raise AudioTransportUnavailableError("GStreamer output host is closed")
            if self._host_lost_reason is not None:
                raise AudioTransportUnavailableError(
                    f"GStreamer output host was lost: {self._host_lost_reason}"
                )
            if bump_generation:
                self._command_generation += 1
            generation = self._command_generation
        return self._supervisor.submit(
            operation,
            payload,
            deadline_s=deadline_s,
            command_generation=generation,
        )


# Backwards-compatible aliases for diagnostics/tests.
HOST_GRACEFUL = GRACEFUL
HOST_EXITED_BEFORE = EXITED_BEFORE
