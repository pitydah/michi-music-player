"""Parent-side supervisor for the GStreamer output host process.

Owns the fault boundary: spawn, bounded handshake, parent-side deadlines,
termination ladder (SHUTDOWN -> SIGTERM -> SIGKILL -> reap), generation
retirement and diagnostics. It NEVER owns playback/output/Direct/Signal
Truth semantics: frames are routed to the owner-side consumers untouched.

Every hazardous command is bounded by a PARENT clock; the real bound on a
wedged child is the killable process, not a Python timeout inside the child.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    FrameDecoder,
    HostOperation,
    HostProtocolError,
    MessageKind,
    encode_message,
    error_payload,
    make_message,
)

#: Termination outcomes recorded per host incarnation (never guessed).
GRACEFUL = "GRACEFUL"
FORCED_TERM = "FORCED_TERM"
FORCED_KILL = "FORCED_KILL"
EXITED_BEFORE = "EXITED_BEFORE"
REAP_PENDING = "REAP_PENDING"


class OutputHostError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class OutputHostStartError(OutputHostError):
    def __init__(self, detail: str) -> None:
        super().__init__("OUTPUT_HOST_START_FAILED", detail)


class OutputHostTimeoutError(OutputHostError):
    def __init__(self, detail: str) -> None:
        super().__init__("OUTPUT_HOST_TIMEOUT", detail)


class OutputHostLostError(OutputHostError):
    def __init__(self, detail: str) -> None:
        super().__init__("OUTPUT_HOST_LOST", detail)


class OutputHostCommandError(OutputHostError):
    def __init__(
        self, code: str, detail: str, payload: dict[str, Any] | None = None
    ) -> None:
        super().__init__(code or "OUTPUT_HOST_COMMAND_FAILED", detail)
        self.payload: dict[str, Any] = dict(payload or {})


class OutputHostProtocolError(OutputHostError):
    def __init__(self, detail: str) -> None:
        super().__init__("OUTPUT_HOST_PROTOCOL_ERROR", detail)


class OutputHostShutdownError(OutputHostError):
    def __init__(self, detail: str) -> None:
        super().__init__("OUTPUT_HOST_SHUTDOWN_FAILED", detail)


class OutputHostStaleError(OutputHostError):
    def __init__(self, detail: str) -> None:
        super().__init__("OUTPUT_HOST_STALE_RESULT", detail)


class SupervisorState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class _PendingRequest:
    request_id: str
    operation: str | None
    expected_command_generation: int = 0
    response: dict[str, Any] | None = None
    error: OutputHostError | None = None
    condition: threading.Condition = field(default_factory=threading.Condition)


#: Default production argv builder: genuinely fresh interpreter, never fork().
def _default_command_factory(fd: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "michi.infrastructure.audio_engines.gstreamer_host_process",
        "--fd",
        str(fd),
    ]


class GStreamerHostSupervisor:
    """Spawn, bound, kill, reap — never block forever, never leak a child."""

    def __init__(
        self,
        *,
        command_factory: Callable[[int], list[str]] | None = None,
        start_timeout_s: float = 15.0,
        command_timeout_s: float = 10.0,
        terminate_grace_s: float = 2.0,
        term_grace_s: float = 2.0,
        kill_grace_s: float = 2.0,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        on_lost: Callable[[int, str, str], None] | None = None,
        callback_handler: Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]]
        | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._command_factory = command_factory or _default_command_factory
        self._start_timeout_s = max(0.05, float(start_timeout_s))
        self._command_timeout_s = max(0.05, float(command_timeout_s))
        self._terminate_grace_s = max(0.05, float(terminate_grace_s))
        self._term_grace_s = max(0.05, float(term_grace_s))
        self._kill_grace_s = max(0.05, float(kill_grace_s))
        self._on_event = on_event
        self._on_lost = on_lost
        self._callback_handler = callback_handler
        self._env = env
        self._lock = threading.RLock()
        self._send_lock = threading.Lock()
        self._state = SupervisorState.STOPPED
        self._process: subprocess.Popen[bytes] | None = None
        self._socket: socket.socket | None = None
        self._reader: threading.Thread | None = None
        self._reader_stop = threading.Event()
        self._pending: dict[str, _PendingRequest] = {}
        self._host_generation = 0
        self._active_generation: int | None = None
        self._accepting_frames = False
        self._hello: dict[str, Any] | None = None
        self._decoder = FrameDecoder()
        self._started_at: float | None = None
        self._last_request_id: str | None = None
        self._last_operation: str | None = None
        self._last_progress_at: float | None = None
        self._termination_kind: str | None = None
        self._lost_reason: str | None = None
        self._stale_events = 0
        self._stale_responses = 0
        self._stale_callbacks = 0
        # Serializes an owner waiting on a command while draining owner frames
        # (reverse callbacks) so the child can never deadlock against us.
        self._owner_drain: Callable[[], None] | None = None

    # ── configuración ─────────────────────────────────────────────────
    def set_owner_drain(self, drain: Callable[[], None] | None) -> None:
        self._owner_drain = drain

    def set_event_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        with self._lock:
            self._on_event = sink

    def set_lost_sink(self, sink: Callable[[int, str, str], None] | None) -> None:
        with self._lock:
            self._on_lost = sink

    def set_callback_handler(
        self,
        handler: Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]] | None,
    ) -> None:
        with self._lock:
            self._callback_handler = handler

    @property
    def state(self) -> SupervisorState:
        with self._lock:
            return self._state

    @property
    def host_generation(self) -> int:
        with self._lock:
            return self._host_generation

    @property
    def pid(self) -> int | None:
        with self._lock:
            process = self._process
            return None if process is None else process.pid

    @property
    def hello(self) -> dict[str, Any] | None:
        with self._lock:
            return None if self._hello is None else dict(self._hello)

    @property
    def termination_kind(self) -> str | None:
        with self._lock:
            return self._termination_kind

    def diagnostics(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            return {
                "state": self._state.value,
                "pid": None if process is None else process.pid,
                "host_generation": self._host_generation,
                "started_at": self._started_at,
                "hello": None if self._hello is None else dict(self._hello),
                "last_request_id": self._last_request_id,
                "last_operation": self._last_operation,
                "last_progress_at": self._last_progress_at,
                "termination_kind": self._termination_kind,
                "lost_reason": self._lost_reason,
                "stale_events": self._stale_events,
                "stale_responses": self._stale_responses,
                "stale_callbacks": self._stale_callbacks,
                "pending_requests": len(self._pending),
            }

    # ── ciclo de vida ─────────────────────────────────────────────────
    def start(self) -> dict[str, Any]:
        """Spawn + bounded handshake. Raises ``OutputHostStartError``."""
        with self._lock:
            if self._state in (SupervisorState.READY, SupervisorState.BUSY):
                return dict(self._hello or {})
            if self._state is SupervisorState.STARTING:
                raise OutputHostStartError("host is already starting")
            if self._process is not None:
                raise OutputHostStartError("a previous host incarnation is live")
            self._state = SupervisorState.STARTING
            self._reader_stop.clear()
            self._decoder = FrameDecoder()
            self._hello = None
            self._lost_reason = None
            self._termination_kind = None
            self._started_at = time.monotonic()
            self._host_generation += 1
            generation = self._host_generation
        parent_sock, child_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        child_fd = child_sock.fileno()
        argv = self._command_factory(child_fd)
        try:
            process = subprocess.Popen(
                argv,
                pass_fds=(child_fd,),
                start_new_session=True,
                env=self._env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            parent_sock.close()
            child_sock.close()
            with self._lock:
                self._state = SupervisorState.FAILED
            raise OutputHostStartError(f"cannot spawn host: {exc}") from exc
        finally:
            child_sock.close()
        with self._lock:
            self._process = process
            self._socket = parent_sock
            self._active_generation = generation
            self._accepting_frames = True
        parent_sock.settimeout(0.2)
        reader = threading.Thread(
            target=self._reader_run,
            name=f"gst-host-reader-{generation}",
            daemon=True,
        )
        with self._lock:
            self._reader = reader
        reader.start()
        try:
            hello = self._command(
                HostOperation.HELLO,
                {},
                deadline_s=self._start_timeout_s,
                command_generation=0,
                expected_kinds=(MessageKind.HELLO.value,),
                during_start=True,
            )
        except OutputHostError as exc:
            detail = f"{exc.code}: {exc.detail}"
            self._terminate_process(reason=f"start_failed: {detail}", graceful=False)
            raise OutputHostStartError(detail) from exc
        with self._lock:
            self._hello = dict(hello)
            self._state = SupervisorState.READY
        return dict(hello)

    def ping(self, *, deadline_s: float | None = None) -> dict[str, Any]:
        return self._command(
            HostOperation.PING,
            {},
            deadline_s=self._command_timeout_s if deadline_s is None else deadline_s,
        )

    def submit(
        self,
        operation: HostOperation,
        payload: dict[str, Any] | None = None,
        *,
        deadline_s: float | None = None,
        command_generation: int = 0,
    ) -> dict[str, Any]:
        return self._command(
            operation,
            payload or {},
            deadline_s=self._command_timeout_s if deadline_s is None else deadline_s,
            command_generation=command_generation,
        )

    def shutdown(self, *, graceful: bool = True) -> str:
        """Bounded shutdown; returns the recorded termination kind.

        GRACEFUL is recorded only when the host actually acknowledged
        SHUTDOWN_COMPLETE; a host that dies first is EXITED_BEFORE.
        """
        with self._lock:
            process = self._process
            if process is None:
                return self._termination_kind or EXITED_BEFORE
            self._state = SupervisorState.STOPPING
        acknowledged = False
        if graceful and process.poll() is None:
            try:
                self._command(
                    HostOperation.SHUTDOWN,
                    {},
                    deadline_s=self._terminate_grace_s,
                    expected_kinds=(MessageKind.SHUTDOWN_COMPLETE.value,),
                    during_shutdown=True,
                )
                acknowledged = True
            except OutputHostError:
                acknowledged = False
        return self._terminate_process(
            reason="shutdown", graceful=False, acknowledged=acknowledged
        )

    def close(self) -> None:
        with contextlib.suppress(OutputHostError):
            self.shutdown()
        with self._lock:
            self._state = SupervisorState.STOPPED
            self._hello = None

    # ── internos de arranque/parada ───────────────────────────────────
    def _finish_termination(self, *, kind: str, reason: str) -> None:
        """Common cleanup after the host has exited (or was SIGKILLed)."""
        with self._lock:
            process = self._process
            parent_sock = self._socket
            self._accepting_frames = False
        if process is not None:
            with contextlib.suppress(Exception):
                process.wait(timeout=max(0.5, self._kill_grace_s))
        with contextlib.suppress(Exception):
            if parent_sock is not None:
                parent_sock.close()
        current = threading.current_thread()
        reader = self._reader
        if reader is not None and reader is not current and reader.is_alive():
            reader.join(timeout=1.0)
        with self._lock:
            self._process = None
            self._socket = None
            self._reader = None
            self._termination_kind = kind
            self._lost_reason = reason if kind != GRACEFUL else self._lost_reason
            for holder in self._pending.values():
                if holder.response is None and holder.error is None:
                    holder.error = OutputHostLostError(
                        f"host terminated ({kind}) during {holder.operation}"
                    )
                with holder.condition:
                    holder.condition.notify_all()
            self._pending.clear()
            if self._state is not SupervisorState.STOPPED:
                self._state = (
                    SupervisorState.STOPPED
                    if kind in (GRACEFUL, FORCED_TERM, FORCED_KILL)
                    and reason == "shutdown"
                    else SupervisorState.FAILED
                )

    def _terminate_process(
        self, *, reason: str, graceful: bool, acknowledged: bool = False
    ) -> str:
        """Canonical termination ladder. Never waits forever, never leaks."""
        with self._lock:
            process = self._process
            parent_sock = self._socket
            self._accepting_frames = False
        if process is None:
            with self._lock:
                kind = self._termination_kind or EXITED_BEFORE
                if self._state is SupervisorState.STARTING:
                    self._state = SupervisorState.FAILED
            return kind
        pid = process.pid
        kind: str
        if process.poll() is not None:
            kind = (
                GRACEFUL if (reason == "shutdown" and acknowledged) else EXITED_BEFORE
            )
        else:
            if graceful and parent_sock is not None:
                with contextlib.suppress(OutputHostError, OSError):
                    self._command(
                        HostOperation.SHUTDOWN,
                        {},
                        deadline_s=self._terminate_grace_s,
                        expected_kinds=(MessageKind.SHUTDOWN_COMPLETE.value,),
                        during_shutdown=True,
                    )
            if self._wait_pid_exit(process, self._terminate_grace_s):
                kind = GRACEFUL if acknowledged or graceful else EXITED_BEFORE
            else:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGTERM)
                if self._wait_pid_exit(process, self._term_grace_s):
                    kind = FORCED_TERM
                else:
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(pid, signal.SIGKILL)
                    if self._wait_pid_exit(process, self._kill_grace_s):
                        kind = FORCED_KILL
                    else:
                        kind = REAP_PENDING
        self._finish_termination(kind=kind, reason=reason)
        return kind

    @staticmethod
    def _wait_pid_exit(process: subprocess.Popen[bytes], timeout_s: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout_s)
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return True
            time.sleep(0.02)
        return process.poll() is not None

    # ── internos de comando ───────────────────────────────────────────
    def _command(
        self,
        operation: HostOperation,
        payload: dict[str, Any],
        *,
        deadline_s: float,
        command_generation: int = 0,
        expected_kinds: tuple[str, ...] | None = None,
        during_start: bool = False,
        during_shutdown: bool = False,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        with self._lock:
            if (
                not during_start
                and not during_shutdown
                and self._state
                not in (
                    SupervisorState.READY,
                    SupervisorState.BUSY,
                    SupervisorState.DEGRADED,
                )
            ):
                raise OutputHostLostError(
                    f"host is not available (state={self._state.value})"
                )
            generation = self._active_generation or 0
            self._last_request_id = request_id
            self._last_operation = str(operation)
            self._last_progress_at = time.monotonic()
            holder = _PendingRequest(
                request_id=request_id,
                operation=str(operation),
                expected_command_generation=command_generation,
            )
            self._pending[request_id] = holder
        message = make_message(
            MessageKind.COMMAND,
            host_generation=generation,
            command_generation=command_generation,
            request_id=request_id,
            operation=operation,
            payload=payload,
        )
        try:
            frame = encode_message(message)
        except HostProtocolError as exc:
            with self._lock:
                self._pending.pop(request_id, None)
            raise OutputHostProtocolError(exc.detail) from exc
        try:
            self._send(frame)
        except OSError as exc:
            lost = OutputHostLostError(f"host socket failed: {exc}")
            self._fail_pending(holder, lost)
            self._terminate_process(reason="socket_send_failed", graceful=False)
            raise OutputHostLostError(f"host socket failed: {exc}") from exc
        deadline = time.monotonic() + max(0.0, deadline_s)
        response = self._await(holder, deadline)
        if response is None:
            self._fail_pending(
                holder,
                OutputHostTimeoutError(
                    f"{operation} exceeded its parent-owned deadline "
                    f"({deadline_s:.3f}s)"
                ),
            )
            self._retire_wedged_host(operation)
            raise OutputHostTimeoutError(
                f"{operation} exceeded its parent-owned deadline ({deadline_s:.3f}s)"
            )
        kind = response["kind"]
        if expected_kinds is not None and kind not in expected_kinds:
            raise OutputHostProtocolError(
                f"{operation} expected {expected_kinds}, received {kind!r}"
            )
        if kind in (MessageKind.RESULT.value, MessageKind.ACK.value):
            return response.get("payload") or {}
        if kind == MessageKind.HELLO.value:
            return response.get("payload") or {}
        if kind == MessageKind.SHUTDOWN_COMPLETE.value:
            return response.get("payload") or {}
        code = ""
        detail = ""
        payload_out = response.get("payload") or {}
        if isinstance(payload_out, dict):
            code = str(payload_out.get("code") or "")
            detail = str(payload_out.get("detail") or "")
        raise OutputHostCommandError(
            code or "OUTPUT_HOST_COMMAND_FAILED",
            detail or f"{operation} rejected by host ({kind})",
            payload=payload_out if isinstance(payload_out, dict) else {},
        )

    def _await(self, holder: _PendingRequest, deadline: float) -> dict[str, Any] | None:
        with holder.condition:
            while holder.response is None and holder.error is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                # Drain owner-side frames (reverse callbacks) while waiting so
                # a child blocked in a callback can never deadlock the parent.
                drain = self._owner_drain
                if drain is not None:
                    with contextlib.suppress(Exception):
                        drain()
                holder.condition.wait(timeout=min(0.05, remaining))
            if holder.error is not None:
                raise holder.error
            return holder.response

    def _retire_wedged_host(self, operation: HostOperation) -> None:
        with self._lock:
            generation = self._host_generation
            pid = None if self._process is None else self._process.pid
        detail = f"host wedged on {operation} (generation {generation}, pid {pid})"
        self._notify_lost(generation, "OUTPUT_HOST_TIMEOUT", detail)
        self._terminate_process(reason=f"wedged_on_{operation}", graceful=False)

    def _fail_pending(self, holder: _PendingRequest, error: OutputHostError) -> None:
        with self._lock:
            self._pending.pop(holder.request_id, None)
        with holder.condition:
            holder.error = error
            holder.condition.notify_all()

    def _notify_lost(self, generation: int, code: str, detail: str) -> None:
        with self._lock:
            callback = self._on_lost
        if callback is None:
            return
        with contextlib.suppress(Exception):
            callback(generation, code, detail)

    # ── hilo lector ───────────────────────────────────────────────────
    def _reader_run(self) -> None:
        with self._lock:
            parent_sock = self._socket
        if parent_sock is None:
            return
        while not self._reader_stop.is_set():
            try:
                chunk = parent_sock.recv(65536)
            except TimeoutError:
                continue
            except OSError:
                break
            if not chunk:
                break
            try:
                frames = self._decoder.feed(chunk)
            except HostProtocolError as exc:
                self._handle_protocol_violation(exc)
                return
            for frame in frames:
                self._route_frame(frame)
        self._on_reader_closed()

    def _route_frame(self, frame: dict[str, Any]) -> None:
        with self._lock:
            accepting = self._accepting_frames
            generation = self._active_generation
            state = self._state
        if generation is not None and frame.get("host_generation") != generation:
            with self._lock:
                self._stale_events += 1
            return
        kind = frame["kind"]
        is_control = kind in (
            MessageKind.RESULT.value,
            MessageKind.REJECTED.value,
            MessageKind.FAULT.value,
            MessageKind.ACK.value,
            MessageKind.HELLO.value,
            MessageKind.SHUTDOWN_COMPLETE.value,
            MessageKind.CALLBACK.value,
        )
        # During STOPPING, in-flight command responses (including
        # SHUTDOWN_COMPLETE) and reverse callbacks must still be routed so a
        # closing child can complete its release handoff; events are moot.
        if not accepting or state in (SupervisorState.STOPPED, SupervisorState.FAILED):
            return
        if state is SupervisorState.STOPPING and not is_control:
            return
        if kind == MessageKind.EVENT.value:
            self._last_progress_at = time.monotonic()
            callback = self._on_event
            if callback is not None:
                with contextlib.suppress(Exception):
                    callback(frame)
            return
        if kind == MessageKind.CALLBACK.value:
            self._handle_callback(frame)
            return
        request_id = frame.get("request_id")
        if not isinstance(request_id, str):
            return
        with self._lock:
            holder = self._pending.get(request_id)
        if holder is None:
            return
        # Two-domain fence for RESPONSES as well: a response that does not
        # echo the command generation of its request can never complete it.
        if frame.get("command_generation") != holder.expected_command_generation:
            with self._lock:
                self._stale_responses += 1
            return
        with self._lock:
            self._pending.pop(request_id, None)
        with holder.condition:
            holder.response = frame
            holder.condition.notify_all()

    def _handle_callback(self, frame: dict[str, Any]) -> None:
        with self._lock:
            current_generation = self._host_generation
        if frame.get("host_generation") != current_generation:
            with self._lock:
                self._stale_callbacks += 1
            return
        handler = self._callback_handler
        ok = False
        payload: dict[str, Any] = {}
        if handler is not None:
            try:
                ok, payload = handler(frame)
            except Exception as exc:  # noqa: BLE001 - typed boundary reply
                ok = False
                payload = error_payload("OUTPUT_HOST_CALLBACK_FAILED", str(exc))
        else:
            payload = error_payload(
                "OUTPUT_HOST_CALLBACK_UNSUPPORTED",
                "no parent callback handler is installed",
            )
        kind = MessageKind.CALLBACK_RESULT if ok else MessageKind.CALLBACK_REJECTED
        reply = make_message(
            kind,
            host_generation=frame.get("host_generation", 0),
            command_generation=frame.get("command_generation", 0),
            request_id=frame.get("request_id"),
            payload=payload,
        )
        with contextlib.suppress(HostProtocolError, OSError):
            self._send(encode_message(reply))

    def _handle_protocol_violation(self, exc: HostProtocolError) -> None:
        with self._lock:
            generation = self._host_generation
        self._notify_lost(generation, "OUTPUT_HOST_PROTOCOL_ERROR", exc.detail)
        self._terminate_process(
            reason=f"protocol_violation: {exc.code}", graceful=False
        )

    def _on_reader_closed(self) -> None:
        with self._lock:
            state = self._state
            process = self._process
            generation = self._host_generation
        if state in (SupervisorState.STOPPING, SupervisorState.STOPPED):
            return
        if process is None:
            return
        code = process.poll()
        if code is None:
            # Socket vanished while the child is alive: protocol/lost fault.
            self._notify_lost(
                generation, "OUTPUT_HOST_LOST", "host channel closed unexpectedly"
            )
        else:
            self._notify_lost(
                generation, "OUTPUT_HOST_LOST", f"host exited with code {code}"
            )
        self._terminate_process(reason="reader_closed", graceful=False)

    def _send(self, frame: bytes) -> None:
        with self._send_lock:
            with self._lock:
                parent_sock = self._socket
            if parent_sock is None:
                raise OSError("host socket is not available")
            parent_sock.sendall(frame)

    # ── utilidades para tests/observabilidad ──────────────────────────
    def pid_alive(self) -> bool:
        with self._lock:
            process = self._process
        if process is None:
            return False
        return process.poll() is None

    def wait_for_hello(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._hello is not None:
                    return True
            time.sleep(0.01)
        with self._lock:
            return self._hello is not None

    def _fail_pending_all(self) -> None:  # pragma: no cover - defensive
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for holder in pending:
            with holder.condition:
                holder.error = OutputHostLostError("host is gone")
                holder.condition.notify_all()
