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
        self._native_dsd_active = False
        self._native_dsd_state = "NONE"
        self._native_dsd_expected: dict[str, Any] | None = None
        self._native_dsd_path: str | None = None
        self._native_eos_listeners: list[Callable[[str], None]] = []
        self._dop_active = False
        self._dsd_pcm_active = False
        self._dsd_pcm_expected: dict[str, Any] | None = None
        self._dsd_pcm_receipt: dict[str, Any] | None = None
        self._dsd_pcm_path: str | None = None
        self._dop_state = "NONE"
        self._dop_expected: dict[str, Any] | None = None
        self._dop_path: str | None = None
        self._dop_release_receipt: dict[str, Any] | None = None
        self._dop_eos_listeners: list[Callable[[str], None]] = []
        self._pcm_active = False
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
        self._host_lost_listeners: list[Callable[[str], None]] = []
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
        # Host shutdown FIRST: the child releases its Direct execution while
        # the parent executor still owns that exact identity, so the close
        # handoff is validated instead of being an unverifiable stale accept.
        kind = self._supervisor.shutdown()
        # A graceful child release already cleared the parent execution; a
        # lost host never released, so the parent invalidates truth here
        # (idempotent release).
        cleanup_error: Exception | None = None
        executor = self._direct_executor
        if executor is not None:
            try:
                executor.release("gstreamer_close")
            except Exception as exc:  # noqa: BLE001 - re-raised after invalidation
                cleanup_error = exc
        with self._lock:
            self._closed = True
            self._closing = False
            self._termination_kind = kind
            self._native_dsd_active = False
            self._native_dsd_state = "RELEASED"
            self._native_dsd_expected = None
            self._native_dsd_path = None
            self._dop_active = False
            self._dop_state = "RELEASED"
            self._dop_expected = None
            self._dop_path = None
            self._dop_release_receipt = None
            self._dsd_pcm_active = False
            self._dsd_pcm_expected = None
            self._dsd_pcm_receipt = None
            self._dsd_pcm_path = None
            self._pcm_active = False
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
        self._run_worker(self.play, on_done=on_done, on_failed=on_failed, name="play")

    def pause_async(self, *, on_done=None, on_failed=None) -> None:
        self._run_worker(self.pause, on_done=on_done, on_failed=on_failed, name="pause")

    def resume_async(self, *, on_done=None, on_failed=None) -> None:
        self._run_worker(
            self.resume, on_done=on_done, on_failed=on_failed, name="resume"
        )

    def stop_async(self, *, on_done=None, on_failed=None) -> None:
        self._run_worker(self.stop, on_done=on_done, on_failed=on_failed, name="stop")

    def seek_async(
        self,
        position_ms: int,
        *,
        on_done=None,
        on_failed=None,
    ) -> None:
        self._run_worker(
            lambda: self.seek(position_ms),
            on_done=on_done,
            on_failed=on_failed,
            name="seek",
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
            if self._dop_active:
                expected_path = self._dop_path
                if expected_path is None or Path(path).resolve() != Path(expected_path):
                    raise AudioTransportCommandError(
                        "DOP_LOAD_CONFLICT: a different DoP execution owns the output"
                    )
                self._commit_accepted(Path(path))
                return {"dop": True, "accepted": True}
            if self._dsd_pcm_active:
                expected_path = self._dsd_pcm_path
                if expected_path is None or Path(path).resolve() != Path(expected_path):
                    raise AudioTransportCommandError(
                        "DSD_PCM_LOAD_CONFLICT: a different DSD→PCM execution "
                        "owns the output"
                    )
                self._commit_accepted(Path(path))
                return {"dsd_pcm": True, "accepted": True}
            if self._native_dsd_active:
                expected_path = self._native_dsd_path
                if expected_path is None or Path(path).resolve() != Path(expected_path):
                    raise AudioTransportCommandError(
                        "NATIVE_DSD_LOAD_CONFLICT: a different Native DSD "
                        "execution owns the output"
                    )
                # The host pipeline is already prepared. Acceptance is the
                # canonical media boundary; it is not a PCM load.
                self._commit_accepted(Path(path))
                return {"native_dsd": True, "accepted": True}
            self._command_generation += 1
        try:
            result = self._submit(
                HostOperation.LOAD,
                {"path": str(path)},
                deadline_s=deadline_s,
            )
            with self._lock:
                self._pcm_active = True
            return result
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
        with self._lock:
            native = self._native_dsd_active
            dop = self._dop_active
        if dop:
            self.start_dop()
            return
        if native:
            self.start_native_dsd()
            return
        self._command(HostOperation.PLAY)

    def pause(self) -> None:
        with self._lock:
            native = self._native_dsd_active
            dop = self._dop_active
        if dop:
            self.pause_dop()
            return
        if native:
            self.pause_native_dsd()
            return
        self._command(HostOperation.PAUSE)

    def resume(self) -> None:
        with self._lock:
            native = self._native_dsd_active
            dop = self._dop_active
        if dop:
            self.resume_dop()
            return
        if native:
            self.resume_native_dsd()
            return
        self._command(HostOperation.RESUME)

    def stop(self) -> None:
        with self._lock:
            native = self._native_dsd_active
            dop = self._dop_active
            native_expected = dict(self._native_dsd_expected or {})
            dop_expected = dict(self._dop_expected or {})
            self._command_generation += 1
        if dop and dop_expected:
            self.stop_dop(dop_expected)
            return
        if native and native_expected:
            self.stop_native_dsd(native_expected)
            return
        self._command(HostOperation.STOP)
        with self._lock:
            self._pcm_active = False

    def seek(self, position_ms: int) -> None:
        with self._lock:
            native = self._native_dsd_active
            dop = self._dop_active
        if dop:
            raise AudioTransportCommandError(
                "DOP_SEEK_UNSUPPORTED: DoP seek is not demonstrated"
            )
        if native:
            raise AudioTransportCommandError(
                "NATIVE_DSD_SEEK_UNSUPPORTED: Native DSD seek is not demonstrated"
            )
        self._command(HostOperation.SEEK, {"position_ms": int(position_ms)})

    def set_volume(self, value: int) -> None:
        with self._lock:
            native = self._native_dsd_active
            dop = self._dop_active
        if dop:
            raise AudioTransportCommandError(
                "DOP_VOLUME_UNSUPPORTED: no software volume on the DoP carrier"
            )
        if native:
            raise AudioTransportCommandError(
                "NATIVE_DSD_VOLUME_UNSUPPORTED: no PCM volume on a Native DSD route"
            )
        self._command(HostOperation.SET_VOLUME, {"value": int(value)})

    def set_muted(self, muted: bool) -> None:
        with self._lock:
            native = self._native_dsd_active
        if native:
            raise AudioTransportCommandError(
                "NATIVE_DSD_MUTE_UNSUPPORTED: no PCM mute on a Native DSD route"
            )
        self._command(HostOperation.SET_MUTED, {"muted": bool(muted)})

    def position(self) -> int:
        with self._lock:
            if self._native_dsd_active:
                return 0
        payload = self._command(HostOperation.QUERY_POSITION)
        return int(payload.get("value") or 0)

    def duration(self) -> int:
        with self._lock:
            if self._native_dsd_active:
                return 0
        payload = self._command(HostOperation.QUERY_DURATION)
        return int(payload.get("value") or 0)

    def backend_state(self) -> str | None:
        with self._lock:
            return None if self._last_state is None else self._last_state.name.lower()

    def supervisor_generation(self) -> int:
        """Current host incarnation generation (parent-side authority)."""
        return int(self._supervisor.host_generation)

    def query_processing_capabilities(self) -> dict[str, Any]:
        """Child-native processing capability facts (primitive dict).

        Bounded by the parent-owned command deadline; a wedged or dead host
        surfaces as a typed transport failure, never as partial facts.
        """
        payload = self._submit(
            HostOperation.QUERY_PROCESSING_CAPABILITIES,
            {},
            deadline_s=self._command_deadline_s,
        )
        facts = payload.get("facts")
        if not isinstance(facts, dict):
            raise AudioTransportCommandError(
                "processing capability query returned malformed facts"
            )
        return facts

    def prepare_processing_candidate(
        self, plan: dict[str, Any], *, processing_generation: int = 0
    ) -> dict[str, Any]:
        """Build+preroll+inspect a REAL native candidate in the child.

        Returns the child's primitive readback; the parent decides. The
        processing generation is stored in the child so the COMMIT can
        revalidate it before any destructive mutation.
        """
        payload = self._submit(
            HostOperation.PREPARE_PROCESSING_CANDIDATE,
            {
                "plan": plan,
                "processing_generation": int(processing_generation),
                "host_generation": self._supervisor.host_generation,
            },
            deadline_s=max(self._command_deadline_s, 12.0),
        )
        observed = payload.get("observed")
        if not isinstance(observed, dict):
            raise AudioTransportCommandError(
                "processing candidate returned a malformed readback"
            )
        return observed

    def commit_processing_candidate(
        self,
        *,
        plan_id: str,
        processing_generation: int,
        pipeline_generation: int,
        candidate_id: str = "",
    ) -> dict[str, Any]:
        """Authorize the destructive install; returns the child's receipt."""
        payload = self._submit(
            HostOperation.COMMIT_PROCESSING_CANDIDATE,
            {
                "plan_id": str(plan_id),
                "processing_generation": int(processing_generation),
                "pipeline_generation": int(pipeline_generation),
                "candidate_id": str(candidate_id or ""),
                "host_generation": self._supervisor.host_generation,
            },
            deadline_s=max(self._command_deadline_s, 12.0),
        )
        receipt = payload.get("receipt")
        if not isinstance(receipt, dict):
            raise AudioTransportCommandError(
                "processing commit returned a malformed receipt"
            )
        return receipt

    def capture_processing_output(
        self,
        seconds: float,
        probe_hz: list[float] | None = None,
        *,
        passive: bool = False,
    ) -> dict[str, Any]:
        """DIAGNOSTIC/TEST: child-local signal metrics of the installed filter."""
        request: dict[str, Any] = {
            "seconds": float(seconds),
            "passive": bool(passive),
        }
        if probe_hz:
            request["probe_hz"] = [float(hz) for hz in probe_hz]
        payload = self._submit(
            HostOperation.CAPTURE_PROCESSING_OUTPUT,
            request,
            deadline_s=max(self._command_deadline_s, float(seconds) + 8.0),
        )
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict):
            raise AudioTransportCommandError(
                "processing capture returned malformed metrics"
            )
        return metrics

    def bypass_processing(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.BYPASS_PROCESSING,
            {},
            deadline_s=max(self._command_deadline_s, 12.0),
        )
        if not payload.get("removed"):
            raise AudioTransportCommandError(
                "DSP_BYPASS_UNPROVEN", "no proven filter removal"
            )
        return payload

    # Transport-adapter aliases consumed by AudioProcessingService.
    def prepare_candidate(
        self, plan: dict[str, Any], *, processing_generation: int = 0
    ) -> dict[str, Any]:
        return self.prepare_processing_candidate(
            plan, processing_generation=processing_generation
        )

    def commit_candidate(
        self,
        *,
        plan_id: str,
        processing_generation: int,
        pipeline_generation: int,
        candidate_id: str = "",
    ) -> dict[str, Any]:
        return self.commit_processing_candidate(
            plan_id=plan_id,
            processing_generation=processing_generation,
            pipeline_generation=pipeline_generation,
            candidate_id=candidate_id,
        )

    def abort_candidate(self) -> bool:
        return self.abort_processing_candidate()

    def abort_processing_candidate(self) -> bool:
        payload = self._submit(
            HostOperation.ABORT_PROCESSING_CANDIDATE,
            {},
            deadline_s=self._command_deadline_s,
        )
        return bool(payload.get("aborted", False))

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

    def stage_managed_execution(self, recipe: dict[str, Any]) -> None:
        """AP2-F06: stage ONE strict managed sink for the selected DAC."""
        self._submit(
            HostOperation.STAGE_MANAGED,
            {"recipe": dict(recipe)},
            deadline_s=self._command_deadline_s,
        )

    def stop_managed_execution(self, expected: dict[str, Any]) -> dict[str, Any]:
        """Stop ONLY the managed execution whose identity matches ``expected``."""
        payload = self._submit(
            HostOperation.STOP_MANAGED,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "stop_managed result is not an object",
            )
        return result

    def query_managed_identity(self) -> dict[str, Any]:
        """Primitive identity of the current managed load (never Gst objects)."""
        payload = self._submit(
            HostOperation.QUERY_MANAGED_IDENTITY,
            {},
            deadline_s=self._command_deadline_s,
        )
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "managed identity payload is not an object",
            )
        return identity

    # ── Native DSD (AP2-F08) ─────────────────────────────────────────
    def add_native_eos_listener(self, callback: Callable[[str], None]) -> None:
        if callback not in self._native_eos_listeners:
            self._native_eos_listeners.append(callback)

    def add_dop_eos_listener(self, callback: Callable[[str], None]) -> None:
        if callback not in self._dop_eos_listeners:
            self._dop_eos_listeners.append(callback)

    @property
    def native_dsd_active(self) -> bool:
        with self._lock:
            return self._native_dsd_active

    def prepare_native_dsd(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build/preroll the one dedicated Native DSD pipeline in the child."""
        with self._lock:
            if self._pcm_active:
                raise AudioTransportCommandError(
                    "NATIVE_DSD_PCM_CONFLICT: release the PCM output before "
                    "preparing Native DSD"
                )
        identity = self._submit(
            HostOperation.PREPARE_NATIVE_DSD,
            dict(payload),
            deadline_s=self._load_deadline_s,
        )
        with self._lock:
            self._native_dsd_active = True
            self._native_dsd_state = "PREPARED"
            self._native_dsd_expected = {
                "plan_id": str(identity.get("plan_id") or ""),
                "execution_id": str(identity.get("execution_id") or ""),
                "stable_device_id": str(identity.get("stable_device_id") or ""),
                "device": str(identity.get("device") or ""),
                "binding_generation": int(identity.get("binding_generation") or 0),
                "host_generation": int(self._supervisor.host_generation),
            }
            self._native_dsd_path = str(Path(str(payload.get("path") or "")).resolve())
        return identity

    def commit_native_dsd(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_native_expected(expected)
        result = self._submit(
            HostOperation.COMMIT_NATIVE_DSD,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("committed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD commit was not explicitly confirmed",
            )
        with self._lock:
            self._native_dsd_state = "COMMITTED"
        return result

    def abort_native_dsd(
        self, expected: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self._require_native_expected(expected)
        result = self._submit(
            HostOperation.ABORT_NATIVE_DSD,
            {"expected": dict(expected or {})},
            deadline_s=self._command_deadline_s,
        )
        if result.get("aborted") is not True or result.get("stale") is not False:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD abort was not explicitly confirmed",
            )
        with self._lock:
            self._native_dsd_active = False
            self._native_dsd_state = "RELEASED"
            self._native_dsd_expected = None
            self._native_dsd_path = None
            self._dop_active = False
            self._dop_state = "RELEASED"
            self._dop_expected = None
            self._dop_path = None
        self._enqueue(lambda: self._commit_state(PlaybackStatus.STOPPED))
        return result

    def start_native_dsd(self) -> dict[str, Any]:
        with self._lock:
            if not self._native_dsd_active:
                raise AudioTransportCommandError(
                    "NATIVE_DSD_NOT_PREPARED: no Native DSD execution is active"
                )
        result = self._submit(
            HostOperation.START_NATIVE_DSD,
            {},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD PLAYING was not confirmed",
            )
        with self._lock:
            self._native_dsd_state = "RUNNING"
        self._enqueue(lambda: self._commit_state(PlaybackStatus.PLAYING))
        return result

    def pause_native_dsd(self) -> dict[str, Any]:
        result = self._submit(
            HostOperation.PAUSE_NATIVE_DSD,
            {},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD PAUSED was not confirmed",
            )
        with self._lock:
            self._native_dsd_state = "PAUSED"
        self._enqueue(lambda: self._commit_state(PlaybackStatus.PAUSED))
        return result

    def resume_native_dsd(self) -> dict[str, Any]:
        result = self._submit(
            HostOperation.RESUME_NATIVE_DSD,
            {},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD PLAYING resume was not confirmed",
            )
        with self._lock:
            self._native_dsd_state = "RUNNING"
        self._enqueue(lambda: self._commit_state(PlaybackStatus.PLAYING))
        return result

    def stop_native_dsd(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_native_expected(expected)
        result = self._submit(
            HostOperation.STOP_NATIVE_DSD,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("stopped") is not True or result.get("stale") is not False:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD stop was not explicitly confirmed",
            )
        with self._lock:
            self._native_dsd_active = False
            self._native_dsd_state = "RELEASED"
            self._native_dsd_expected = None
            self._native_dsd_path = None
            self._dop_active = False
            self._dop_state = "RELEASED"
            self._dop_expected = None
            self._dop_path = None
        self._enqueue(lambda: self._commit_state(PlaybackStatus.STOPPED))
        return result

    @property
    def dsd_pcm_active(self) -> bool:
        with self._lock:
            return self._dsd_pcm_active

    def prepare_dsd_pcm(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._dsd_pcm_active:
                raise AudioTransportCommandError(
                    "DSD_PCM_SUPERSESSION_UNAUTHORIZED: release the active execution"
                )
            if self._dop_active or self._native_dsd_active:
                raise AudioTransportCommandError(
                    "DSD_PCM_ENGINE_CONFLICT: release Native/DoP first"
                )
            if self._pcm_active:
                raise AudioTransportCommandError(
                    "DSD_PCM_PCM_CONFLICT: release the PCM output first"
                )
        actual = dict(payload)
        actual["host_generation"] = int(self._supervisor.host_generation)
        identity = self._submit(
            HostOperation.PREPARE_DSD_PCM,
            actual,
            deadline_s=self._load_deadline_s,
        )
        with self._lock:
            self._dsd_pcm_active = True
            self._dsd_pcm_path = str(Path(str(payload.get("path") or "")).resolve())
            self._dsd_pcm_expected = {
                "plan_id": str(identity.get("plan_id") or ""),
                "execution_id": str(identity.get("execution_id") or ""),
                "stable_device_id": str(identity.get("stable_device_id") or ""),
                "device": str(identity.get("device") or ""),
                "binding_generation": int(identity.get("binding_generation") or 0),
                "host_generation": int(self._supervisor.host_generation),
            }
            self._dsd_pcm_receipt = None
        return identity

    def commit_dsd_pcm(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_dsd_pcm_expected(expected)
        result = self._submit(
            HostOperation.COMMIT_DSD_PCM,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("committed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DSD→PCM commit was not confirmed"
            )
        return result

    def start_dsd_pcm(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is None:
            expected = dict(self._dsd_pcm_expected or {})
        self._require_dsd_pcm_expected(expected)
        result = self._submit(
            HostOperation.START_DSD_PCM,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DSD→PCM PLAYING was not confirmed"
            )
        self._enqueue(lambda: self._commit_state(PlaybackStatus.PLAYING))
        return result

    def pause_dsd_pcm(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is None:
            expected = dict(self._dsd_pcm_expected or {})
        self._require_dsd_pcm_expected(expected)
        result = self._submit(
            HostOperation.PAUSE_DSD_PCM,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DSD→PCM PAUSED was not confirmed"
            )
        self._enqueue(lambda: self._commit_state(PlaybackStatus.PAUSED))
        return result

    def resume_dsd_pcm(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is None:
            expected = dict(self._dsd_pcm_expected or {})
        self._require_dsd_pcm_expected(expected)
        result = self._submit(
            HostOperation.RESUME_DSD_PCM,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DSD→PCM PLAYING was not confirmed"
            )
        self._enqueue(lambda: self._commit_state(PlaybackStatus.PLAYING))
        return result

    def _release_dsd_pcm(
        self, operation: HostOperation, expected: dict[str, Any], key: str
    ) -> dict[str, Any]:
        with self._lock:
            already = not self._dsd_pcm_active
            receipt = dict(self._dsd_pcm_receipt or {})
        if already:
            if not self._release_receipt_matches(receipt, expected):
                raise AudioTransportCommandError(
                    "DSD_PCM_RELEASE_UNCONFIRMED: no proven release receipt"
                )
            return {
                key: True,
                "already": True,
                "stale": False,
                "execution_id": str(expected.get("execution_id") or ""),
                "release": receipt,
            }
        self._require_dsd_pcm_expected(expected)
        result = self._submit(
            operation, {"expected": dict(expected)}, deadline_s=self._command_deadline_s
        )
        if result.get(key) is not True or result.get("stale") is not False:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", f"DSD→PCM {key} was not confirmed"
            )
        release = result.get("release")
        if not self._release_receipt_matches(release, expected):
            raise OutputHostCommandError(
                "DSD_PCM_RELEASE_UNCONFIRMED", "release receipt identity mismatch"
            )
        with self._lock:
            self._dsd_pcm_active = False
            self._dsd_pcm_expected = None
            self._dsd_pcm_receipt = dict(release)
            self._dsd_pcm_path = None
        self._enqueue(lambda: self._commit_state(PlaybackStatus.STOPPED))
        return {
            **result,
            "execution_id": str(expected.get("execution_id") or ""),
            "release": release,
        }

    def stop_dsd_pcm(self, expected: dict[str, Any]) -> dict[str, Any]:
        return self._release_dsd_pcm(HostOperation.STOP_DSD_PCM, expected, "stopped")

    def abort_dsd_pcm(self, expected: dict[str, Any]) -> dict[str, Any]:
        return self._release_dsd_pcm(HostOperation.ABORT_DSD_PCM, expected, "aborted")

    def query_dsd_pcm_identity(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.QUERY_DSD_PCM_IDENTITY,
            {},
            deadline_s=self._command_deadline_s,
        )
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DSD→PCM identity is not an object"
            )
        return identity

    def query_dsd_pcm_evidence(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.QUERY_DSD_PCM_EVIDENCE,
            {},
            deadline_s=self._command_deadline_s,
        )
        evidence = payload.get("evidence")
        if not isinstance(evidence, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DSD→PCM evidence is not an object"
            )
        return evidence

    def _require_dsd_pcm_expected(self, expected: dict[str, Any] | None) -> None:
        if not isinstance(expected, dict) or not expected:
            raise AudioTransportCommandError(
                "DSD_PCM_IDENTITY_REQUIRED: execution identity required"
            )
        with self._lock:
            current = dict(self._dsd_pcm_expected or {})
        if not current:
            raise AudioTransportCommandError(
                "DSD_PCM_NOT_PREPARED: no DSD→PCM execution"
            )
        for field in self._DOP_RELEASE_FIELDS:
            if str(expected.get(field)) != str(current.get(field)):
                raise AudioTransportCommandError(
                    f"DSD_PCM_IDENTITY_MISMATCH: {field} does not match"
                )

    @property
    def dop_active(self) -> bool:
        with self._lock:
            return self._dop_active

    def prepare_dop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build/preroll the Gate A DoP pipeline in the supervised child."""
        with self._lock:
            if self._dop_active:
                raise AudioTransportCommandError(
                    "DOP_SUPERSESSION_UNAUTHORIZED: release the active "
                    "DoP execution first"
                )
            if self._native_dsd_active:
                raise AudioTransportCommandError(
                    "DOP_NATIVE_DSD_CONFLICT: release Native DSD before DoP"
                )
            if self._pcm_active:
                raise AudioTransportCommandError(
                    "DOP_PCM_CONFLICT: release the PCM output before DoP"
                )
        actual = dict(payload)
        actual["host_generation"] = int(self._supervisor.host_generation)
        identity = self._submit(
            HostOperation.PREPARE_DOP,
            actual,
            deadline_s=self._load_deadline_s,
        )
        with self._lock:
            self._dop_active = True
            self._dop_state = "PREPARED"
            self._dop_expected = {
                "plan_id": str(identity.get("plan_id") or ""),
                "execution_id": str(identity.get("execution_id") or ""),
                "stable_device_id": str(identity.get("stable_device_id") or ""),
                "device": str(identity.get("device") or ""),
                "binding_generation": int(identity.get("binding_generation") or 0),
                "host_generation": int(self._supervisor.host_generation),
            }
            self._dop_path = str(Path(str(payload.get("path") or "")).resolve())
            self._dop_release_receipt = None
        return identity

    def commit_dop(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_dop_expected(expected)
        result = self._submit(
            HostOperation.COMMIT_DOP,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("committed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP commit was not confirmed"
            )
        with self._lock:
            self._dop_state = "COMMITTED"
        return result

    def abort_dop(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        # A normal stop may already have released the route. Idempotence is
        # allowed only with a stored release receipt for THIS exact execution
        # on the current host generation. A caller-supplied execution id is
        # never evidence that the host released it.
        with self._lock:
            already_released = not self._dop_active
        if already_released:
            self._require_dop_release_expected(expected)
            receipt = dict(self._dop_release_receipt or {})
            return {
                "aborted": True,
                "already": True,
                "stale": False,
                "execution_id": str(expected.get("execution_id") or ""),
                "release": receipt,
            }
        self._require_dop_expected(expected)
        result = self._submit(
            HostOperation.ABORT_DOP,
            {"expected": dict(expected or {})},
            deadline_s=self._command_deadline_s,
        )
        if result.get("aborted") is not True or result.get("stale") is not False:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP abort was not confirmed"
            )
        receipt = self._require_confirmed_release(result, expected)
        with self._lock:
            self._dop_active = False
            self._dop_state = "RELEASED"
            self._dop_expected = None
            self._dop_path = None
            self._dop_release_receipt = dict(receipt)
        self._enqueue(lambda: self._commit_state(PlaybackStatus.STOPPED))
        return {
            **result,
            "execution_id": str(expected.get("execution_id") or ""),
            "release": receipt,
        }

    def start_dop(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            if not self._dop_active:
                raise AudioTransportCommandError(
                    "DOP_NOT_PREPARED: no DoP execution is active"
                )
            if expected is None:
                expected = dict(self._dop_expected or {})
        self._require_dop_expected(expected)
        result = self._submit(
            HostOperation.START_DOP,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP PLAYING was not confirmed"
            )
        with self._lock:
            self._dop_state = "RUNNING"
            command_generation = self._command_generation
        execution_id = str(expected.get("execution_id") or "")
        self._enqueue(
            lambda: self._commit_dop_state_if_current(
                execution_id, PlaybackStatus.PLAYING, command_generation
            )
        )
        return result

    def pause_dop(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is None:
            expected = dict(self._dop_expected or {})
        self._require_dop_expected(expected)
        result = self._submit(
            HostOperation.PAUSE_DOP,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP PAUSED was not confirmed"
            )
        with self._lock:
            self._dop_state = "PAUSED"
            command_generation = self._command_generation
        execution_id = str(expected.get("execution_id") or "")
        self._enqueue(
            lambda: self._commit_dop_state_if_current(
                execution_id, PlaybackStatus.PAUSED, command_generation
            )
        )
        return result

    def resume_dop(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is None:
            expected = dict(self._dop_expected or {})
        self._require_dop_expected(expected)
        result = self._submit(
            HostOperation.RESUME_DOP,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("confirmed") is not True:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP PLAYING was not confirmed"
            )
        with self._lock:
            self._dop_state = "RUNNING"
            command_generation = self._command_generation
        execution_id = str(expected.get("execution_id") or "")
        self._enqueue(
            lambda: self._commit_dop_state_if_current(
                execution_id, PlaybackStatus.PLAYING, command_generation
            )
        )
        return result

    def stop_dop(self, expected: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            already_released = not self._dop_active
        if already_released:
            self._require_dop_release_expected(expected)
            receipt = dict(self._dop_release_receipt or {})
            return {
                "stopped": True,
                "already": True,
                "stale": False,
                "execution_id": str(expected.get("execution_id") or ""),
                "release": receipt,
            }
        self._require_dop_expected(expected)
        result = self._submit(
            HostOperation.STOP_DOP,
            {"expected": dict(expected)},
            deadline_s=self._command_deadline_s,
        )
        if result.get("stopped") is not True or result.get("stale") is not False:
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP stop was not confirmed"
            )
        receipt = self._require_confirmed_release(result, expected)
        with self._lock:
            self._dop_active = False
            self._dop_state = "RELEASED"
            self._dop_expected = None
            self._dop_path = None
            self._dop_release_receipt = dict(receipt)
        self._enqueue(lambda: self._commit_state(PlaybackStatus.STOPPED))
        return {
            **result,
            "execution_id": str(expected.get("execution_id") or ""),
            "release": receipt,
        }

    def query_dop_identity(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.QUERY_DOP_IDENTITY, {}, deadline_s=self._command_deadline_s
        )
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP identity payload is not an object"
            )
        return identity

    def query_dop_evidence(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.QUERY_DOP_EVIDENCE, {}, deadline_s=self._command_deadline_s
        )
        evidence = payload.get("evidence")
        if not isinstance(evidence, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT", "DoP evidence payload is not an object"
            )
        return evidence

    _DOP_RELEASE_FIELDS = (
        "plan_id",
        "execution_id",
        "stable_device_id",
        "device",
        "binding_generation",
        "host_generation",
    )

    def _release_receipt_matches(
        self,
        receipt: object,
        expected: dict[str, Any],
        *,
        require_current_host: bool = True,
    ) -> bool:
        if not isinstance(receipt, dict):
            return False
        if receipt.get("confirmed") is not True:
            return False
        if receipt.get("terminal_state") != "RELEASED":
            return False
        if receipt.get("provenance") != "SUPERVISED_HOST":
            return False
        for field in self._DOP_RELEASE_FIELDS:
            wanted = str(expected.get(field) or "")
            observed = str(receipt.get(field) or "")
            if not wanted or observed != wanted:
                return False
        current_generation = int(self._supervisor.host_generation)
        return not (
            require_current_host
            and int(receipt.get("host_generation") or 0) != current_generation
        )

    def _require_dop_release_expected(self, expected: dict[str, Any] | None) -> None:
        if not isinstance(expected, dict) or not expected:
            raise AudioTransportCommandError(
                "DOP_HOST_IDENTITY_REQUIRED: release identity required"
            )
        if not self._release_receipt_matches(self._dop_release_receipt, expected):
            raise AudioTransportCommandError(
                "DOP_RELEASE_UNCONFIRMED: no proven release receipt for this exact "
                "execution on the current host generation"
            )

    def _require_confirmed_release(
        self, result: dict[str, Any], expected: dict[str, Any]
    ) -> dict[str, Any]:
        receipt = result.get("release")
        if not self._release_receipt_matches(receipt, expected):
            raise OutputHostCommandError(
                "DOP_RELEASE_UNCONFIRMED",
                "host result did not carry an exact proved release receipt",
            )
        assert isinstance(receipt, dict)
        return dict(receipt)

    def _require_dop_expected(self, expected: dict[str, Any] | None) -> None:
        if not isinstance(expected, dict) or not expected:
            raise AudioTransportCommandError(
                "DOP_HOST_IDENTITY_REQUIRED: destructive DoP operation needs identity"
            )
        with self._lock:
            current = dict(self._dop_expected or {})
        for field in (
            "plan_id",
            "execution_id",
            "stable_device_id",
            "device",
            "binding_generation",
            "host_generation",
        ):
            value = expected.get(field)
            if value is None or value == "" or str(value) != str(current.get(field)):
                raise AudioTransportCommandError(
                    f"DOP_HOST_IDENTITY_MISMATCH: {field} does not match"
                )

    def query_native_dsd_identity(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.QUERY_NATIVE_DSD_IDENTITY,
            {},
            deadline_s=self._command_deadline_s,
        )
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD identity payload is not an object",
            )
        return identity

    def query_native_dsd_evidence(self) -> dict[str, Any]:
        payload = self._submit(
            HostOperation.QUERY_NATIVE_DSD_EVIDENCE,
            {},
            deadline_s=self._command_deadline_s,
        )
        evidence = payload.get("evidence")
        if not isinstance(evidence, dict):
            raise OutputHostCommandError(
                "OUTPUT_HOST_INVALID_RESULT",
                "native DSD evidence payload is not an object",
            )
        return evidence

    def _require_native_expected(self, expected: dict[str, Any] | None) -> None:
        if not isinstance(expected, dict) or not expected:
            raise AudioTransportCommandError(
                "NATIVE_DSD_IDENTITY_REQUIRED: destructive operations require "
                "the canonical execution identity"
            )
        local = self._native_dsd_expected
        if local is None:
            raise AudioTransportCommandError(
                "NATIVE_DSD_IDENTITY_STALE: no owning Native DSD execution"
            )
        for field in (
            "plan_id",
            "execution_id",
            "stable_device_id",
            "device",
            "binding_generation",
        ):
            value = expected.get(field)
            if value is None or value == "":
                raise AudioTransportCommandError(
                    f"NATIVE_DSD_IDENTITY_REQUIRED: missing {field}"
                )
            if str(value) != str(local.get(field)):
                raise AudioTransportCommandError(
                    f"NATIVE_DSD_IDENTITY_STALE: {field} does not belong to "
                    "the current execution"
                )
        if local.get("host_generation") != self._supervisor.host_generation:
            raise AudioTransportCommandError(
                "NATIVE_DSD_IDENTITY_STALE: host incarnation changed"
            )

    def discard_direct_load(self, handle: object, *, executor: object) -> bool:
        self._require_direct_executor(executor)
        with self._lock:
            closing = self._closing
        if closing:
            # During close the host owns its teardown: the child session
            # releases its own staged state, and a nested discard command
            # would only race the shutdown. The parent truth is cleared by
            # the release path.
            return False
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
    def _is_allowed_close_handoff(self, frame: dict[str, Any]) -> bool:
        """Minimal close-time callback allowlist with MANDATORY identity.

        The stale-generation exception exists for exactly one handoff: the
        terminal release of a CURRENT Direct execution while this port is
        closing. It is only allowed when ALL hold:

          * this port is closing,
          * callback == release,
          * the frame carries the current host generation,
          * a Direct executor is bound and still owns an execution handle,
          * the payload carries a well-formed handle equal to that handle.

        Anything else — including a release without a handle, a Shared-only
        composition, or a mismatched/old/malformed handle — keeps the normal
        generation firewall and is rejected as stale.
        """
        if not self._closing:
            return False
        payload = frame.get("payload") or {}
        if payload.get("callback") != CB_RELEASE:
            return False
        if frame.get("host_generation") != self._supervisor.host_generation:
            return False
        executor = self._direct_executor
        if executor is None:
            # Shared-only composition: no Direct execution exists, so there is
            # nothing to finalize; never bypass the generation firewall.
            return False
        current = getattr(executor, "handle", None)
        if current is None:
            return False
        if "handle" not in payload:
            return False
        try:
            requested = handle_from_wire(payload.get("handle"))
        except Exception:  # noqa: BLE001 - malformed identity never passes
            return False
        return requested == current

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
        # The ONLY documented exception is the terminal release handoff
        # during close, gated by an explicit minimal predicate — never a
        # blanket "closing accepts anything".
        with self._lock:
            generation = frame.get("command_generation")
        stale_generation = generation != self._command_generation
        if stale_generation and not self._is_allowed_close_handoff(frame):
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
            closed = self._closed
            native_expected = dict(self._native_dsd_expected or {})
        dop_eos = kind == HostEvent.EOS.value and payload.get("dop") is True
        if dop_eos:
            with self._lock:
                dop_expected = dict(self._dop_expected or {})
                dop_active = bool(self._dop_active and self._dop_expected)
            execution_id = payload.get("execution_id")
            plan_id = payload.get("plan_id")
            host_generation = payload.get("host_generation")
            if (
                not closed
                and dop_active
                and isinstance(execution_id, str)
                and execution_id
                and isinstance(plan_id, str)
                and plan_id
                and isinstance(host_generation, int)
                and not isinstance(host_generation, bool)
                and execution_id == dop_expected.get("execution_id")
                and plan_id == dop_expected.get("plan_id")
                and host_generation == int(dop_expected.get("host_generation", -1))
                and host_generation == int(self._supervisor.host_generation)
            ):
                self._enqueue(
                    lambda: self._commit_dop_eos(execution_id, plan_id, host_generation)
                )
            else:
                with self._lock:
                    self._stale_events += 1
            return
        with self._lock:
            dop_owns_output = bool(self._dop_active and self._dop_expected)
        if kind == HostEvent.EOS.value and dop_owns_output:
            # DoP owns the transport: an identity-less/ambiguous EOS must never
            # fall through to the generic PCM end-of-media path.
            with self._lock:
                self._stale_events += 1
            return
        native_eos = kind == HostEvent.EOS.value and bool(
            payload.get("execution_id") or payload.get("plan_id")
        )
        with self._lock:
            native_owns_output = bool(
                self._native_dsd_active and self._native_dsd_expected
            )
        if kind == HostEvent.EOS.value and native_owns_output and not native_eos:
            # A Native execution must never be finalized by an identity-less
            # EOS through the PCM path.
            with self._lock:
                self._stale_events += 1
            return
        if native_eos:
            if (
                not closed
                and native_expected
                and payload.get("execution_id") == native_expected.get("execution_id")
                and int(
                    self._supervisor.host_generation
                    if payload.get("host_generation") is None
                    else payload["host_generation"]
                )
                == int(native_expected.get("host_generation", 0))
            ):
                # Capture the identity NOW; the owner commit revalidates it.
                # A later prepare B must never receive A's EOS.
                execution_id = str(payload.get("execution_id"))
                plan_id = str(payload.get("plan_id") or "")
                self._enqueue(lambda: self._commit_native_eos(execution_id, plan_id))
                return
            # An EOS carrying Native identity NEVER falls through to the PCM
            # end-of-media handler, even when stale/malformed.
            with self._lock:
                self._stale_events += 1
            return
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
            self._dop_release_receipt = None
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
        for listener in list(self._host_lost_listeners):
            with contextlib.suppress(Exception):
                listener(reason)
        self._relay_runtime_failure(reason)

    # ── commits owner ─────────────────────────────────────────────────
    def _commit_dop_state_if_current(
        self, execution_id: str, status: PlaybackStatus, command_generation: int
    ) -> None:
        """Publish a transport state only while its exact DoP command owns output.

        A state update queued by START/PAUSE/RESUME can still be pending when a
        later stop/abort releases the execution. The owner queue must not
        replay that stale PLAYING/PAUSED observation against the next
        execution (or after device-loss convergence).
        """
        with self._lock:
            expected = dict(self._dop_expected or {})
            current = bool(
                self._dop_active
                and execution_id
                and expected.get("execution_id") == execution_id
                and self._command_generation == command_generation
            )
        if not current:
            return
        self._commit_state(status)

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

    def _commit_native_eos(self, execution_id: str, plan_id: str) -> None:
        with self._lock:
            expected = dict(self._native_dsd_expected or {})
            if (
                not expected
                or str(expected.get("execution_id")) != execution_id
                or (plan_id and str(expected.get("plan_id")) != plan_id)
                or int(expected.get("host_generation", -1))
                != int(self._supervisor.host_generation)
            ):
                self._stale_events += 1
                return
            if self._native_dsd_state == "EOS":
                return
            self._native_dsd_state = "EOS"
            listeners = list(self._native_eos_listeners)
        for listener in listeners:
            with contextlib.suppress(Exception):
                listener(execution_id)
        self._commit_eos()

    def _commit_dop_eos(
        self, execution_id: str, plan_id: str, host_generation: int
    ) -> None:
        """Owner-thread DoP EOS commit with the captured identity revalidated."""
        with self._lock:
            expected = dict(self._dop_expected or {})
            if (
                not self._dop_active
                or not expected
                or str(expected.get("execution_id")) != execution_id
                or str(expected.get("plan_id")) != plan_id
                or int(expected.get("host_generation", -1)) != host_generation
                or int(self._supervisor.host_generation) != host_generation
            ):
                self._stale_events += 1
                return
            if self._dop_state == "EOS":
                return
            self._dop_state = "EOS"
            listeners = list(self._dop_eos_listeners)
        for listener in listeners:
            with contextlib.suppress(Exception):
                listener(execution_id)
        self._commit_eos()

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

    def add_host_lost_listener(self, callback: Callable[[str], None]) -> None:
        """Additive fan-out for host-loss events (DSP truth invalidation)."""
        with self._lock:
            self._host_lost_listeners.append(callback)

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
