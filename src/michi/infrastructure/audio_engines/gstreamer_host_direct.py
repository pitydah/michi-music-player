"""Direct execution transport for the GStreamer output host.

Wire DTOs for the immutable Direct objects (handle, strict recipe, runtime
snapshot) plus the CHILD-side coordinator that emulates the canonical
``GStreamerDirectOutputExecutor`` surface used by the port.

Non-negotiable authority split: the child only REPORTS facts. The parent's
real ``GStreamerDirectOutputExecutor`` remains the only classifier —
``verify_preroll``, ``observe_runtime``, ``begin_runtime``,
``mark_previous_source_released``, ``abort`` and ``release`` execute in the
parent through bounded reverse callbacks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from michi.domain.audio_evidence import RuntimeTransformEvidence
from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    HostProtocolError,
)
from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutionHandle,
    DirectExecutorError,
    DirectLoadPreparation,
)
from michi.infrastructure.audio_output.runtime_inspector import (
    DirectRuntimeSnapshot,
)
from michi.infrastructure.audio_output.strict_sink import StrictSinkRecipe

_REQUEST_TIMEOUT_S = 8.0

#: child -> parent reverse callback names (exact, no aliases).
CB_MARK_PREVIOUS_SOURCE_RELEASED = "mark_previous_source_released"
CB_BEGIN_RUNTIME = "begin_runtime"
CB_VERIFY_PREROLL = "verify_preroll"
CB_OBSERVE_RUNTIME = "observe_runtime"
CB_RECORD_RUNTIME_ANOMALY = "record_runtime_anomaly"
CB_ABORT = "abort"
CB_RELEASE = "release"


# ── wire codecs (strict, bounded) ─────────────────────────────────────
def _require_str(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", f"{key} must be a string"
        )
    return value


def _require_int(data: dict, key: str, minimum: int = 0) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD",
            f"{key} must be an integer >= {minimum}",
        )
    return value


def _optional_int(data: dict, key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", f"{key} must be an integer or null"
        )
    return value


def handle_to_wire(handle: DirectExecutionHandle) -> dict[str, Any]:
    return {"generation": int(handle.generation), "plan_id": str(handle.plan_id)}


def handle_from_wire(data: object) -> DirectExecutionHandle:
    if not isinstance(data, dict):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "handle must be an object"
        )
    return DirectExecutionHandle(
        generation=_require_int(data, "generation"),
        plan_id=_require_str(data, "plan_id"),
    )


def recipe_to_wire(recipe: StrictSinkRecipe) -> dict[str, Any]:
    return {
        "plan_id": recipe.plan_id,
        "sink_factory": recipe.sink_factory,
        "device": recipe.device,
        "media_type": recipe.media_type,
        "gst_format": recipe.gst_format,
        "rate_hz": int(recipe.rate_hz),
        "channels": int(recipe.channels),
        "layout": recipe.layout,
        "container_conversion": bool(recipe.container_conversion),
        "resync_delay_ms": int(recipe.resync_delay_ms),
    }


def recipe_from_wire(data: object) -> StrictSinkRecipe:
    if not isinstance(data, dict):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "recipe must be an object"
        )
    container = data.get("container_conversion", False)
    if not isinstance(container, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "container_conversion must be a boolean"
        )
    return StrictSinkRecipe(
        plan_id=_require_str(data, "plan_id"),
        sink_factory=_require_str(data, "sink_factory"),
        device=_require_str(data, "device"),
        media_type=_require_str(data, "media_type"),
        gst_format=_require_str(data, "gst_format"),
        rate_hz=_require_int(data, "rate_hz", 1),
        channels=_require_int(data, "channels", 1),
        layout=_require_str(data, "layout"),
        container_conversion=container,
        resync_delay_ms=_require_int(data, "resync_delay_ms"),
    )


def preparation_to_wire(preparation: DirectLoadPreparation) -> dict[str, Any]:
    return {
        "handle": handle_to_wire(preparation.handle),
        "recipe": recipe_to_wire(preparation.recipe),
        "candidate_volume": float(preparation.candidate_volume),
    }


def preparation_from_wire(data: object) -> DirectLoadPreparation:
    if not isinstance(data, dict):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "preparation must be an object"
        )
    volume = data.get("candidate_volume")
    if not isinstance(volume, (int, float)) or isinstance(volume, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "candidate_volume must be a number"
        )
    return DirectLoadPreparation(
        handle=handle_from_wire(data.get("handle")),
        recipe=recipe_from_wire(data.get("recipe")),
        candidate_volume=float(volume),
    )


def _transform_to_wire(evidence: RuntimeTransformEvidence) -> dict[str, Any]:
    return {
        "converter_present": bool(evidence.converter_present),
        "converter_transforming": evidence.converter_transforming,
        "resampler_present": bool(evidence.resampler_present),
        "resampler_transforming": evidence.resampler_transforming,
        "remix_transforming": evidence.remix_transforming,
        "converter_dithering_disabled": evidence.converter_dithering_disabled,
        "converter_noise_shaping_disabled": evidence.converter_noise_shaping_disabled,
    }


def _optional_bool(data: dict, key: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", f"{key} must be a boolean or null"
        )
    return value


def _transform_from_wire(data: object) -> RuntimeTransformEvidence:
    if not isinstance(data, dict):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "transform_evidence must be an object"
        )
    present = {
        key: data.get(key, False) for key in ("converter_present", "resampler_present")
    }
    for key, value in present.items():
        if not isinstance(value, bool):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_FIELD", f"{key} must be a boolean"
            )
    return RuntimeTransformEvidence(
        converter_present=present["converter_present"],
        converter_transforming=_optional_bool(data, "converter_transforming"),
        resampler_present=present["resampler_present"],
        resampler_transforming=_optional_bool(data, "resampler_transforming"),
        remix_transforming=_optional_bool(data, "remix_transforming"),
        converter_dithering_disabled=_optional_bool(
            data, "converter_dithering_disabled"
        ),
        converter_noise_shaping_disabled=_optional_bool(
            data, "converter_noise_shaping_disabled"
        ),
    )


def snapshot_to_wire(snapshot: DirectRuntimeSnapshot) -> dict[str, Any]:
    return {
        "execution_generation": int(snapshot.execution_generation),
        "port_generation": int(snapshot.port_generation),
        "plan_id": snapshot.plan_id,
        "sink_factory": snapshot.sink_factory,
        "sink_device": snapshot.sink_device,
        "negotiated_format": snapshot.negotiated_format,
        "negotiated_rate_hz": snapshot.negotiated_rate_hz,
        "negotiated_channels": snapshot.negotiated_channels,
        "graph_factories": list(snapshot.graph_factories),
        "transform_evidence": _transform_to_wire(snapshot.transform_evidence),
        "decoded_format": snapshot.decoded_format,
        "decoded_rate_hz": snapshot.decoded_rate_hz,
        "decoded_channels": snapshot.decoded_channels,
        "decoded_significant_bits": snapshot.decoded_significant_bits,
        "effective_significant_bits": snapshot.effective_significant_bits,
        "graph_inspection_complete": bool(snapshot.graph_inspection_complete),
        "software_gain": snapshot.software_gain,
        "muted": snapshot.muted,
        "sink_provides_clock": snapshot.sink_provides_clock,
        "sink_clock_is_pipeline_clock": snapshot.sink_clock_is_pipeline_clock,
        "slave_method": snapshot.slave_method,
    }


def snapshot_from_wire(data: object) -> DirectRuntimeSnapshot:
    if not isinstance(data, dict):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "snapshot must be an object"
        )
    factories = data.get("graph_factories", ())
    if not isinstance(factories, (list, tuple)) or any(
        not isinstance(item, str) for item in factories
    ):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "graph_factories must be strings"
        )
    complete = data.get("graph_inspection_complete", True)
    if not isinstance(complete, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "graph_inspection_complete must be bool"
        )
    gain = data.get("software_gain")
    if gain is not None and not isinstance(gain, (int, float)):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "software_gain must be a number or null"
        )
    muted = data.get("muted")
    if muted is not None and not isinstance(muted, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "muted must be a boolean or null"
        )
    for key in ("sink_factory", "sink_device", "plan_id"):
        _require_str(data, key)
    return DirectRuntimeSnapshot(
        execution_generation=_require_int(data, "execution_generation"),
        port_generation=_require_int(data, "port_generation"),
        plan_id=data["plan_id"],
        sink_factory=data["sink_factory"],
        sink_device=data["sink_device"],
        negotiated_format=_opt_str(data, "negotiated_format"),
        negotiated_rate_hz=_optional_int(data, "negotiated_rate_hz"),
        negotiated_channels=_optional_int(data, "negotiated_channels"),
        graph_factories=tuple(factories),
        transform_evidence=_transform_from_wire(data.get("transform_evidence", {})),
        decoded_format=_opt_str(data, "decoded_format"),
        decoded_rate_hz=_optional_int(data, "decoded_rate_hz"),
        decoded_channels=_optional_int(data, "decoded_channels"),
        decoded_significant_bits=_optional_int(data, "decoded_significant_bits"),
        effective_significant_bits=_optional_int(data, "effective_significant_bits"),
        graph_inspection_complete=complete,
        software_gain=None if gain is None else float(gain),
        muted=muted,
        sink_provides_clock=_optional_bool(data, "sink_provides_clock"),
        sink_clock_is_pipeline_clock=_optional_bool(
            data, "sink_clock_is_pipeline_clock"
        ),
        slave_method=_opt_str(data, "slave_method"),
    )


def _opt_str(data: dict, key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", f"{key} must be a string or null"
        )
    return value


# ── child-side coordinator ────────────────────────────────────────────
RequestCallback = Callable[[str, dict[str, Any], float], tuple[bool, dict[str, Any]]]


class HostDirectCoordinator:
    """Child-side mirror of the parent's Direct executor surface.

    Holds ONLY the staged recipe needed for local validation; every semantic
    transition is a bounded reverse callback into the parent.
    """

    def __init__(self, request_callback: RequestCallback) -> None:
        self._request = request_callback
        self._handle: DirectExecutionHandle | None = None
        self._recipe: StrictSinkRecipe | None = None

    @property
    def handle(self) -> DirectExecutionHandle | None:
        return self._handle

    def stage(self, preparation: DirectLoadPreparation) -> None:
        self._handle = preparation.handle
        self._recipe = preparation.recipe

    def discard(self, handle: DirectExecutionHandle) -> bool:
        if self._handle != handle:
            return False
        self._handle = None
        self._recipe = None
        return True

    def recipe_for_load(self, handle: DirectExecutionHandle) -> StrictSinkRecipe:
        if self._handle != handle:
            raise DirectExecutorError(
                "DIRECT_STALE_EXECUTION", "handle is not the current execution"
            )
        if self._recipe is None:
            raise DirectExecutorError(
                "DIRECT_EXECUTION_NOT_STAGED", "no staged execution in host"
            )
        return self._recipe

    # ── reversals ─────────────────────────────────────────────────────
    def _call(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        ok, response = self._request(name, payload, _REQUEST_TIMEOUT_S)
        if not ok:
            code = str(response.get("code") or "DIRECT_CALLBACK_REJECTED")
            detail = str(response.get("detail") or f"{name} rejected by parent")
            raise DirectExecutorError(code, detail)
        return response

    def mark_previous_source_released(self) -> None:
        self._call(CB_MARK_PREVIOUS_SOURCE_RELEASED, {})

    def begin_runtime(
        self, handle: DirectExecutionHandle, *, port_generation: int
    ) -> None:
        self._call(
            CB_BEGIN_RUNTIME,
            {"handle": handle_to_wire(handle), "port_generation": int(port_generation)},
        )

    def verify_preroll(
        self, handle: DirectExecutionHandle, snapshot: DirectRuntimeSnapshot
    ) -> None:
        self._call(
            CB_VERIFY_PREROLL,
            {
                "handle": handle_to_wire(handle),
                "snapshot": snapshot_to_wire(snapshot),
            },
        )

    def observe_runtime(
        self, handle: DirectExecutionHandle, snapshot: DirectRuntimeSnapshot
    ) -> bool:
        response = self._call(
            CB_OBSERVE_RUNTIME,
            {
                "handle": handle_to_wire(handle),
                "snapshot": snapshot_to_wire(snapshot),
            },
        )
        return bool(response.get("recorded", True))

    def record_runtime_anomaly(
        self, handle: DirectExecutionHandle, detail: str
    ) -> bool:
        response = self._call(
            CB_RECORD_RUNTIME_ANOMALY,
            {"handle": handle_to_wire(handle), "detail": str(detail)},
        )
        return bool(response.get("recorded", True))

    def abort(self, handle: DirectExecutionHandle, reason: str) -> None:
        self._call(
            CB_ABORT,
            {"handle": handle_to_wire(handle), "reason": str(reason)},
        )

    def release(self, reason: str) -> None:
        try:
            self._call(CB_RELEASE, {"reason": str(reason)})
        finally:
            # The parent executor clears its execution on release; the mirror
            # must never claim a handle the parent no longer owns.
            self._handle = None
            self._recipe = None
