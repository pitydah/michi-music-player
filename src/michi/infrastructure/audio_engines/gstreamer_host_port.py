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
        self._activated = False
        self._hello: dict[str, Any] | None = None
        self._host_lost_reason: str | None = None
        self._last_state: PlaybackStatus | None = None
        self._termination_kind: str | None = None
        self._runtime_failure_callback: Callable[[int, str], None] | None = None
        self._owner_invoker: object | None = None
        self._owner_queue: list[Callable[[], None]] = []
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
        self._supervisor.set_owner_drain(self._drain_all)
        self._supervisor.set_callback_handler(self._handle_host_callback)
        self._ensure_owner_invoker()
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
            self._closed = True
            self._activated = False
            self._command_generation += 1
        kind = self._supervisor.shutdown()
        with self._lock:
            self._termination_kind = kind
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

    # ── comandos de transporte ────────────────────────────────────────
    def load(self, file_path: Path) -> None:
        path = Path(file_path)
        with self._lock:
            self._command_generation += 1
        try:
            self._submit(
                HostOperation.LOAD,
                {"path": str(path)},
                deadline_s=self._load_deadline_s,
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
        """Direct resync evidence is transported with the Direct integration.

        Returning fabricated values would be false evidence; until the Direct
        stage is hosted this port reports nothing.
        """
        return {}

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
        except OutputHostError as exc:
            raise self._direct_error(
                "OUTPUT_HOST_DIRECT_TRANSPORT_FAILED", exc.detail
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
            raise self._direct_error(
                "OUTPUT_HOST_DIRECT_UNBOUND",
                "no Direct executor is bound to this hosted port",
            )
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
            sig = Signal()

            def __init__(self) -> None:
                super().__init__()
                self.sig.connect(drain, Qt.QueuedConnection)

        invoker = _OwnerInvoker()
        self._owner_invoker = invoker  # ownership: keep the QObject alive
        self._owner_dispatch = invoker.sig.emit

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

    def _enqueue(self, work: Callable[[], None]) -> None:
        with self._lock:
            self._owner_queue.append(work)
        dispatch = self._owner_dispatch
        if dispatch is not None:
            with contextlib.suppress(Exception):
                dispatch(self._drain_all)

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
            self._enqueue(lambda: self._commit_position(ms))
        elif kind == HostEvent.DURATION.value:
            ms = int(payload.get("ms") or 0)
            self._enqueue(lambda: self._commit_duration(ms))
        elif kind == HostEvent.HOST_FAULT.value:
            reason = str(payload.get("reason"))
            self._enqueue(lambda: self._relay_runtime_failure(reason))

    def _on_host_lost(self, generation: int, code: str, detail: str) -> None:
        with self._lock:
            if self._closed:
                return
            self._host_lost_reason = f"{code}: {detail}"
        self._enqueue(lambda: self._relay_runtime_failure(f"{code}: {detail}"))

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
