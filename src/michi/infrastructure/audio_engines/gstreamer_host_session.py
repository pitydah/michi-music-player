"""Child-side engine session for the GStreamer output host.

Runs INSIDE the host process and drives one AudioPort-like engine
(production: ``GStreamerAudioPort``). It executes typed commands and
converts the engine's public callbacks into host protocol events.

It NEVER owns semantic authority: no playback state, no output session,
no Direct receipts, no Signal Truth classification. It reports primitive
facts and state transitions; the parent decides what they mean.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from michi.application.ports import AudioLoadError
from michi.infrastructure.audio_engines.gstreamer_host_direct import (
    HostDirectCoordinator,
    handle_from_wire,
    preparation_from_wire,
)
from michi.infrastructure.audio_engines.gstreamer_host_dop import (
    DopHostError,
    DopHostRuntime,
)
from michi.infrastructure.audio_engines.gstreamer_host_dsd_pcm import (
    DsdPcmHostError,
    DsdPcmHostRuntime,
)
from michi.infrastructure.audio_engines.gstreamer_host_native_dsd import (
    NativeDsdHostError,
    NativeDsdHostRuntime,
)
from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    HostEvent,
    HostOperation,
    HostProtocolError,
)

EmitEvent = Callable[[HostEvent, dict[str, Any]], None]


class EnginePort(Protocol):
    """Duck-typed subset of the canonical AudioPort used by the host."""

    def activate(self) -> None: ...

    def load(self, file_path: Path) -> None: ...

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def seek(self, position_ms: int) -> None: ...

    def set_volume(self, value: int) -> None: ...

    def set_muted(self, muted: bool) -> None: ...

    def position(self) -> int: ...

    def duration(self) -> int: ...

    def close(self) -> None: ...


def default_gstreamer_port_factory(
    coordinator: HostDirectCoordinator,
) -> EnginePort:
    """Production factory: the canonical in-process port, inside the child."""
    from michi.infrastructure.audio_engines.gstreamer import (
        GStreamerAudioPort,
        GStreamerBindings,
    )

    return GStreamerAudioPort(GStreamerBindings(), direct_executor=coordinator)


class HostEngineSession:
    """Deterministic command -> engine adapter (child side)."""

    def __init__(
        self,
        *,
        port_factory: Callable[[HostDirectCoordinator], EnginePort],
        emit: EmitEvent,
        request_callback: Callable[[str, dict, float], tuple[bool, dict]],
    ) -> None:
        self._port_factory = port_factory
        self._emit = emit
        self._port: EnginePort | None = None
        self._opened = False
        self._processing_candidate: Any | None = None
        self._processing_plan_wire: dict[str, Any] | None = None
        self._processing_pipeline_generation: int | None = None
        self._native_dsd = NativeDsdHostRuntime()
        self._native_dsd_active = False
        self._native_eos_emitted = False
        self._native_timer_source = None
        self._native_timer_bindings = None
        self._dop = DopHostRuntime()
        self._dop_active = False
        self._dop_eos_emitted = False
        self._dop_timer_source = None
        self._dop_timer_bindings = None
        self._dsd_pcm = DsdPcmHostRuntime()
        self._dsd_pcm_active = False
        self._dsd_pcm_eos_emitted = False
        self._dsd_pcm_timer_source = None
        self._dsd_pcm_timer_bindings = None
        self._processing_generation: int | None = None
        self._processing_host_generation: int = 0
        self._coordinator = HostDirectCoordinator(request_callback)

    @property
    def opened(self) -> bool:
        return self._opened

    # ── dispatch ──────────────────────────────────────────────────────
    def _install_native_eos_timer(self) -> None:
        """Observe the native bus on the SAME GLib pump as the engine."""
        port = self._port
        bindings = getattr(port, "_bindings", None)
        context = getattr(port, "_context", None)
        if bindings is None or context is None:
            return
        self._clear_native_eos_timer()

        def _tick():
            if not self._native_dsd_active:
                return False
            identity = self._native_dsd.query_identity()
            if identity.get("eos") and not self._native_eos_emitted:
                self._native_eos_emitted = True
                self._emit(
                    HostEvent.EOS,
                    {
                        "execution_id": identity.get("execution_id"),
                        "plan_id": identity.get("plan_id"),
                    },
                )
                self._native_timer_source = None
                return False
            return True

        source = bindings.create_timeout_source(50, _tick)
        bindings.attach_source(source, context)
        self._native_timer_source = source
        self._native_timer_bindings = bindings

    def _install_dop_eos_timer(self) -> None:
        port = self._port
        bindings = getattr(port, "_bindings", None)
        context = getattr(port, "_context", None)
        if bindings is None or context is None:
            return
        self._clear_dop_eos_timer()

        def _tick():
            if not self._dop_active:
                return False
            identity = self._dop.query_identity()
            if identity.get("eos") and not self._dop_eos_emitted:
                self._dop_eos_emitted = True
                self._emit(
                    HostEvent.EOS,
                    {
                        "dop": True,
                        "execution_id": identity.get("execution_id"),
                        "plan_id": identity.get("plan_id"),
                        "host_generation": identity.get("host_generation"),
                    },
                )
                self._dop_timer_source = None
                return False
            return True

        source = bindings.create_timeout_source(50, _tick)
        bindings.attach_source(source, context)
        self._dop_timer_source = source
        self._dop_timer_bindings = bindings

    def _install_dsd_pcm_eos_timer(self) -> None:
        port = self._port
        bindings = getattr(port, "_bindings", None)
        context = getattr(port, "_context", None)
        if bindings is None or context is None:
            return
        self._clear_dsd_pcm_eos_timer()

        def _tick():
            if not self._dsd_pcm_active:
                return False
            identity = self._dsd_pcm.query_identity()
            if identity.get("eos") and not self._dsd_pcm_eos_emitted:
                self._dsd_pcm_eos_emitted = True
                self._emit(
                    HostEvent.EOS,
                    {
                        "dsd_pcm": True,
                        "execution_id": identity.get("execution_id"),
                        "plan_id": identity.get("plan_id"),
                        "host_generation": identity.get("host_generation"),
                    },
                )
                self._dsd_pcm_timer_source = None
                return False
            return True

        source = bindings.create_timeout_source(50, _tick)
        bindings.attach_source(source, context)
        self._dsd_pcm_timer_source = source
        self._dsd_pcm_timer_bindings = bindings

    def _clear_dsd_pcm_eos_timer(self) -> None:
        source = self._dsd_pcm_timer_source
        bindings = self._dsd_pcm_timer_bindings
        self._dsd_pcm_timer_source = None
        self._dsd_pcm_timer_bindings = None
        if source is not None and bindings is not None:
            import contextlib

            with contextlib.suppress(Exception):
                bindings.destroy_source(source)

    def _clear_dop_eos_timer(self) -> None:
        source = self._dop_timer_source
        bindings = self._dop_timer_bindings
        self._dop_timer_source = None
        self._dop_timer_bindings = None
        if source is not None and bindings is not None:
            bindings.destroy_source(source)

    def _clear_native_eos_timer(self) -> None:
        source = self._native_timer_source
        bindings = self._native_timer_bindings
        self._native_timer_source = None
        self._native_timer_bindings = None
        if source is not None and bindings is not None:
            bindings.destroy_source(source)

    def handle(
        self, operation: str, payload: dict[str, Any], command_generation: int
    ) -> tuple[bool, dict[str, Any]]:
        handler = _HANDLERS.get(operation)
        if handler is None:
            return False, {
                "code": "OUTPUT_HOST_COMMAND_FAILED",
                "detail": f"unsupported operation {operation!r}",
            }
        _ = command_generation  # generation stamping lives in the caller
        try:
            return handler(self, payload)
        except AudioLoadError as exc:
            return False, {
                "code": "AUDIO_LOAD_FAILED",
                "detail": exc.detail,
                "previous_source_preserved": bool(exc.previous_source_preserved),
            }
        except Exception as exc:  # noqa: BLE001 - typed rejection boundary
            code = getattr(exc, "code", None) or type(exc).__name__
            return False, {"code": str(code), "detail": str(exc)[:1000]}

    # ── operations ────────────────────────────────────────────────────
    def _op_open(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        if self._port is not None:
            return True, {"already_open": True}
        port = self._port_factory(self._coordinator)
        port.activate()
        self._wire_subscriptions(port)
        self._port = port
        self._opened = True
        return True, {"opened": True}

    def _op_close_pipeline(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        if self._native_dsd_active or self._dop_active:
            return False, {
                "code": "NATIVE_DSD_PIPELINE_ACTIVE",
                "detail": "release the active DSD/DoP execution before closing PCM",
            }
        port = self._require_port()
        port.close()
        self._port = None
        self._opened = False
        return True, {"closed": True}

    def _op_load(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        if self._native_dsd_active or self._dop_active:
            return False, {
                "code": "NATIVE_DSD_LOAD_CONFLICT",
                "detail": "a DSD/DoP execution owns the output",
            }
        port = self._require_port()
        path = self._require_path(payload)
        port.load(path)
        return True, {}

    def _op_play(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().play()
        return True, {}

    def _op_pause(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().pause()
        return True, {}

    def _op_resume(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().resume()
        return True, {}

    def _op_stop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().stop()
        return True, {}

    def _op_seek(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        position = payload.get("position_ms")
        if not isinstance(position, int) or isinstance(position, bool) or position < 0:
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "position_ms must be a non-negative integer",
            }
        self._require_port().seek(position)
        return True, {}

    def _op_set_volume(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        value = payload.get("value")
        if not isinstance(value, int) or isinstance(value, bool):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "value must be an integer",
            }
        self._require_port().set_volume(value)
        return True, {}

    def _op_set_muted(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        muted = payload.get("muted")
        if not isinstance(muted, bool):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "muted must be a boolean",
            }
        self._require_port().set_muted(muted)
        return True, {}

    def _op_query_position(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"value": int(self._require_port().position())}

    def _op_query_duration(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"value": int(self._require_port().duration())}

    def _op_prepare_processing_candidate(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        # One productive candidate at a time. A newer prepare supersedes the
        # previous candidate ONLY after its native teardown is proven; an
        # unproven retirement fails closed.
        if self._processing_candidate is not None:
            self._abort_processing_candidate()
        plan = payload.get("plan")
        if not isinstance(plan, dict):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "processing plan must be an object",
            }
        from michi.infrastructure.audio_processing.gstreamer_graph_builder import (
            build_processing_candidate,
        )
        from michi.infrastructure.audio_processing.gstreamer_runtime import (
            inspect_processing_candidate,
        )

        built = build_processing_candidate(plan)
        self._processing_candidate = built
        self._processing_plan_wire = dict(plan)
        self._processing_pipeline_generation = int(
            getattr(self._port, "pipeline_generation", 0)
        )
        self._processing_generation = int(payload.get("processing_generation") or 0)
        self._processing_host_generation = int(payload.get("host_generation") or 0)
        observed = inspect_processing_candidate(built, plan)
        observed["pipeline_generation"] = self._processing_pipeline_generation
        return True, {"observed": observed}

    def _op_commit_processing_candidate(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        built = self._processing_candidate
        plan = self._processing_plan_wire
        if built is None or plan is None:
            return False, {
                "code": "DSP_CANDIDATE_MISSING",
                "predecessor_untouched": True,
                "detail": "no prepared processing candidate to commit",
            }
        if str(payload.get("plan_id")) != built.plan_id:
            return False, {
                "code": "DSP_CANDIDATE_MISMATCH",
                "predecessor_untouched": True,
                "detail": "commit plan does not match the prepared candidate",
            }
        port = self._require_port()
        # ── PRE-DESTRUCTIVE GENERATION FENCE ─────────────────────────
        # Prove the CURRENT reality still matches the prepared identity
        # BEFORE any native mutation: a stale commit can never install over
        # a newer pipeline/processing generation.
        current_pipeline_generation = int(getattr(port, "pipeline_generation", 0))
        if (
            self._processing_pipeline_generation is None
            or current_pipeline_generation != self._processing_pipeline_generation
        ):
            return False, {
                "code": "DSP_STALE_PIPELINE_GENERATION",
                "predecessor_untouched": True,
                "detail": (
                    f"prepared pipeline generation "
                    f"{self._processing_pipeline_generation!r} != current "
                    f"{current_pipeline_generation}"
                ),
            }
        requested_processing_generation = int(
            payload.get("processing_generation") or -1
        )
        if (
            self._processing_generation is None
            or requested_processing_generation != self._processing_generation
        ):
            return False, {
                "code": "DSP_STALE_PROCESSING_GENERATION",
                "predecessor_untouched": True,
                "detail": (
                    f"commit processing generation "
                    f"{requested_processing_generation} != prepared "
                    f"{self._processing_generation!r}"
                ),
            }
        # The standalone harness candidate was already read+validated at
        # PREPARE and is retired FIRST with PROVEN teardown: a teardown
        # failure leaves the productive runtime untouched.
        self._abort_processing_candidate()
        install = getattr(port, "install_processing_filter", None)
        if not callable(install):
            # EFFECTIVE requires a REAL productive install: fail closed.
            return False, {
                "code": "DSP_PLAYBACK_SEAM_UNAVAILABLE",
                "predecessor_untouched": True,
                "detail": ("the hosted engine exposes no productive processing seam"),
            }
        from michi.infrastructure.audio_processing.gstreamer_graph_builder import (
            build_processing_filter,
        )
        from michi.infrastructure.audio_processing.gstreamer_runtime import (
            inspect_processing_filter,
        )

        filter_info = build_processing_filter(plan)
        try:
            install_result = install(filter_info["bin"])
            if not isinstance(install_result, dict):
                raise RuntimeError("install seam returned no receipt facts")
            observed = inspect_processing_filter(filter_info, plan)
        except Exception as exc:  # noqa: BLE001 - typed rejection boundary
            code = getattr(exc, "code", None) or "DSP_COMMIT_FAILED"
            return False, {
                "code": str(code),
                "detail": str(exc)[:500],
                "predecessor_restored": bool(
                    getattr(exc, "predecessor_restored", False)
                ),
                "predecessor_untouched": bool(
                    getattr(exc, "predecessor_untouched", False)
                ),
            }
        self._processing_plan_wire = None
        self._processing_pipeline_generation = None
        self._processing_generation = None
        return True, {
            "receipt": {
                "installed": bool(install_result.get("installed")),
                "runtime_identity": str(install_result.get("runtime_identity") or ""),
                "pipeline_generation": int(
                    install_result.get("pipeline_generation") or 0
                ),
                "processing_generation": requested_processing_generation,
                "host_generation": int(
                    payload.get("host_generation") or self._processing_host_generation
                ),
                "candidate_id": str(payload.get("candidate_id") or ""),
                "observed_plan_id": str(observed.get("plan_id") or ""),
                "observed_graph_revision": int(observed.get("graph_revision") or 0),
                "install_diagnostics": dict(
                    install_result.get("install_diagnostics") or {}
                ),
                "observed": observed,
            }
        }

    def _op_capture_processing_output(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        capture = getattr(port, "capture_processing_output", None)
        if not callable(capture):
            return False, {
                "code": "DSP_CAPTURE_UNAVAILABLE",
                "detail": "this engine exposes no signal capture instrumentation",
            }
        seconds = payload.get("seconds")
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "seconds must be a number",
            }
        passive = payload.get("passive", False)
        if not isinstance(passive, bool):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_FIELD", "passive must be a boolean"
            )
        probe_hz = payload.get("probe_hz")
        if probe_hz is not None and (
            not isinstance(probe_hz, list)
            or any(
                not isinstance(hz, (int, float)) or isinstance(hz, bool)
                for hz in probe_hz
            )
        ):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "probe_hz must be a list of numbers",
            }
        metrics = capture(
            float(seconds),
            [float(hz) for hz in probe_hz] if probe_hz else None,
            passive=passive,
        )
        return True, {"metrics": metrics}

    def _op_bypass_processing(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        remove = getattr(port, "remove_processing_filter", None)
        if not callable(remove):
            return False, {
                "code": "DSP_PLAYBACK_SEAM_UNAVAILABLE",
                "predecessor_untouched": True,
                "detail": "the hosted engine exposes no productive processing seam",
            }
        if self._processing_candidate is not None:
            self._abort_processing_candidate()
            self._processing_plan_wire = None
        installed_filter = getattr(port, "_installed_processing_filter", None)
        had_filter = installed_filter is not None
        removed = bool(remove())
        return True, {
            "bypassed": removed,
            "removed": removed,
            "had_filter": had_filter,
            "pipeline_generation": int(getattr(port, "pipeline_generation", 0)),
        }

    def _op_abort_processing_candidate(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        if self._processing_candidate is None:
            return True, {"aborted": False}
        # Raises on unproven teardown: the candidate stays owned, the caller
        # gets a typed rejection and must never report success.
        self._abort_processing_candidate()
        return True, {"aborted": True}

    def _abort_processing_candidate(self) -> bool:
        """Native teardown with proven retirement; failure keeps ownership."""
        built = self._processing_candidate
        if built is None:
            return False
        from michi.infrastructure.audio_processing.gstreamer_runtime import (
            abort_processing_candidate,
        )

        abort_processing_candidate(built)  # raises on unproven teardown
        self._processing_candidate = None
        return True

    def _op_query_processing_capabilities(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        # The port may provide scripted facts (test compositions); otherwise
        # the CHILD-NATIVE probe inspects real factories in this process.
        port = self._require_port()
        supplied = getattr(port, "processing_capabilities", None)
        if callable(supplied):
            facts = supplied()
        else:
            from michi.infrastructure.audio_processing.gstreamer_capabilities import (
                probe_processing_capabilities,
            )

            facts = probe_processing_capabilities()
        if not isinstance(facts, dict):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "processing capabilities must be an object",
            }
        return True, {"facts": facts}

    def _op_query_resync_evidence(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        evidence = getattr(port, "resync_evidence", None)
        if evidence is None:
            return True, {"evidence": {}}
        raw = evidence() or {}
        clean: dict[str, Any] = {}
        for key, value in raw.items():
            if (
                value is None
                or isinstance(value, str)
                or isinstance(value, int)
                and not isinstance(value, bool)
            ):
                clean[str(key)] = value
            else:
                return False, {
                    "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                    "detail": f"resync evidence field {key!r} is not primitive",
                }
        return True, {"evidence": clean}

    def _op_prepare_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._port
        has_source = getattr(port, "has_active_source", None)
        owns_pcm = (
            bool(has_source())
            if callable(has_source)
            else bool(
                getattr(port, "_current_path", None) is not None
                or getattr(port, "_pending_path", None) is not None
            )
        )
        if owns_pcm or self._dop_active or self._dsd_pcm_active:
            return False, {
                "code": "NATIVE_DSD_PCM_CONFLICT",
                "detail": "a PCM/DoP pipeline still owns the output; release it first",
            }
        try:
            identity = self._native_dsd.prepare(payload)
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        self._native_dsd_active = True
        self._native_eos_emitted = False
        self._install_native_eos_timer()
        return True, identity

    def _op_commit_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict):
            return False, {
                "code": "HOST_PROTOCOL_INVALID_FIELD",
                "detail": "expected must be an object",
            }
        try:
            return True, self._native_dsd.commit(expected)
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_abort_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict) or not expected:
            return False, {
                "code": "NATIVE_DSD_HOST_IDENTITY_REQUIRED",
                "detail": "abort requires the full execution identity",
            }
        try:
            result = self._native_dsd.abort(expected)
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        if result.get("aborted") is True and result.get("stale") is False:
            self._native_dsd_active = False
            self._clear_native_eos_timer()
        return True, result

    def _op_start_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._native_dsd.start()
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_pause_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._native_dsd.pause()
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_resume_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._native_dsd.resume()
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_stop_native_dsd(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict) or not expected:
            return False, {
                "code": "NATIVE_DSD_HOST_IDENTITY_REQUIRED",
                "detail": "stop requires the full execution identity",
            }
        try:
            result = self._native_dsd.stop(expected)
        except NativeDsdHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        if result.get("stopped") is True and result.get("stale") is False:
            self._native_dsd_active = False
            self._clear_native_eos_timer()
        return True, result

    def _op_query_native_dsd_identity(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        identity = self._native_dsd.query_identity()
        return True, {"identity": identity}

    def _op_query_native_dsd_evidence(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"evidence": self._native_dsd.query_evidence()}

    def _op_prepare_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        if self._native_dsd_active or self._dsd_pcm_active:
            return False, {
                "code": "DOP_ENGINE_CONFLICT",
                "detail": "release Native DSD before preparing DoP",
            }
        port = self._port
        has_source = getattr(port, "has_active_source", None)
        owns_pcm = (
            bool(has_source())
            if callable(has_source)
            else bool(
                getattr(port, "_current_path", None) is not None
                or getattr(port, "_pending_path", None) is not None
            )
        )
        if owns_pcm:
            return False, {
                "code": "DOP_PCM_CONFLICT",
                "detail": "release the PCM pipeline before preparing DoP",
            }
        try:
            identity = self._dop.prepare(payload)
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        self._dop_active = True
        self._dop_eos_emitted = False
        self._install_dop_eos_timer()
        return True, identity

    def _op_commit_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict):
            return False, {
                "code": "HOST_PROTOCOL_INVALID_FIELD",
                "detail": "expected must be an object",
            }
        try:
            return True, self._dop.commit(expected)
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_abort_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict) or not expected:
            return False, {
                "code": "DOP_HOST_IDENTITY_REQUIRED",
                "detail": "abort requires the full execution identity",
            }
        try:
            result = self._dop.abort(expected)
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        if result.get("aborted") is True and result.get("stale") is False:
            self._dop_active = False
            self._clear_dop_eos_timer()
        return True, result

    def _op_start_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._dop.start(payload.get("expected"))
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_pause_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._dop.pause(payload.get("expected"))
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_resume_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._dop.resume(payload.get("expected"))
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_stop_dop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict) or not expected:
            return False, {
                "code": "DOP_HOST_IDENTITY_REQUIRED",
                "detail": "stop requires the full execution identity",
            }
        try:
            result = self._dop.stop(expected)
        except DopHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        if result.get("stopped") is True and result.get("stale") is False:
            self._dop_active = False
            self._clear_dop_eos_timer()
        return True, result

    def _op_prepare_dsd_pcm(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        if self._native_dsd_active or self._dop_active:
            return False, {
                "code": "DSD_PCM_ENGINE_CONFLICT",
                "detail": "release Native DSD/DoP before DSD→PCM",
            }
        port = self._port
        has_source = getattr(port, "has_active_source", None)
        owns_pcm = bool(has_source()) if callable(has_source) else False
        if owns_pcm:
            return False, {
                "code": "DSD_PCM_PCM_CONFLICT",
                "detail": "release the PCM pipeline before DSD→PCM",
            }
        try:
            identity = self._dsd_pcm.prepare(payload)
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        self._dsd_pcm_active = True
        self._dsd_pcm_eos_emitted = False
        self._install_dsd_pcm_eos_timer()
        return True, identity

    def _op_commit_dsd_pcm(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict):
            return False, {
                "code": "HOST_PROTOCOL_INVALID_FIELD",
                "detail": "expected must be object",
            }
        try:
            return True, self._dsd_pcm.commit(expected)
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_abort_dsd_pcm(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict) or not expected:
            return False, {
                "code": "DSD_PCM_HOST_IDENTITY_REQUIRED",
                "detail": "identity required",
            }
        try:
            result = self._dsd_pcm.abort(expected)
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        if result.get("aborted") is True and result.get("stale") is False:
            self._dsd_pcm_active = False
            self._clear_dsd_pcm_eos_timer()
        return True, result

    def _op_start_dsd_pcm(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._dsd_pcm.start(payload.get("expected"))
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_pause_dsd_pcm(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._dsd_pcm.pause(payload.get("expected"))
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_resume_dsd_pcm(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        try:
            return True, self._dsd_pcm.resume(payload.get("expected"))
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}

    def _op_stop_dsd_pcm(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict) or not expected:
            return False, {
                "code": "DSD_PCM_HOST_IDENTITY_REQUIRED",
                "detail": "identity required",
            }
        try:
            result = self._dsd_pcm.stop(expected)
        except DsdPcmHostError as exc:
            return False, {"code": exc.code, "detail": exc.detail}
        if result.get("stopped") is True and result.get("stale") is False:
            self._dsd_pcm_active = False
            self._clear_dsd_pcm_eos_timer()
        return True, result

    def _op_query_dsd_pcm_identity(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"identity": self._dsd_pcm.query_identity()}

    def _op_query_dsd_pcm_evidence(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"evidence": self._dsd_pcm.query_evidence()}

    def _op_query_dop_identity(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"identity": self._dop.query_identity()}

    def _op_query_dop_evidence(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"evidence": self._dop.query_evidence()}

    def _op_stage_direct(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        preparation = preparation_from_wire(payload.get("preparation"))
        port = self._require_port()
        # The port validates the staged recipe against the coordinator mirror,
        # so the mirror is populated first; a failed port stage rolls it back.
        self._coordinator.stage(preparation)
        try:
            port.stage_direct_load(preparation, executor=self._coordinator)  # type: ignore[attr-defined]
        except Exception:
            self._coordinator.discard(preparation.handle)
            raise
        return True, {}

    def _op_discard_direct(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        handle = handle_from_wire(payload.get("handle"))
        port = self._require_port()
        discarded = False
        stage = getattr(port, "discard_direct_load", None)
        if stage is not None:
            discarded = bool(stage(handle, executor=self._coordinator))
        self._coordinator.discard(handle)
        return True, {"discarded": discarded}

    def _op_stage_managed(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """AP2-F06: stage ONE strict managed sink for the selected binding."""
        from michi.infrastructure.audio_output.strict_sink import StrictSinkRecipe

        data = payload.get("recipe")
        if not isinstance(data, dict):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_FIELD", "managed recipe must be an object"
            )
        recipe = StrictSinkRecipe(
            plan_id=str(data.get("plan_id") or ""),
            sink_factory=str(data.get("sink_factory") or ""),
            device=str(data.get("device") or ""),
            media_type=str(data.get("media_type") or "audio/x-raw"),
            gst_format=str(data.get("gst_format") or ""),
            rate_hz=int(data.get("rate_hz") or 0),
            channels=int(data.get("channels") or 0),
            layout=str(data.get("layout") or "interleaved"),
            container_conversion=False,
            resync_delay_ms=0,
        )
        port = self._require_port()
        port.stage_managed_load(
            recipe, execution_id=str(data.get("execution_id") or "")
        )  # type: ignore[attr-defined]
        return True, {}

    def _op_stop_managed(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        expected = payload.get("expected")
        if not isinstance(expected, dict):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_FIELD", "expected identity must be an object"
            )
        port = self._require_port()
        result = port.stop_managed(expected)  # type: ignore[attr-defined]
        if not isinstance(result, dict):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_RESULT", "stop_managed must return an object"
            )
        return True, {"result": result}

    def _op_query_managed_identity(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        identity = port.managed_identity()  # type: ignore[attr-defined]
        if not isinstance(identity, dict):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_RESULT", "managed identity must be an object"
            )
        return True, {"identity": identity}

    # ── help ──────────────────────────────────────────────────────────
    def _require_port(self) -> EnginePort:
        if self._port is None:
            raise RuntimeError("engine is not open in this host")
        return self._port

    @staticmethod
    def _require_path(payload: dict[str, Any]) -> Path:
        path = payload.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("path must be a non-empty string")
        return Path(path)

    def _wire_subscriptions(self, port: EnginePort) -> None:
        emit = self._emit

        def state_changed(status: object) -> None:
            # PlaybackStatus is a name-identified enum: transport the NAME.
            value = getattr(status, "name", None) or str(status)
            emit(HostEvent.STATE_CHANGED, {"status": value})

        def media_accepted(path: Path) -> None:
            emit(HostEvent.MEDIA_ACCEPTED, {"path": str(path)})

        def media_rejected(path: Path, reason: str) -> None:
            emit(HostEvent.MEDIA_REJECTED, {"path": str(path), "reason": reason})

        def end_of_media() -> None:
            emit(HostEvent.EOS, {})

        def position_changed(ms: int) -> None:
            emit(HostEvent.POSITION, {"ms": int(ms)})

        def duration_changed(ms: int) -> None:
            emit(HostEvent.DURATION, {"ms": int(ms)})

        port.subscribe_playback_state_changed(state_changed)  # type: ignore[attr-defined]
        port.subscribe_media_accepted(media_accepted)  # type: ignore[attr-defined]
        port.subscribe_media_rejected(media_rejected)  # type: ignore[attr-defined]
        port.subscribe_end_of_media(end_of_media)  # type: ignore[attr-defined]
        port.subscribe_position_changed(position_changed)  # type: ignore[attr-defined]
        port.subscribe_duration_changed(duration_changed)  # type: ignore[attr-defined]
        failure_callback = getattr(port, "set_runtime_failure_callback", None)
        if failure_callback is not None:

            def runtime_failed(generation: int, reason: str) -> None:
                emit(
                    HostEvent.HOST_FAULT,
                    {"reason": reason, "port_generation": int(generation)},
                )

            failure_callback(runtime_failed)

    def close(self) -> None:
        """Best-effort port teardown before host exit."""
        self._clear_native_eos_timer()
        self._clear_dop_eos_timer()
        self._clear_dsd_pcm_eos_timer()
        self._native_dsd.close()
        self._dop.close()
        self._dsd_pcm.close()
        self._native_dsd_active = False
        self._dop_active = False
        self._dsd_pcm_active = False
        port = self._port
        self._port = None
        self._opened = False
        if port is None:
            return
        import contextlib

        with contextlib.suppress(Exception):
            port.close()


#: Ops implemented in this phase (Direct staging lands in its own commit).
_HANDLERS: dict[str, Callable[[HostEngineSession, dict], tuple[bool, dict]]] = {
    HostOperation.OPEN.value: HostEngineSession._op_open,
    HostOperation.CLOSE_PIPELINE.value: HostEngineSession._op_close_pipeline,
    HostOperation.LOAD.value: HostEngineSession._op_load,
    HostOperation.PLAY.value: HostEngineSession._op_play,
    HostOperation.PAUSE.value: HostEngineSession._op_pause,
    HostOperation.RESUME.value: HostEngineSession._op_resume,
    HostOperation.STOP.value: HostEngineSession._op_stop,
    HostOperation.SEEK.value: HostEngineSession._op_seek,
    HostOperation.SET_VOLUME.value: HostEngineSession._op_set_volume,
    HostOperation.SET_MUTED.value: HostEngineSession._op_set_muted,
    HostOperation.QUERY_POSITION.value: HostEngineSession._op_query_position,
    HostOperation.QUERY_DURATION.value: HostEngineSession._op_query_duration,
    HostOperation.QUERY_RESYNC_EVIDENCE.value: (
        HostEngineSession._op_query_resync_evidence
    ),
    HostOperation.QUERY_PROCESSING_CAPABILITIES.value: (
        HostEngineSession._op_query_processing_capabilities
    ),
    HostOperation.PREPARE_PROCESSING_CANDIDATE.value: (
        HostEngineSession._op_prepare_processing_candidate
    ),
    HostOperation.COMMIT_PROCESSING_CANDIDATE.value: (
        HostEngineSession._op_commit_processing_candidate
    ),
    HostOperation.BYPASS_PROCESSING.value: (HostEngineSession._op_bypass_processing),
    HostOperation.CAPTURE_PROCESSING_OUTPUT.value: (
        HostEngineSession._op_capture_processing_output
    ),
    HostOperation.ABORT_PROCESSING_CANDIDATE.value: (
        HostEngineSession._op_abort_processing_candidate
    ),
    HostOperation.PREPARE_NATIVE_DSD.value: (HostEngineSession._op_prepare_native_dsd),
    HostOperation.COMMIT_NATIVE_DSD.value: (HostEngineSession._op_commit_native_dsd),
    HostOperation.ABORT_NATIVE_DSD.value: (HostEngineSession._op_abort_native_dsd),
    HostOperation.START_NATIVE_DSD.value: (HostEngineSession._op_start_native_dsd),
    HostOperation.PAUSE_NATIVE_DSD.value: (HostEngineSession._op_pause_native_dsd),
    HostOperation.RESUME_NATIVE_DSD.value: (HostEngineSession._op_resume_native_dsd),
    HostOperation.STOP_NATIVE_DSD.value: (HostEngineSession._op_stop_native_dsd),
    HostOperation.QUERY_NATIVE_DSD_IDENTITY.value: (
        HostEngineSession._op_query_native_dsd_identity
    ),
    HostOperation.QUERY_NATIVE_DSD_EVIDENCE.value: (
        HostEngineSession._op_query_native_dsd_evidence
    ),
    HostOperation.PREPARE_DOP.value: HostEngineSession._op_prepare_dop,
    HostOperation.COMMIT_DOP.value: HostEngineSession._op_commit_dop,
    HostOperation.ABORT_DOP.value: HostEngineSession._op_abort_dop,
    HostOperation.START_DOP.value: HostEngineSession._op_start_dop,
    HostOperation.PAUSE_DOP.value: HostEngineSession._op_pause_dop,
    HostOperation.RESUME_DOP.value: HostEngineSession._op_resume_dop,
    HostOperation.STOP_DOP.value: HostEngineSession._op_stop_dop,
    HostOperation.QUERY_DOP_IDENTITY.value: HostEngineSession._op_query_dop_identity,
    HostOperation.QUERY_DOP_EVIDENCE.value: HostEngineSession._op_query_dop_evidence,
    HostOperation.PREPARE_DSD_PCM.value: HostEngineSession._op_prepare_dsd_pcm,
    HostOperation.COMMIT_DSD_PCM.value: HostEngineSession._op_commit_dsd_pcm,
    HostOperation.ABORT_DSD_PCM.value: HostEngineSession._op_abort_dsd_pcm,
    HostOperation.START_DSD_PCM.value: HostEngineSession._op_start_dsd_pcm,
    HostOperation.PAUSE_DSD_PCM.value: HostEngineSession._op_pause_dsd_pcm,
    HostOperation.RESUME_DSD_PCM.value: HostEngineSession._op_resume_dsd_pcm,
    HostOperation.STOP_DSD_PCM.value: HostEngineSession._op_stop_dsd_pcm,
    HostOperation.QUERY_DSD_PCM_IDENTITY.value: (
        HostEngineSession._op_query_dsd_pcm_identity
    ),
    HostOperation.QUERY_DSD_PCM_EVIDENCE.value: (
        HostEngineSession._op_query_dsd_pcm_evidence
    ),
    HostOperation.STAGE_DIRECT.value: HostEngineSession._op_stage_direct,
    HostOperation.DISCARD_DIRECT.value: HostEngineSession._op_discard_direct,
    HostOperation.STAGE_MANAGED.value: HostEngineSession._op_stage_managed,
    HostOperation.STOP_MANAGED.value: HostEngineSession._op_stop_managed,
    HostOperation.QUERY_MANAGED_IDENTITY.value: (
        HostEngineSession._op_query_managed_identity
    ),
}
